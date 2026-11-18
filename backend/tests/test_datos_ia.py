"""Datos para la IA: uniformidad, sacrificadas, oximetría, faena, predicción y canales de hardware."""
import unittest
from datetime import date, datetime, timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from tests.evidencia_prueba import guia
from app.db import Base, get_db
from app.logic import peso_esperado
from app.main import app
from app.models import Alerta, FotoGalpon, Galpon, Granja, LecturaAmbiental, Organizacion, RegistroDiario, Usuario
from app.security import hash_password

CLAVE = "Clave#Prueba1"
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 100


class DatosIaTest(unittest.TestCase):
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
        for rol, correo in (("PRODUCTOR", "prod@c.pe"), ("VETERINARIO", "vet@c.pe")):
            db.add(Usuario(nombre=rol.title(), email=correo, password_hash=hash_password(CLAVE), rol=rol, activo=1, debe_cambiar_clave=0, organizacion_id=org.id))
        granja = Granja(nombre="Granja", ubicacion="Juliaca", organizacion_id=org.id)
        db.add(granja)
        db.flush()
        galpon = Galpon(granja_id=granja.id, nombre="Galpón 01", capacidad=5000)
        db.add(galpon)
        db.commit()
        self.galpon = galpon.id
        db.close()
        self.client = TestClient(app)
        self.h = {c: {"Authorization": "Bearer " + self.client.post("/api/auth/login", json={"email": f"{c}@c.pe", "password": CLAVE}).json()["token"]} for c in ("prod", "vet")}
        self.lote = self.client.post("/api/lotes", headers=self.h["prod"], json={
            "galpon_id": self.galpon, "linea": "Cobb 500", "fecha_ingreso": (date.today() - timedelta(days=20)).isoformat(), "proveedor": "San Fernando",
            "cantidad_recibida": 3000, "descarte_llegada": 0, "peso_llegada_g": 42, "precio_pollito": 2.3, "peso_objetivo_g": 3000, "edad_saca_dias": 42,
            "adjuntos": [guia(self.client, self.h["prod"])]}).json()["id"]

    def tearDown(self):
        app.dependency_overrides.clear()
        self.engine.dispose()

    def registrar(self, dias_atras=0, **datos):
        dia = 20 - dias_atras
        cuerpo = {"fecha": (date.today() - timedelta(days=dias_atras)).isoformat(), "mortalidad": 3, "alimento_kg": 100, "agua_l": 200,
                  "peso_muestra_g": peso_esperado(dia, "Cobb 500"), **datos}
        return self.client.post(f"/api/lotes/{self.lote}/registros", headers=self.h["prod"], json=cuerpo)

    def test_uniformidad_y_sacrificadas(self):
        self.assertIn("sacrificadas", self.registrar(descartadas=5).json()["detail"])
        self.assertIn("al menos 5", self.registrar(pesos_muestra=[800, 900]).json()["detail"])
        base = peso_esperado(20, "Cobb 500")
        pesos = [base, base, base * 1.02, base * 0.98, base * 1.2]
        r = self.registrar(descartadas=2, horas_luz=18, pesos_muestra=pesos)
        self.assertEqual(r.status_code, 200, r.text)
        db = self.Session()
        registro = db.query(RegistroDiario).one()
        self.assertEqual((registro.descartadas, registro.horas_luz, registro.muestra_aves), (2, 18, 5))
        self.assertEqual(registro.uniformidad_pct, 80.0, "4 de 5 aves dentro de ±10 % del promedio")
        self.assertAlmostEqual(registro.peso_muestra_g, sum(pesos) / 5, delta=0.1, msg="el promedio sale de los pesos")
        db.close()
        panel = self.client.get(f"/api/lotes/{self.lote}/panel", headers=self.h["prod"]).json()
        self.assertEqual(panel["uniformidad"]["pct"], 80.0)
        self.assertEqual(panel["aves_vivas"], 2997, "las sacrificadas ya están dentro de las bajas")

    def test_prediccion_sigue_la_tendencia_del_lote(self):
        self.assertIsNone(self.client.get(f"/api/lotes/{self.lote}/panel", headers=self.h["prod"]).json()["prediccion"], "sin datos no predice")
        for atras in range(7, -1, -1):
            r = self.registrar(atras, peso_muestra_g=peso_esperado(20 - atras, "Cobb 500") * 0.9)
            self.assertEqual(r.status_code, 200, r.text)
        p = self.client.get(f"/api/lotes/{self.lote}/panel", headers=self.h["prod"]).json()["prediccion"]
        self.assertTrue(p["disponible"])
        self.assertEqual(p["dias_restantes"], 22)
        self.assertAlmostEqual(p["peso_g"], peso_esperado(42, "Cobb 500") * 0.9, delta=2, msg="10 % bajo la curva se mantiene hasta la saca")
        self.assertGreater(p["mortalidad_final_pct"], 24 / 3000 * 100, "suma las bajas que faltan")

    def test_oximetria_alerta_cuando_cae(self):
        hoy, antes = date.today().isoformat(), (date.today() - timedelta(days=7)).isoformat()
        medir = lambda quien, fecha, spo2: self.client.post(f"/api/lotes/{self.lote}/oximetria", headers=self.h[quien], json={"fecha": fecha, "aves_medidas": 10, "spo2_promedio": spo2})  # noqa: E731
        self.assertEqual(medir("prod", antes, 88).status_code, 403, "la mide el veterinario")
        self.assertFalse(medir("vet", antes, 88).json()["alerta"], "la primera no tiene con qué compararse")
        self.assertTrue(medir("vet", hoy, 82).json()["alerta"])
        self.assertIn("Ya hay", medir("vet", hoy, 82).json()["detail"])
        self.assertEqual(len(self.client.get(f"/api/lotes/{self.lote}/oximetria", headers=self.h["prod"]).json()["mediciones"]), 2)
        db = self.Session()
        alerta = db.query(Alerta).filter(Alerta.mensaje.startswith("Oxígeno")).one()
        self.assertEqual(alerta.tipo, "SALUD")
        db.close()

    def test_sensor_con_aire_agua_y_fotos(self):
        clave = self.client.post(f"/api/galpones/{self.galpon}/sensor", headers=self.h["prod"]).json()["clave"]
        cabecera = {"X-Sensor-Clave": clave}
        with patch("app.iot.clima_local.consultar", return_value=None):
            r = self.client.post("/api/iot/lecturas", headers=cabecera, json={"temperatura": 27, "humedad": 60, "co2_ppm": 3500, "nh3_ppm": 30, "agua_l": 1.5})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(len([a for a in r.json()["alertas"] if a.startswith(("CO₂", "Amoníaco"))]), 2)
        panel = self.client.get(f"/api/lotes/{self.lote}/panel", headers=self.h["prod"]).json()
        self.assertEqual(panel["lectura"]["co2_ppm"], 3500)
        self.assertEqual(panel["agua_medidor_hoy_l"], 1.5)

        foto = lambda c, contenido=PNG: self.client.post("/api/iot/fotos", headers={"X-Sensor-Clave": c}, files={"archivo": ("g.png", contenido, "image/png")})  # noqa: E731
        self.assertEqual(foto("avs_falsa").status_code, 401)
        self.assertEqual(foto(clave, b"%PDF-1.4 no es foto").status_code, 400)
        self.assertEqual(self.client.get(f"/api/lotes/{self.lote}/camara/foto", headers=self.h["prod"]).status_code, 404)
        self.assertEqual(foto(clave).status_code, 201)
        self.assertEqual(foto(clave).status_code, 429, "una foto por minuto")
        self.assertEqual(self.client.get(f"/api/lotes/{self.lote}/camara/foto", headers=self.h["vet"]).content, PNG)
        self.assertIsNotNone(self.client.get(f"/api/lotes/{self.lote}/camara", headers=self.h["prod"]).json()["foto"])
        db = self.Session()
        self.assertEqual(db.query(FotoGalpon).one().lote_id, self.lote, "la foto queda ligada al lote para entrenar")
        self.assertEqual(db.query(LecturaAmbiental).one().agua_l, 1.5)
        db.close()

    def test_datos_de_faena_en_el_cierre(self):
        self.assertEqual(self.registrar(peso_muestra_g=peso_esperado(20, "Cobb 500")).status_code, 200)
        cuerpo = {"fecha_cierre": date.today().isoformat(), "aves_vendidas": 2900, "peso_total_kg": 5800, "precio_venta_kg": 6, "costo_pollitos": 6900,
                  "costo_alimento": 15000, "costo_sanidad": 500, "otros_costos": 100}
        cerrar = lambda **d: self.client.post(f"/api/lotes/{self.lote}/cerrar", headers=self.h["prod"], json={**cuerpo, **d})  # noqa: E731
        self.assertIn("canal", cerrar(peso_canal_kg=6000).json()["detail"])
        self.assertIn("decomisos", cerrar(decomisos_aves=3000).json()["detail"])
        r = cerrar(peso_canal_kg=4350, decomisos_aves=12, pododermatitis_pct=8.5)
        self.assertEqual(r.status_code, 200, r.text)
        for formato in ("pdf", "xlsx"):
            self.assertEqual(self.client.get(f"/api/lotes/{self.lote}/reporte.{formato}", headers=self.h["prod"]).status_code, 200)


if __name__ == "__main__":
    unittest.main()
