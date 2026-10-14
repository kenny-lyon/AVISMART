import unittest
from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import Organizacion, Usuario
from app.security import hash_password


class ContactoApiTest(unittest.TestCase):
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
        organizacion = Organizacion(nombre="Cliente de prueba", estado="ACTIVA", creada_en=datetime.now())
        db.add(organizacion)
        db.flush()
        db.add_all([
            Usuario(nombre="Propietario", email="owner@prueba.local", password_hash=hash_password("propietario123"), rol="PLATAFORMA", activo=1, debe_cambiar_clave=0),
            Usuario(nombre="Admin cliente", email="admin@prueba.local", password_hash=hash_password("administrador123"), rol="ADMIN", activo=1, debe_cambiar_clave=0, organizacion_id=organizacion.id),
        ])
        db.commit()
        db.close()
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.engine.dispose()

    def token(self, email, password):
        respuesta = self.client.post("/api/auth/login", json={"email": email, "password": password})
        return {"Authorization": f"Bearer {respuesta.json()['token']}"}

    def test_visitante_envia_y_plataforma_gestiona(self):
        alta = self.client.post("/api/contacto", json={
            "nombre": "Cliente Interesado",
            "email": "cliente@granja.pe",
            "empresa": "Granja Los Andes",
            "pais": "Perú",
            "aves": "5 000 a 20 000",
            "motivo": "DEMO",
            "plan": "PROFESIONAL",
            "mensaje": "Deseo conocer el sistema para dos galpones.",
        })
        self.assertEqual(alta.status_code, 201, alta.text)

        cliente = self.token("admin@prueba.local", "administrador123")
        self.assertEqual(self.client.get("/api/plataforma/solicitudes", headers=cliente).status_code, 403)

        admin = self.token("owner@prueba.local", "propietario123")
        listado = self.client.get("/api/plataforma/solicitudes", headers=admin)
        self.assertEqual(listado.status_code, 200, listado.text)
        self.assertEqual(listado.json()[0]["estado"], "NUEVA")

        cambio = self.client.patch(
            f"/api/plataforma/solicitudes/{alta.json()['id']}",
            json={"estado": "CONTACTADA"},
            headers=admin,
        )
        self.assertEqual(cambio.status_code, 200, cambio.text)
        self.assertEqual(cambio.json()["estado"], "CONTACTADA")
        self.assertIsNotNone(cambio.json()["atendida_en"])


if __name__ == "__main__":
    unittest.main()
