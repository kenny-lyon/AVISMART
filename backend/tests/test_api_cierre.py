import unittest
from datetime import date, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import Galpon, Granja, Lote, Organizacion, RegistroDiario, Tratamiento, Usuario
from app.security import hash_password


class CierreApiTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
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
        organizacion = Organizacion(nombre="Cliente de prueba", estado="ACTIVA", creada_en=datetime.now())
        db.add(organizacion)
        db.flush()
        productor = Usuario(
            organizacion_id=organizacion.id,
            nombre="Productor de prueba",
            email="productor@prueba.local",
            password_hash=hash_password("prueba123"),
            rol="PRODUCTOR",
            activo=1,
        )
        db.add(productor)
        db.flush()
        granja = Granja(nombre="Granja prueba", ubicacion="Puno", organizacion_id=organizacion.id)
        db.add(granja)
        db.flush()
        galpon = Galpon(granja_id=granja.id, nombre="Galpón prueba", capacidad=1000)
        db.add(galpon)
        db.flush()
        self.lote = Lote(
            galpon_id=galpon.id,
            linea="Ross",
            fecha_ingreso=date.today() - timedelta(days=10),
            poblacion_inicial=100,
            peso_objetivo_g=2800,
            estado="ACTIVO",
        )
        db.add(self.lote)
        db.flush()
        db.add(
            RegistroDiario(
                lote_id=self.lote.id,
                usuario_id=productor.id,
                fecha=date.today() - timedelta(days=1),
                mortalidad=2,
                alimento_kg=20,
                agua_l=35,
                peso_muestra_g=320,
            )
        )
        db.commit()
        self.lote_id = self.lote.id
        db.close()
        self.client = TestClient(app)
        login = self.client.post(
            "/api/auth/login",
            json={"email": "productor@prueba.local", "password": "prueba123"},
        )
        self.headers = {"Authorization": f"Bearer {login.json()['token']}"}

    def tearDown(self):
        app.dependency_overrides.clear()
        self.engine.dispose()

    def datos_cierre(self):
        return {
            "fecha_cierre": date.today().isoformat(),
            "aves_vendidas": 98,
            "peso_total_kg": 220,
            "precio_venta_kg": 8.5,
            "costo_pollitos": 250,
            "costo_alimento": 900,
            "costo_sanidad": 80,
            "otros_costos": 40,
            "observaciones": "Cierre de prueba",
        }

    def test_cierra_lote_y_genera_ambos_reportes(self):
        respuesta = self.client.post(
            f"/api/lotes/{self.lote_id}/cerrar",
            json=self.datos_cierre(),
            headers=self.headers,
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        self.assertEqual(respuesta.json()["ingreso_total"], 1870)
        self.assertEqual(respuesta.json()["total_costos"], 1270)
        self.assertEqual(respuesta.json()["margen"], 600)

        resumen = self.client.get("/api/resumen", headers=self.headers)
        lote = next(item for item in resumen.json()["lotes"] if item["id"] == self.lote_id)
        self.assertEqual(lote["estado"], "CERRADO")
        self.assertEqual(lote["dia_vida"], 10)

        pdf = self.client.get(f"/api/lotes/{self.lote_id}/reporte.pdf", headers=self.headers)
        excel = self.client.get(f"/api/lotes/{self.lote_id}/reporte.xlsx", headers=self.headers)
        self.assertEqual(pdf.status_code, 200, pdf.text[:200])
        self.assertTrue(pdf.content.startswith(b"%PDF"))
        self.assertEqual(excel.status_code, 200, excel.text[:200])
        self.assertTrue(excel.content.startswith(b"PK"))

        segundo = self.client.post(
            f"/api/lotes/{self.lote_id}/cerrar",
            json=self.datos_cierre(),
            headers=self.headers,
        )
        self.assertEqual(segundo.status_code, 400)

    def test_impide_cerrar_durante_carencia(self):
        db = self.Session()
        db.add(
            Tratamiento(
                lote_id=self.lote_id,
                medicamento="Medicamento de prueba",
                dosis="1 ml",
                via="Agua de bebida",
                fecha_inicio=date.today(),
                dias_tratamiento=1,
                dias_carencia=5,
                aves_tratadas=None,
                estado="VALIDADA",
                diagnostico="",
                validado_por=None,
            )
        )
        db.commit()
        db.close()

        respuesta = self.client.post(
            f"/api/lotes/{self.lote_id}/cerrar",
            json=self.datos_cierre(),
            headers=self.headers,
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("carencia", respuesta.json()["detail"].lower())


if __name__ == "__main__":
    unittest.main()
