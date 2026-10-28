"""Revisión de bajas: el veterinario ve los días con bajas y deja su dictamen (normal, visita o posible brote)."""
import unittest
from datetime import date, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from tests.evidencia_prueba import guia
from app.db import Base, get_db
from app.main import app
from app.models import Alerta, Galpon, Granja, Organizacion, Usuario
from app.security import hash_password

CLAVE = "Clave#Prueba1"
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 100


class RevisionBajasTest(unittest.TestCase):
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
        for rol, correo in (("PRODUCTOR", "prod@c.pe"), ("OPERARIO", "ope@c.pe"), ("VETERINARIO", "vet@c.pe")):
            db.add(Usuario(nombre=rol.title(), email=correo, password_hash=hash_password(CLAVE), rol=rol, activo=1, debe_cambiar_clave=0, organizacion_id=org.id))
        granja = Granja(nombre="Granja", ubicacion="Juliaca", organizacion_id=org.id)
        db.add(granja)
        db.flush()
        galpon = Galpon(granja_id=granja.id, nombre="Galpón 01", capacidad=5000)
        db.add(galpon)
        db.commit()
        galpon_id = galpon.id
        db.close()
        self.client = TestClient(app)
        self.h = {c: {"Authorization": "Bearer " + self.client.post("/api/auth/login", json={"email": f"{c}@c.pe", "password": CLAVE}).json()["token"]}
                  for c in ("prod", "ope", "vet")}
        self.lote = self.client.post("/api/lotes", headers=self.h["prod"], json={
            "galpon_id": galpon_id, "linea": "Cobb 500", "fecha_ingreso": (date.today() - timedelta(days=2)).isoformat(), "proveedor": "San Fernando",
            "cantidad_recibida": 3000, "descarte_llegada": 0, "peso_llegada_g": 42, "precio_pollito": 2.3, "adjuntos": [guia(self.client, self.h["prod"])]}).json()["id"]
        foto = self.client.post("/api/adjuntos/temporales", headers=self.h["ope"], data={"seccion": "BAJAS"}, files={"archivo": ("bajas.png", PNG, "image/png")}).json()["id"]
        for dias, bajas, adjuntos in ((2, 0, []), (1, 4, []), (0, 25, [foto])):
            r = self.client.post(f"/api/lotes/{self.lote}/registros", headers=self.h["ope"], json={
                "fecha": (date.today() - timedelta(days=dias)).isoformat(), "mortalidad": bajas, "alimento_kg": 50, "agua_l": 100,
                "peso_muestra_g": 45 + (2 - dias) * 10, "adjuntos": adjuntos})
            self.assertEqual(r.status_code, 200, r.text)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.engine.dispose()

    def bajas(self, quien="vet"):
        return self.client.get(f"/api/lotes/{self.lote}/bajas", headers=self.h[quien]).json()

    def revisar(self, registro_id, quien="vet", **datos):
        return self.client.post(f"/api/registros/{registro_id}/revision", headers=self.h[quien], json={"causa": "Muerte súbita", **datos})

    def test_dias_con_bajas_con_fotos_y_prioridad(self):
        lista = self.bajas()
        self.assertEqual(lista["pendientes"], 2, "todos los días con al menos una baja")
        hoy, ayer = lista["dias"]
        self.assertTrue(hoy["prioridad"], "25 bajas superan el umbral de 20")
        self.assertFalse(ayer["prioridad"])
        self.assertEqual([f["nombre"] for f in hoy["fotos"]], ["bajas.png"])
        self.assertEqual(self.bajas("prod")["pendientes"], 2, "el productor también ve la lista")

    def test_solo_el_veterinario_evalua_y_una_vez(self):
        dia = self.bajas()["dias"][1]["registro_id"]
        self.assertEqual(self.revisar(dia, "prod", dictamen="NORMAL").status_code, 403)
        self.assertEqual(self.revisar(dia, dictamen="NORMAL").status_code, 200)
        self.assertIn("ya fueron evaluadas", self.revisar(dia, dictamen="NORMAL").json()["detail"])
        self.assertEqual(self.bajas()["pendientes"], 1)

    def test_visita_avisa_al_productor_y_cierra_la_alerta(self):
        hoy = self.bajas()["dias"][0]["registro_id"]
        self.assertIn("fecha de la visita", self.revisar(hoy, dictamen="VISITA").json()["detail"])
        manana = (date.today() + timedelta(days=1)).isoformat()
        evidencia = self.client.post("/api/adjuntos/temporales", headers=self.h["vet"], data={"seccion": "REVISION"}, files={"archivo": ("necropsia.png", PNG, "image/png")}).json()["id"]
        r = self.revisar(hoy, dictamen="VISITA", fecha_visita=manana, adjuntos=[evidencia])
        self.assertEqual(r.status_code, 200, r.text)
        revision = self.bajas()["dias"][0]["revision"]
        self.assertEqual(revision["dictamen"], "VISITA")
        self.assertEqual([e["nombre"] for e in revision["evidencias"]], ["necropsia.png"])
        db = self.Session()
        mortalidad = db.query(Alerta).filter(Alerta.mensaje.startswith("Mortalidad")).one()
        self.assertEqual(mortalidad.estado, "ATENDIDA")
        visita = db.query(Alerta).filter(Alerta.mensaje.startswith("Visita del veterinario")).one()
        self.assertEqual(visita.requiere_veterinario, 0, "la ve y la atiende el productor")
        db.close()

    def test_posible_brote_exige_indicaciones_y_alerta_al_productor(self):
        hoy = self.bajas()["dias"][0]["registro_id"]
        self.assertIn("posible brote", self.revisar(hoy, dictamen="BROTE", observaciones="ver").json()["detail"])
        r = self.revisar(hoy, dictamen="BROTE", causa="Enfermedad respiratoria", observaciones="Aislar el galpón y no mover aves. Indico tratamiento hoy.")
        self.assertEqual(r.status_code, 200, r.text)
        db = self.Session()
        brote = db.query(Alerta).filter(Alerta.mensaje.startswith("Posible brote")).one()
        self.assertEqual((brote.tipo, brote.requiere_veterinario), ("SALUD", 0))
        db.close()
        panel = self.client.get(f"/api/lotes/{self.lote}/panel", headers=self.h["prod"]).json()
        self.assertEqual(panel["registros"][0]["revision"], "BROTE")

    def test_el_veterinario_solo_sube_evidencias_de_revision(self):
        r = self.client.post("/api/adjuntos/temporales", headers=self.h["vet"], data={"seccion": "BAJAS"}, files={"archivo": ("f.png", PNG, "image/png")})
        self.assertEqual(r.status_code, 403)


if __name__ == "__main__":
    unittest.main()
