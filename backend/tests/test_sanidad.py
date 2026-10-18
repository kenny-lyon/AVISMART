"""Lógica sanitaria: carencia al cerrar el lote y ciclo de vacunas con sus recordatorios."""
import unittest
from datetime import date, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import Alerta, Galpon, Granja, Lote, Organizacion, RegistroDiario, Tratamiento, Usuario, Vacunacion
from app.security import hash_password

HOY = date.today()
CLAVE = "ClavePrueba123"


class SanidadTest(unittest.TestCase):
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
            db.add(Usuario(nombre=rol.title(), email=f"{rol.lower()}@granja.pe", password_hash=hash_password(CLAVE), rol=rol, activo=1, debe_cambiar_clave=0, organizacion_id=org.id))
        granja = Granja(nombre="Granja", ubicacion="Puno", organizacion_id=org.id)
        db.add(granja)
        db.flush()
        galpon = Galpon(granja_id=granja.id, nombre="Galpón 1", capacidad=1000)
        db.add(galpon)
        db.flush()
        lote = Lote(galpon_id=galpon.id, linea="Ross", fecha_ingreso=HOY - timedelta(days=40), poblacion_inicial=500, peso_objetivo_g=2800, estado="ACTIVO")
        db.add(lote)
        db.flush()
        db.add(RegistroDiario(lote_id=lote.id, usuario_id=1, fecha=HOY - timedelta(days=12), mortalidad=2, alimento_kg=50, agua_l=90, peso_muestra_g=2400))
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

    # ------------------------------------------------------------------ utilidades
    def tratamiento(self, inicio, dias=1, carencia=5, estado="PENDIENTE"):
        db = self.Session()
        db.add(Tratamiento(lote_id=self.lote_id, medicamento="Enrofloxacina 10 %", dosis="10 mg/kg", via="Agua de bebida",
                           fecha_inicio=inicio, dias_tratamiento=dias, dias_carencia=carencia, estado=estado, diagnostico=""))
        db.commit()
        db.close()

    def cerrar(self, fecha):
        return self.client.post(f"/api/lotes/{self.lote_id}/cerrar", headers=self.h["PRODUCTOR"], json={
            "fecha_cierre": fecha.isoformat(), "aves_vendidas": 400, "peso_total_kg": 900, "precio_venta_kg": 7,
            "costo_pollitos": 1000, "costo_alimento": 2000, "costo_sanidad": 100, "otros_costos": 0,
        })

    def programar(self, nombre, dias_atras):
        r = self.client.post(f"/api/lotes/{self.lote_id}/sanidad", headers=self.h["OPERARIO"],
                             json={"nombre": nombre, "fecha_programada": (HOY - timedelta(days=dias_atras)).isoformat()})
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()["id"]

    def revisar(self, vacuna_id, decision="VALIDADA"):
        return self.client.post(f"/api/vacunas/{vacuna_id}/validar", headers=self.h["VETERINARIO"], json={"decision": decision, "observacion": "ok"})

    def aplicar(self, vacuna_id, fecha=None, quien="OPERARIO"):
        return self.client.post(f"/api/vacunas/{vacuna_id}/aplicar", headers=self.h[quien],
                                json={"fecha_aplicacion": (fecha or HOY).isoformat(), "nota": "Frasco lote 123"})

    def recordatorios(self, vacuna_id=None):
        self.client.get("/api/alertas", headers=self.h["VETERINARIO"])  # dispara la evaluación
        db = self.Session()
        q = db.query(Alerta).filter(Alerta.tipo == "RECORDATORIO")
        if vacuna_id is not None:
            q = q.filter(Alerta.vacuna_id == vacuna_id)
        filas = [(a.estado, bool(a.requiere_veterinario)) for a in q.order_by(Alerta.id).all()]
        db.close()
        return filas

    # ------------------------------------------------------------------ carencia
    def test_carencia_se_compara_con_la_fecha_de_faena(self):
        # Libre para faena hace 5 días; hoy ya está libre, pero la faena del día -8 cae en carencia.
        self.tratamiento(inicio=HOY - timedelta(days=10), dias=1, carencia=5)
        r = self.cerrar(HOY - timedelta(days=8))
        self.assertEqual(r.status_code, 400, r.text)
        self.assertIn("cae dentro de la carencia", r.json()["detail"])
        self.assertEqual(self.cerrar(HOY).status_code, 200, "con faena hoy, la carencia ya terminó")

    def test_tratamiento_observado_sigue_en_carencia(self):
        self.tratamiento(inicio=HOY, dias=3, carencia=10, estado="OBSERVADA")
        r = self.cerrar(HOY)
        self.assertEqual(r.status_code, 400)
        sanidad = self.client.get(f"/api/lotes/{self.lote_id}/sanidad", headers=self.h["PRODUCTOR"]).json()
        self.assertTrue(sanidad["tratamientos"][0]["en_carencia"])
        panel = self.client.get(f"/api/lotes/{self.lote_id}/panel", headers=self.h["PRODUCTOR"]).json()
        self.assertEqual(len(panel["carencias"]), 1)

    def test_tratamiento_revisado_no_cambia_de_decision(self):
        self.tratamiento(inicio=HOY)
        r = self.client.post("/api/tratamientos/1/validar", headers=self.h["VETERINARIO"], json={"decision": "OBSERVADA", "observacion": "x"})
        self.assertEqual(r.status_code, 200)
        r = self.client.post("/api/tratamientos/1/validar", headers=self.h["VETERINARIO"], json={"decision": "VALIDADA"})
        self.assertEqual(r.status_code, 400)

    # ------------------------------------------------------------------ vacunas
    def test_ciclo_completo_de_una_vacuna(self):
        v = self.programar("Gumboro (cepa intermedia)", dias_atras=2)
        self.assertEqual(self.recordatorios(v), [("NUEVA", True)], "fecha vencida sin aprobar: avisa al veterinario")
        self.assertEqual(self.aplicar(v).status_code, 400, "no se aplica antes de aprobar la fecha")

        self.assertEqual(self.revisar(v).json()["estado"], "PROGRAMADA")
        self.assertEqual(self.recordatorios(v), [("ATENDIDA", True), ("NUEVA", False)], "ahora avisa al productor que falta aplicarla")

        self.assertEqual(self.aplicar(v, HOY + timedelta(days=1)).status_code, 400, "no se aplica en el futuro")
        r = self.aplicar(v, HOY - timedelta(days=1))
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["estado"], "APLICADA")
        self.assertEqual(r.json()["nota_aplicacion"], "Frasco lote 123")
        self.assertEqual(self.recordatorios(v), [("ATENDIDA", True), ("ATENDIDA", False)])
        self.assertEqual(self.aplicar(v).status_code, 400, "no se registra dos veces")

        r = self.revisar(v)
        self.assertEqual(r.json()["estado"], "VALIDADA")
        self.assertEqual(self.revisar(v).status_code, 400, "sin revisión pendiente")

    def test_recordatorios_no_se_cruzan_entre_vacunas_parecidas(self):
        a = self.programar("Gumboro (cepa intermedia)", dias_atras=10)
        b = self.programar("Gumboro (intermedia plus)", dias_atras=3)
        self.assertEqual(len(self.recordatorios()), 2, "una alerta por cada dosis")
        self.revisar(a)
        self.assertEqual(self.recordatorios(b), [("NUEVA", True)], "aprobar una no cierra la otra")

    def test_recordatorio_atendido_a_mano_no_reaparece(self):
        v = self.programar("Marek (HVT)", dias_atras=1)
        self.recordatorios(v)
        db = self.Session()
        alerta = db.query(Alerta).filter(Alerta.vacuna_id == v).one().id
        db.close()
        r = self.client.post(f"/api/alertas/{alerta}/atender", headers=self.h["VETERINARIO"], json={"decision": "ATENDIDA", "observacion": "Lo veo mañana"})
        self.assertEqual(r.status_code, 200)
        for _ in range(3):
            self.recordatorios(v)
        self.assertEqual(self.recordatorios(v), [("ATENDIDA", True)])

    def test_lote_cerrado_no_genera_recordatorios_y_cierra_los_abiertos(self):
        v = self.programar("Viruela aviar", dias_atras=1)
        self.assertEqual(self.recordatorios(v), [("NUEVA", True)])
        self.assertEqual(self.cerrar(HOY).status_code, 200)
        self.assertEqual(self.recordatorios(v), [("ATENDIDA", True)], "al cerrar el lote se cierra el recordatorio")
        db = self.Session()
        db.add(Vacunacion(lote_id=self.lote_id, nombre="Marek (HVT)", fecha_programada=HOY - timedelta(days=2), estado="PENDIENTE", observacion=""))
        db.commit()
        db.close()
        self.assertEqual(len(self.recordatorios()), 1, "un lote cerrado no genera recordatorios nuevos")

    def test_vacuna_en_lote_cerrado_no_se_aplica(self):
        v = self.programar("Viruela aviar", dias_atras=0)
        self.revisar(v)
        self.cerrar(HOY)
        self.assertEqual(self.aplicar(v).status_code, 400)


if __name__ == "__main__":
    unittest.main()
