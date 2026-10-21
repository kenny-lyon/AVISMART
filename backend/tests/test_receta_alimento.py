"""Rol del veterinario: programa vacunas, indica tratamientos y define el plan de alimentación."""
import unittest
from datetime import date, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import Alerta, Galpon, Granja, Lote, Organizacion, RegistroDiario, Usuario
from app.security import hash_password

HOY = date.today()
CLAVE = "ClavePrueba123"
RECETA = {"medicamento": "Enrofloxacina 10 %", "dosis": "10 mg/kg", "via": "Agua de bebida", "fecha_inicio": HOY.isoformat(),
          "dias_tratamiento": 5, "dias_carencia": 7, "diagnostico": "Colibacilosis: mortalidad alta y lesiones en necropsia"}


class RecetaYAlimentoTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        Base.metadata.create_all(self.engine)

        def db_prueba():
            db = self.Session()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = db_prueba
        db = self.Session()
        org = Organizacion(nombre="Cliente", estado="ACTIVA", creada_en=datetime.now())
        db.add(org)
        db.flush()
        for rol in ("PRODUCTOR", "OPERARIO", "VETERINARIO"):
            db.add(Usuario(nombre=rol.title(), email=f"{rol.lower()}@granja.pe", password_hash=hash_password(CLAVE), rol=rol,
                           activo=1, debe_cambiar_clave=0, organizacion_id=org.id))
        granja = Granja(nombre="Granja", ubicacion="Puno", organizacion_id=org.id)
        db.add(granja)
        db.flush()
        galpon = Galpon(granja_id=granja.id, nombre="Galpón 01", capacidad=6000)
        db.add(galpon)
        db.flush()
        lote = Lote(galpon_id=galpon.id, linea="Cobb 500", fecha_ingreso=HOY - timedelta(days=25), poblacion_inicial=5000,
                    peso_objetivo_g=3000, estado="ACTIVO")
        db.add(lote)
        db.commit()
        self.lote_id = lote.id
        db.close()
        self.client = TestClient(app)
        self.h = {rol: self.entrar(f"{rol.lower()}@granja.pe") for rol in ("PRODUCTOR", "OPERARIO", "VETERINARIO")}

    def tearDown(self):
        app.dependency_overrides.clear()
        self.engine.dispose()

    def entrar(self, email):
        return {"Authorization": "Bearer " + self.client.post("/api/auth/login", json={"email": email, "password": CLAVE}).json()["token"]}

    # ------------------------------------------------------------------ vacunas
    def test_vacuna_programada_por_el_veterinario_ya_queda_aprobada(self):
        cuerpo = {"nombre": "Newcastle La Sota (refuerzo)", "fecha_programada": (HOY + timedelta(days=2)).isoformat()}
        vet = self.client.post(f"/api/lotes/{self.lote_id}/sanidad", headers=self.h["VETERINARIO"], json=cuerpo).json()
        self.assertEqual(vet["estado"], "PROGRAMADA", "lista para aplicar, sin pasar por aprobación")
        prod = self.client.post(f"/api/lotes/{self.lote_id}/sanidad", headers=self.h["PRODUCTOR"], json=cuerpo).json()
        self.assertEqual(prod["estado"], "PENDIENTE", "la propuesta del productor la aprueba el veterinario")

    # ------------------------------------------------------------------ receta veterinaria
    def test_receta_del_veterinario_la_inicia_el_personal(self):
        url = f"/api/lotes/{self.lote_id}/tratamientos/indicar"
        self.assertEqual(self.client.post(url, headers=self.h["PRODUCTOR"], json=RECETA).status_code, 403, "solo el veterinario indica")
        r = self.client.post(url, headers=self.h["VETERINARIO"], json=RECETA)
        self.assertEqual(r.status_code, 200, r.text)
        receta = r.json()
        self.assertEqual(receta["estado"], "INDICADO")
        self.assertTrue(receta["indicado"])
        self.assertFalse(receta["en_carencia"], "sin iniciar no hay carencia")

        db = self.Session()
        aviso = db.query(Alerta).filter(Alerta.tratamiento_id == receta["id"]).one()
        self.assertEqual((aviso.tipo, aviso.estado, aviso.requiere_veterinario), ("RECORDATORIO", "NUEVA", 0))
        self.assertIn("El veterinario indicó Enrofloxacina 10 %", aviso.mensaje)
        db.close()
        panel = self.client.get(f"/api/lotes/{self.lote_id}/panel", headers=self.h["PRODUCTOR"]).json()
        self.assertEqual(panel["tratamientos_indicados"], 1)
        self.assertEqual(panel["carencias"], [])

        iniciar = f"/api/tratamientos/{receta['id']}/iniciar"
        self.assertEqual(self.client.post(iniciar, headers=self.h["VETERINARIO"], json={"fecha_inicio": HOY.isoformat()}).status_code, 403)
        manana = (HOY + timedelta(days=1)).isoformat()
        self.assertEqual(self.client.post(iniciar, headers=self.h["OPERARIO"], json={"fecha_inicio": manana}).status_code, 400)
        hecho = self.client.post(iniciar, headers=self.h["OPERARIO"], json={"fecha_inicio": HOY.isoformat()}).json()
        self.assertEqual(hecho["estado"], "VALIDADA", "ya tiene la indicación del veterinario")
        self.assertTrue(hecho["en_carencia"], "desde el inicio corre la carencia")
        db = self.Session()
        self.assertEqual(db.get(Alerta, aviso.id).estado, "ATENDIDA", "el aviso se cierra solo al iniciar")
        db.close()
        self.assertEqual(self.client.post(iniciar, headers=self.h["OPERARIO"], json={"fecha_inicio": HOY.isoformat()}).status_code, 400)

    def test_el_personal_sigue_pudiendo_medicar_y_el_veterinario_valida_despues(self):
        cuerpo = {k: v for k, v in RECETA.items() if k != "diagnostico"}
        r = self.client.post(f"/api/lotes/{self.lote_id}/tratamientos", headers=self.h["OPERARIO"], json=cuerpo)
        self.assertEqual(r.json()["estado"], "PENDIENTE")
        self.assertFalse(r.json()["indicado"])

    # ------------------------------------------------------------------ alimentación
    def test_plan_de_alimentacion_y_registro_diario(self):
        plan = self.client.get(f"/api/lotes/{self.lote_id}/alimentacion", headers=self.h["OPERARIO"]).json()
        self.assertEqual([f["nombre"] for f in plan["fases"]], ["Preinicio", "Inicio", "Crecimiento", "Acabado"])
        self.assertEqual(plan["fase_actual"], "Crecimiento", "día 25")
        r = self.client.post(f"/api/lotes/{self.lote_id}/registros", headers=self.h["OPERARIO"], json={
            "fecha": HOY.isoformat(), "mortalidad": 3, "alimento_kg": 650, "agua_l": 1200, "peso_muestra_g": 1350})
        self.assertEqual(r.status_code, 200, r.text)
        db = self.Session()
        self.assertEqual(db.query(RegistroDiario).one().fase_alimento, "Crecimiento", "se toma del plan")
        db.close()
        self.assertEqual(self.client.get(f"/api/lotes/{self.lote_id}/panel", headers=self.h["OPERARIO"]).json()["alimento_hoy"]["nombre"], "Crecimiento")

    def test_el_veterinario_varia_el_plan_con_motivo(self):
        fases = [
            {"nombre": "Preinicio", "dia_desde": 0, "dia_hasta": 10, "presentacion": "Migaja"},
            {"nombre": "Inicio", "dia_desde": 11, "dia_hasta": 26, "presentacion": "Migaja o pellet pequeño", "producto": "Inicio medicado"},
            {"nombre": "Crecimiento", "dia_desde": 27, "dia_hasta": 37, "presentacion": "Pellet"},
            {"nombre": "Retiro", "dia_desde": 38, "dia_hasta": 45, "presentacion": "Pellet"},
        ]
        url = f"/api/lotes/{self.lote_id}/alimentacion"
        cuerpo = {"fases": fases, "motivo": "Se prolonga el Inicio por el brote respiratorio"}
        self.assertEqual(self.client.put(url, headers=self.h["PRODUCTOR"], json=cuerpo).status_code, 403, "lo varía el veterinario")
        r = self.client.put(url, headers=self.h["VETERINARIO"], json=cuerpo)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["fase_actual"], "Inicio", "día 25 cae ahora en Inicio")
        self.assertEqual(r.json()["cambios"][0]["motivo"], "Se prolonga el Inicio por el brote respiratorio")
        self.assertIn("Antes: Preinicio 0-10", r.json()["cambios"][0]["detalle"])

        hueco = [dict(fases[0]), dict(fases[2])]
        self.assertIn("sin huecos", self.client.put(url, headers=self.h["VETERINARIO"], json={"fases": hueco, "motivo": "prueba de hueco"}).json()["detail"])
        corto = [{"nombre": "Preinicio", "dia_desde": 0, "dia_hasta": 30}]
        self.assertIn("día 42", self.client.put(url, headers=self.h["VETERINARIO"], json={"fases": corto, "motivo": "plan corto"}).json()["detail"])


if __name__ == "__main__":
    unittest.main()
