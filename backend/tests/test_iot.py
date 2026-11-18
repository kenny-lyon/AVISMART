"""Sensor IoT del galpón: clave propia, lecturas con alertas de ambiente y límite de envíos."""
import unittest
from datetime import date, datetime, timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from tests.evidencia_prueba import guia
from app.db import Base, get_db
from app.main import app
from app.models import Galpon, Granja, LecturaAmbiental, Organizacion, Usuario
from app.security import hash_password

CLAVE = "Clave#Prueba1"


class IotTest(unittest.TestCase):
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
        self.galpon = {}
        for c in ("a", "b"):
            org = Organizacion(nombre=f"Cliente {c}", estado="ACTIVA", creada_en=datetime.now())
            db.add(org)
            db.flush()
            db.add(Usuario(nombre="Productor", email=f"prod@{c}.pe", password_hash=hash_password(CLAVE), rol="PRODUCTOR", activo=1, debe_cambiar_clave=0, organizacion_id=org.id))
            db.add(Usuario(nombre="Operario", email=f"ope@{c}.pe", password_hash=hash_password(CLAVE), rol="OPERARIO", activo=1, debe_cambiar_clave=0, organizacion_id=org.id))
            granja = Granja(nombre="Granja", ubicacion="Juliaca", organizacion_id=org.id)
            db.add(granja)
            db.flush()
            galpon = Galpon(granja_id=granja.id, nombre="Galpón 01", capacidad=5000)
            db.add(galpon)
            db.flush()
            self.galpon[c] = galpon.id
        db.commit()
        db.close()
        self.client = TestClient(app)
        self.h = {k: {"Authorization": "Bearer " + self.client.post("/api/auth/login", json={"email": k.replace("_", "@") + ".pe", "password": CLAVE}).json()["token"]}
                  for k in ("prod_a", "ope_a", "prod_b")}

    def tearDown(self):
        app.dependency_overrides.clear()
        self.engine.dispose()

    def enviar(self, clave, temperatura=32.0, humedad=60.0):
        with patch("app.iot.clima_local.consultar", return_value=None):
            return self.client.post("/api/iot/lecturas", headers={"X-Sensor-Clave": clave}, json={"temperatura": temperatura, "humedad": humedad})

    def permitir_otro_envio(self):
        db = self.Session()
        db.get(Galpon, self.galpon["a"]).sensor_ultimo_envio = datetime.now() - timedelta(minutes=2)
        db.commit()
        db.close()

    def test_solo_el_productor_activa_y_la_clave_se_guarda_como_resumen(self):
        self.assertEqual(self.client.post(f"/api/galpones/{self.galpon['a']}/sensor", headers=self.h["ope_a"]).status_code, 403)
        self.assertEqual(self.client.post(f"/api/galpones/{self.galpon['a']}/sensor", headers=self.h["prod_b"]).status_code, 404, "galpón de otro cliente")
        r = self.client.post(f"/api/galpones/{self.galpon['a']}/sensor", headers=self.h["prod_a"]).json()
        self.assertTrue(r["clave"].startswith("avs_"))
        db = self.Session()
        self.assertNotEqual(db.get(Galpon, self.galpon["a"]).sensor_clave_hash, r["clave"], "no se guarda la clave en claro")
        db.close()
        self.assertEqual(self.enviar("avs_inventada").status_code, 401)
        nueva = self.client.post(f"/api/galpones/{self.galpon['a']}/sensor", headers=self.h["prod_a"]).json()["clave"]
        self.assertEqual(self.enviar(r["clave"]).status_code, 401, "la clave anterior deja de servir")
        self.assertEqual(self.enviar(nueva).status_code, 200)
        self.client.delete(f"/api/galpones/{self.galpon['a']}/sensor", headers=self.h["prod_a"])
        self.permitir_otro_envio()
        self.assertEqual(self.enviar(nueva).status_code, 401, "desactivado no recibe lecturas")

    def test_lecturas_del_sensor_generan_alertas_y_respetan_el_limite(self):
        clave = self.client.post(f"/api/galpones/{self.galpon['a']}/sensor", headers=self.h["prod_a"]).json()["clave"]
        sin_lote = self.enviar(clave)
        self.assertEqual(sin_lote.status_code, 200)
        self.assertFalse(sin_lote.json()["lote_activo"], "sin lote se guarda pero no se evalúa")
        lote = self.client.post("/api/lotes", headers=self.h["prod_a"], json={
            "galpon_id": self.galpon["a"], "linea": "Cobb 500", "fecha_ingreso": date.today().isoformat(), "proveedor": "San Fernando",
            "cantidad_recibida": 3000, "descarte_llegada": 0, "peso_llegada_g": 42, "precio_pollito": 2.3, "adjuntos": [guia(self.client, self.h["prod_a"])]}).json()["id"]
        self.permitir_otro_envio()
        frio = self.enviar(clave, temperatura=24)
        self.assertEqual(frio.status_code, 200, frio.text)
        self.assertTrue(frio.json()["alertas"], "24 °C en el día 0 está fuera del rango 31–34 °C")
        self.assertEqual(self.enviar(clave).status_code, 429, "una lectura por minuto")
        self.assertEqual(self.enviar(clave, temperatura=80).status_code, 422)
        panel = self.client.get(f"/api/lotes/{lote}/panel", headers=self.h["prod_a"]).json()
        self.assertEqual(panel["lectura"]["origen"], "SENSOR")
        self.assertTrue(panel["sensor"]["en_linea"])
        db = self.Session()
        self.assertEqual(db.query(LecturaAmbiental).filter_by(origen="SENSOR").count(), 2)
        db.close()


if __name__ == "__main__":
    unittest.main()
