"""Clima de la zona: se guarda junto a la lectura del galpón y su falla no impide registrar."""
import unittest
from datetime import date, datetime
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from tests.evidencia_prueba import guia
from app.db import Base, get_db
from app.main import app
from app.models import Galpon, Granja, Organizacion, Usuario
from app.security import hash_password

CLAVE = "Clave#Prueba1"
EXTERIOR = {"temperatura": 9.5, "humedad": 40.0, "minima": -2.0, "hora_minima": "2026-10-29T04:00",
            "maxima": 17.0, "hora_maxima": "2026-10-29T13:00", "consultado": "2026-10-28T20:00"}


class ClimaLocalTest(unittest.TestCase):
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
        db.add(Usuario(nombre="Productor", email="prod@c.pe", password_hash=hash_password(CLAVE), rol="PRODUCTOR", activo=1, debe_cambiar_clave=0, organizacion_id=org.id))
        self.granja = Granja(nombre="Granja", ubicacion="Juliaca", organizacion_id=org.id)
        db.add(self.granja)
        db.flush()
        galpon = Galpon(granja_id=self.granja.id, nombre="Galpón 01", capacidad=5000)
        db.add(galpon)
        db.commit()
        self.granja_id, galpon_id = self.granja.id, galpon.id
        db.close()
        self.client = TestClient(app)
        self.h = {"Authorization": "Bearer " + self.client.post("/api/auth/login", json={"email": "prod@c.pe", "password": CLAVE}).json()["token"]}
        lote = self.client.post("/api/lotes", headers=self.h, json={
            "galpon_id": galpon_id, "linea": "Cobb 500", "fecha_ingreso": date.today().isoformat(), "proveedor": "San Fernando",
            "cantidad_recibida": 3000, "descarte_llegada": 0, "peso_llegada_g": 42, "precio_pollito": 2.3, "adjuntos": [guia(self.client, self.h)]})
        self.lote = lote.json()["id"]

    def tearDown(self):
        app.dependency_overrides.clear()
        self.engine.dispose()

    def test_sin_ubicacion_no_consulta(self):
        with patch("app.main.clima_local.consultar") as consultar:
            r = self.client.get(f"/api/lotes/{self.lote}/clima-exterior", headers=self.h).json()
        self.assertFalse(r["disponible"])
        self.assertIn("mapa", r["motivo"])
        consultar.assert_not_called()

    def test_la_lectura_guarda_el_clima_de_la_zona(self):
        db = self.Session()
        db.get(Granja, self.granja_id).latitud, db.get(Granja, self.granja_id).longitud = -15.49, -70.16
        db.commit()
        db.close()
        with patch("app.main.clima_local.consultar", return_value=EXTERIOR):
            self.assertEqual(self.client.get(f"/api/lotes/{self.lote}/clima-exterior", headers=self.h).json()["minima"], -2.0)
            r = self.client.post(f"/api/lotes/{self.lote}/clima", headers=self.h, json={"temperatura": 32, "humedad": 60})
        self.assertEqual(r.json()["lectura"]["temp_exterior"], 9.5)
        panel = self.client.get(f"/api/lotes/{self.lote}/panel", headers=self.h).json()
        self.assertEqual(panel["lectura"]["humedad_exterior"], 40.0)

        with patch("app.main.clima_local.consultar", return_value=None):
            r = self.client.post(f"/api/lotes/{self.lote}/clima", headers=self.h, json={"temperatura": 32, "humedad": 60})
        self.assertEqual(r.status_code, 200, "sin el servicio externo la lectura igual se guarda")
        self.assertIsNone(r.json()["lectura"]["temp_exterior"])


if __name__ == "__main__":
    unittest.main()
