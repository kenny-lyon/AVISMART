import unittest

RECEPCION = {"proveedor": "Incubadora San Fernando", "sexo": "MIXTO", "descarte_llegada": 0, "peso_llegada_g": 42, "precio_pollito": 2.1}
from datetime import date, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import (
    Alerta,
    Galpon,
    Granja,
    Lote,
    Organizacion,
    SolicitudContacto,
    Tratamiento,
    Usuario,
    Vacunacion,
)
from app.security import hash_password

CLAVE = "clave-de-prueba-123"


class OrganizacionesTest(unittest.TestCase):
    """Cada cliente ve solo lo suyo; la plataforma administra clientes y no opera granjas avícolas."""

    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)

        def db_prueba():
            db = self.Session()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = db_prueba
        db = self.Session()
        db.add(Usuario(nombre="Dueño", email="duenio@avismart.pe", password_hash=hash_password(CLAVE), rol="PLATAFORMA", activo=1))
        self.ids = {}
        for clave in ("a", "b"):
            org = Organizacion(nombre=f"Cliente {clave.upper()}", estado="ACTIVA", creada_en=datetime.now())
            db.add(org)
            db.flush()
            for rol in ("ADMIN", "PRODUCTOR", "VETERINARIO"):
                db.add(Usuario(nombre=f"{rol} {clave}", email=f"{rol.lower()}@{clave}.pe", password_hash=hash_password(CLAVE), rol=rol, activo=1, organizacion_id=org.id))
            granja = Granja(nombre=f"Granja {clave}", ubicacion="Puno", organizacion_id=org.id)
            db.add(granja)
            db.flush()
            galpon = Galpon(granja_id=granja.id, nombre="Galpón 1", capacidad=1000)
            db.add(galpon)
            db.flush()
            lote = Lote(galpon_id=galpon.id, linea="Ross", fecha_ingreso=date.today() - timedelta(days=10), poblacion_inicial=500, estado="ACTIVO")
            db.add(lote)
            db.flush()
            vacuna = Vacunacion(lote_id=lote.id, nombre="Newcastle", fecha_programada=date.today() + timedelta(days=3), estado="PENDIENTE")
            tratamiento = Tratamiento(lote_id=lote.id, medicamento="Enrofloxacina", dosis="10 mg/kg", via="Agua de bebida", fecha_inicio=date.today(), dias_tratamiento=3, dias_carencia=5, estado="PENDIENTE")
            alerta = Alerta(lote_id=lote.id, tipo="SALUD", mensaje="Mortalidad alta", estado="NUEVA", requiere_veterinario=1, creada_en=datetime.now())
            db.add_all([vacuna, tratamiento, alerta])
            db.flush()
            self.ids[clave] = {"org": org.id, "granja": granja.id, "galpon": galpon.id, "lote": lote.id, "vacuna": vacuna.id, "tratamiento": tratamiento.id, "alerta": alerta.id}
        db.commit()
        self.ids["b"]["usuario"] = db.query(Usuario).filter(Usuario.email == "productor@b.pe").one().id
        db.close()
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.engine.dispose()

    def entrar(self, email, clave=CLAVE):
        r = self.client.post("/api/auth/login", json={"email": email, "password": clave})
        self.assertEqual(r.status_code, 200, r.text)
        return {"Authorization": f"Bearer {r.json()['token']}"}

    def test_un_cliente_no_ve_ni_modifica_datos_de_otro(self):
        a = self.entrar("admin@a.pe")
        prod_a = self.entrar("productor@a.pe")
        vet_a = self.entrar("veterinario@a.pe")
        b = self.ids["b"]

        resumen = self.client.get("/api/resumen", headers=a).json()
        self.assertEqual([l["id"] for l in resumen["lotes"]], [self.ids["a"]["lote"]])
        self.assertEqual([g["id"] for g in resumen["granjas"]], [self.ids["a"]["granja"]])

        for ruta in (f"/api/lotes/{b['lote']}/panel", f"/api/lotes/{b['lote']}/sanidad", f"/api/lotes/{b['lote']}/camara", f"/api/lotes/{b['lote']}/reporte.pdf"):
            self.assertEqual(self.client.get(ruta, headers=a).status_code, 404, ruta)

        validar = {"decision": "VALIDADA", "observacion": ""}
        self.assertEqual(self.client.post(f"/api/vacunas/{b['vacuna']}/validar", json=validar, headers=vet_a).status_code, 404)
        self.assertEqual(self.client.post(f"/api/tratamientos/{b['tratamiento']}/validar", json=validar, headers=vet_a).status_code, 404)
        self.assertEqual(self.client.post(f"/api/alertas/{b['alerta']}/atender", json={"decision": "ATENDIDA"}, headers=vet_a).status_code, 404)

        alertas = self.client.get("/api/alertas", headers=a).json()
        self.assertEqual({x["lote_id"] for x in alertas}, {self.ids["a"]["lote"]})

        lote_en_b = {**RECEPCION, "galpon_id": b["galpon"], "linea": "Ross", "fecha_ingreso": date.today().isoformat(), "cantidad_recibida": 10}
        self.assertEqual(self.client.post("/api/lotes", json=lote_en_b, headers=prod_a).status_code, 404)
        self.assertEqual(self.client.post(f"/api/granjas/{b['granja']}/galpones", json={"nombre": "Intruso", "capacidad": 10}, headers=prod_a).status_code, 404)

        correos = {u["email"] for u in self.client.get("/api/usuarios", headers=a).json()}
        self.assertTrue(all(c.endswith("@a.pe") for c in correos))
        self.assertEqual(self.client.post(f"/api/usuarios/{b['usuario']}/restablecer-clave", headers=a).status_code, 404)
        self.assertEqual(self.client.patch(f"/api/usuarios/{b['usuario']}/estado", json={"activo": False}, headers=a).status_code, 404)

    def test_umbral_de_mortalidad_es_por_organizacion(self):
        a = self.entrar("admin@a.pe")
        b = self.entrar("admin@b.pe")
        self.assertEqual(self.client.put("/api/umbral", json={"mortalidad_diaria": 5}, headers=a).status_code, 200)
        self.assertEqual(self.client.get("/api/resumen", headers=a).json()["umbral_mortalidad"], 5)
        self.assertEqual(self.client.get("/api/resumen", headers=b).json()["umbral_mortalidad"], 20)

    def test_plataforma_convierte_solicitud_en_cliente(self):
        dueno = self.entrar("duenio@avismart.pe")
        self.assertEqual(self.client.get("/api/resumen", headers=dueno).status_code, 403)
        self.assertEqual(self.client.get("/api/plataforma/solicitudes", headers=self.entrar("admin@a.pe")).status_code, 403)

        db = self.Session()
        solicitud = SolicitudContacto(nombre="Ana Quispe", email="ana@granjanueva.pe", empresa="Granja Nueva", pais="Perú", motivo="COMERCIAL", mensaje="Quiero usar AviSmart", estado="NUEVA", creada_en=datetime.now())
        db.add(solicitud)
        db.commit()
        solicitud_id = solicitud.id
        db.close()

        alta = self.client.post("/api/plataforma/organizaciones", headers=dueno, json={
            "nombre": "Granja Nueva SAC", "productor_nombre": "Ana Quispe", "productor_email": "ana@granjanueva.pe", "solicitud_id": solicitud_id,
        })
        self.assertEqual(alta.status_code, 201, alta.text)
        self.assertEqual(alta.json()["usuario"]["rol"], "PRODUCTOR")
        repetida = self.client.post("/api/plataforma/organizaciones", headers=dueno, json={
            "nombre": "Otra", "productor_nombre": "Otra Persona", "productor_email": "otra@granjanueva.pe", "solicitud_id": solicitud_id,
        })
        self.assertEqual(repetida.status_code, 400)
        estado = next(s for s in self.client.get("/api/plataforma/solicitudes", headers=dueno).json() if s["id"] == solicitud_id)["estado"]
        self.assertEqual(estado, "CLIENTE")

        temporal = self.entrar("ana@granjanueva.pe", alta.json()["clave_temporal"])
        self.client.post("/api/auth/cambiar-clave", headers=temporal, json={"clave_actual": alta.json()["clave_temporal"], "clave_nueva": "ClavePropia12345"})
        ana = self.entrar("ana@granjanueva.pe", "ClavePropia12345")
        self.assertEqual(self.client.get("/api/resumen", headers=ana).json()["lotes"], [])
        granja = self.client.post("/api/granjas", headers=ana, json={"nombre": "Granja Nueva", "ubicacion": "Juliaca"})
        self.assertEqual(granja.status_code, 201, granja.text)
        galpon = self.client.post(f"/api/granjas/{granja.json()['id']}/galpones", headers=ana, json={"nombre": "Galpón A", "capacidad": 3000})
        self.assertEqual(galpon.status_code, 201, galpon.text)
        lote = self.client.post("/api/lotes", headers=ana, json={**RECEPCION, "galpon_id": galpon.json()["id"], "linea": "Cobb", "fecha_ingreso": date.today().isoformat(), "cantidad_recibida": 2500})
        self.assertEqual(lote.status_code, 200, lote.text)

        self.assertEqual(self.client.post("/api/usuarios", headers=dueno, json={"nombre": "Colado", "email": "x@y.pe", "rol": "ADMIN"}).status_code, 400)

    def test_suspender_cliente_corta_el_acceso(self):
        dueno = self.entrar("duenio@avismart.pe")
        sesion_b = self.entrar("productor@b.pe")
        r = self.client.patch(f"/api/plataforma/organizaciones/{self.ids['b']['org']}", headers=dueno, json={"estado": "SUSPENDIDA"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.client.get("/api/resumen", headers=sesion_b).status_code, 401)
        login = self.client.post("/api/auth/login", json={"email": "productor@b.pe", "password": CLAVE})
        self.assertEqual(login.status_code, 401)
        self.assertIn("suspendido", login.json()["detail"])
        self.assertEqual(self.client.get("/api/resumen", headers=self.entrar("productor@a.pe")).status_code, 200)


    def test_productor_gestiona_solo_operarios_y_veterinarios(self):
        prod = self.entrar("productor@a.pe")
        alta = self.client.post("/api/usuarios", headers=prod, json={"nombre": "Pedro Operario", "email": "pedro@a.pe", "rol": "OPERARIO"})
        self.assertEqual(alta.status_code, 200, alta.text)
        self.assertEqual(alta.json()["usuario"]["organizacion"]["id"], self.ids["a"]["org"])
        for rol in ("PRODUCTOR", "ADMIN", "PLATAFORMA"):
            r = self.client.post("/api/usuarios", headers=prod, json={"nombre": "No permitido", "email": f"x{rol}@a.pe", "rol": rol})
            self.assertEqual(r.status_code, 400, rol)
        visibles = self.client.get("/api/usuarios", headers=prod).json()
        self.assertFalse(any(u["rol"] in ("ADMIN", "PLATAFORMA") for u in visibles), "el productor no ve cuentas de administración")
        db = self.Session()
        admin_a = db.query(Usuario).filter(Usuario.email == "admin@a.pe").one().id
        db.close()
        self.assertEqual(self.client.post(f"/api/usuarios/{admin_a}/restablecer-clave", headers=prod).status_code, 404)
        self.assertEqual(self.client.patch(f"/api/usuarios/{admin_a}/estado", headers=prod, json={"activo": False}).status_code, 404)
        operario = alta.json()["usuario"]["id"]
        self.assertEqual(self.client.patch(f"/api/usuarios/{operario}/estado", headers=prod, json={"activo": False}).status_code, 200)
        self.assertEqual(self.client.post(f"/api/usuarios/{operario}/restablecer-clave", headers=prod).status_code, 200)

    def test_plataforma_gestiona_el_personal_de_un_cliente(self):
        dueno = self.entrar("duenio@avismart.pe")
        org = self.ids["b"]["org"]
        vet = self.client.post(f"/api/plataforma/organizaciones/{org}/usuarios", headers=dueno, json={"nombre": "Vet Nueva", "email": "vetnueva@b.pe", "rol": "VETERINARIO"})
        self.assertEqual(vet.status_code, 200, vet.text)
        self.assertGreaterEqual(len(vet.json()["clave_temporal"]), 10)
        self.assertEqual(self.client.post(f"/api/plataforma/organizaciones/{org}/usuarios", headers=dueno, json={"nombre": "Admin Nuevo", "email": "adm@b.pe", "rol": "ADMIN"}).status_code, 400)
        personal = self.client.get(f"/api/plataforma/organizaciones/{org}/usuarios", headers=dueno).json()
        self.assertTrue(all(u["organizacion"]["id"] == org for u in personal))
        productor = next(u for u in personal if u["rol"] == "PRODUCTOR")
        baja = self.client.patch(f"/api/plataforma/organizaciones/{org}/usuarios/{productor['id']}/estado", headers=dueno, json={"activo": False})
        self.assertEqual(baja.status_code, 400)
        self.assertIn("Productor", baja.json()["detail"])
        reset = self.client.post(f"/api/plataforma/organizaciones/{org}/usuarios/{productor['id']}/restablecer-clave", headers=dueno)
        self.assertEqual(reset.status_code, 200, reset.text)
        ajena = self.ids["a"]["org"]
        self.assertEqual(self.client.post(f"/api/plataforma/organizaciones/{ajena}/usuarios/{productor['id']}/restablecer-clave", headers=dueno).status_code, 404)
        self.assertEqual(self.client.get(f"/api/plataforma/organizaciones/{org}/usuarios", headers=self.entrar("productor@a.pe")).status_code, 403)

    def test_umbral_lo_ajusta_el_veterinario(self):
        self.assertEqual(self.client.put("/api/umbral", json={"mortalidad_diaria": 9}, headers=self.entrar("veterinario@a.pe")).status_code, 200)
        self.assertEqual(self.client.put("/api/umbral", json={"mortalidad_diaria": 3}, headers=self.entrar("productor@a.pe")).status_code, 403)
        self.assertEqual(self.client.get("/api/resumen", headers=self.entrar("productor@a.pe")).json()["umbral_mortalidad"], 9)


    def test_sanidad_solo_acepta_el_catalogo(self):
        prod = self.entrar("productor@a.pe")
        lote = self.ids["a"]["lote"]
        cat = self.client.get("/api/catalogo/sanidad", headers=prod).json()
        self.assertTrue(cat["vacunas"] and cat["medicamentos"])
        ok = {"medicamento": "Enrofloxacina 10 %", "dosis": "10 mg/kg", "via": "Agua de bebida",
              "fecha_inicio": date.today().isoformat(), "dias_tratamiento": 5, "dias_carencia": 7}
        self.assertEqual(self.client.post(f"/api/lotes/{lote}/tratamientos", headers=prod, json=ok).status_code, 200)
        for cambio in ({"medicamento": "Cualquier cosa"}, {"dosis": "un chorrito"}, {"via": "Inyección"}):
            self.assertEqual(self.client.post(f"/api/lotes/{lote}/tratamientos", headers=prod, json={**ok, **cambio}).status_code, 400, cambio)
        vac = {"nombre": "Gumboro (cepa intermedia)", "fecha_programada": date.today().isoformat()}
        self.assertEqual(self.client.post(f"/api/lotes/{lote}/sanidad", headers=prod, json=vac).status_code, 200)
        self.assertEqual(self.client.post(f"/api/lotes/{lote}/sanidad", headers=prod, json={**vac, "nombre": "Vacuna inventada"}).status_code, 400)


    def test_un_lote_activo_por_galpon_y_datos_de_recepcion(self):
        prod = self.entrar("productor@a.pe")
        a = self.ids["a"]
        nuevo = {**RECEPCION, "galpon_id": a["galpon"], "linea": "Cobb", "fecha_ingreso": date.today().isoformat(), "cantidad_recibida": 600}
        ocupado = self.client.post("/api/lotes", headers=prod, json=nuevo)
        self.assertEqual(ocupado.status_code, 400)
        self.assertIn("ya tiene un lote activo", ocupado.json()["detail"])

        g2 = self.client.post(f"/api/granjas/{a['granja']}/galpones", headers=prod, json={"nombre": "Galpón 2", "capacidad": 1000}).json()
        base = {**nuevo, "galpon_id": g2["id"]}
        self.assertEqual(self.client.post("/api/lotes", headers=prod, json={**base, "cantidad_recibida": 1100}).status_code, 400)
        self.assertEqual(self.client.post("/api/lotes", headers=prod, json={**base, "fecha_ingreso": "2099-01-01"}).status_code, 400)
        self.assertEqual(self.client.post("/api/lotes", headers=prod, json={**base, "sexo": "OTRO"}).status_code, 400)
        creado = self.client.post("/api/lotes", headers=prod, json={**base, "cantidad_recibida": 1020, "descarte_llegada": 25, "guia": "G-001"})
        self.assertEqual(creado.status_code, 200, creado.text)
        lote = creado.json()
        self.assertEqual(lote["poblacion_inicial"], 995)
        self.assertEqual(lote["costo_pollitos"], round(1020 * 2.1, 2))
        self.assertEqual(lote["proveedor"], "Incubadora San Fernando")
        self.assertEqual(self.client.post("/api/lotes", headers=prod, json=base).status_code, 400)


if __name__ == "__main__":
    unittest.main()
