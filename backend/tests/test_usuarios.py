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


class UsuariosApiTest(unittest.TestCase):
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
        db.add(
            Usuario(
                organizacion_id=organizacion.id,
                nombre="Administrador",
                email="admin@prueba.local",
                password_hash=hash_password("administrador123"),
                rol="ADMIN",
                activo=1,
                debe_cambiar_clave=0,
            )
        )
        db.commit()
        db.close()
        self.client = TestClient(app)
        login = self.client.post(
            "/api/auth/login",
            json={"email": "admin@prueba.local", "password": "administrador123"},
        )
        self.admin_headers = {"Authorization": f"Bearer {login.json()['token']}"}

    def tearDown(self):
        app.dependency_overrides.clear()
        self.engine.dispose()

    def test_alta_clave_temporal_cambio_obligatorio_y_desactivacion(self):
        alta = self.client.post(
            "/api/usuarios",
            json={"nombre": "Operador Uno", "email": "operador@prueba.local", "rol": "OPERARIO"},
            headers=self.admin_headers,
        )
        self.assertEqual(alta.status_code, 200, alta.text)
        cuenta = alta.json()["usuario"]
        clave_temporal = alta.json()["clave_temporal"]
        self.assertTrue(cuenta["debe_cambiar_clave"])
        self.assertGreaterEqual(len(clave_temporal), 10)

        login = self.client.post(
            "/api/auth/login",
            json={"email": cuenta["email"], "password": clave_temporal},
        )
        self.assertEqual(login.status_code, 200, login.text)
        headers = {"Authorization": f"Bearer {login.json()['token']}"}
        bloqueado = self.client.get("/api/resumen", headers=headers)
        self.assertEqual(bloqueado.status_code, 403)

        cambio = self.client.post(
            "/api/auth/cambiar-clave",
            json={"clave_actual": clave_temporal, "clave_nueva": "NuevaClaveSegura123"},
            headers=headers,
        )
        self.assertEqual(cambio.status_code, 200, cambio.text)
        self.assertFalse(cambio.json()["debe_cambiar_clave"])
        self.assertEqual(self.client.get("/api/resumen", headers=headers).status_code, 401, "la sesión con la clave vieja se cierra")
        headers = {"Authorization": f"Bearer {cambio.json()['token']}"}
        self.assertEqual(self.client.get("/api/resumen", headers=headers).status_code, 200)

        sin_permiso = self.client.post(
            "/api/usuarios",
            json={"nombre": "Otro Usuario", "email": "otro@prueba.local", "rol": "OPERARIO"},
            headers=headers,
        )
        self.assertEqual(sin_permiso.status_code, 403)

        baja = self.client.patch(
            f"/api/usuarios/{cuenta['id']}/estado",
            json={"activo": False},
            headers=self.admin_headers,
        )
        self.assertEqual(baja.status_code, 200, baja.text)
        login_baja = self.client.post(
            "/api/auth/login",
            json={"email": cuenta["email"], "password": "NuevaClaveSegura123"},
        )
        self.assertEqual(login_baja.status_code, 401)

    def test_no_permite_correo_duplicado_ni_desactivar_admin_actual(self):
        duplicado = self.client.post(
            "/api/usuarios",
            json={"nombre": "Administrador Dos", "email": "ADMIN@PRUEBA.LOCAL", "rol": "ADMIN"},
            headers=self.admin_headers,
        )
        self.assertEqual(duplicado.status_code, 400)

        usuarios = self.client.get("/api/usuarios", headers=self.admin_headers).json()
        admin = next(u for u in usuarios if u["email"] == "admin@prueba.local")
        baja = self.client.patch(
            f"/api/usuarios/{admin['id']}/estado",
            json={"activo": False},
            headers=self.admin_headers,
        )
        self.assertEqual(baja.status_code, 400)


if __name__ == "__main__":
    unittest.main()
