import os
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import Organizacion, Usuario
from app.security import hash_password

CLAVE = "ClaveOriginal123"


@patch.dict(os.environ, {"AVISMART_DEV": "true", "SMTP_HOST": "", "AVISMART_PROXIES_CONFIABLES": "testclient"})
class RecuperacionTest(unittest.TestCase):
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
        self.org_id = org.id
        db.add_all([
            Usuario(nombre="Ana Productora", email="ana@granja.pe", password_hash=hash_password(CLAVE), rol="PRODUCTOR", activo=1, debe_cambiar_clave=0, organizacion_id=org.id),
            Usuario(nombre="Baja", email="baja@granja.pe", password_hash=hash_password(CLAVE), rol="OPERARIO", activo=0, debe_cambiar_clave=0, organizacion_id=org.id),
        ])
        db.commit()
        db.close()
        self.client = TestClient(app)
        self.ip = 0

    def tearDown(self):
        app.dependency_overrides.clear()
        self.engine.dispose()

    def pedir(self, email):
        self.ip += 1
        return self.client.post("/api/auth/olvide-clave", json={"email": email}, headers={"X-Forwarded-For": f"10.1.0.{self.ip}"})

    def token_de(self, respuesta):
        return parse_qs(urlparse(respuesta.json()["enlace_desarrollo"]).query)["token"][0]

    def entrar(self, clave):
        return self.client.post("/api/auth/login", json={"email": "ana@granja.pe", "password": clave})

    def test_flujo_completo_y_cierre_de_sesiones(self):
        sesion_vieja = {"Authorization": "Bearer " + self.entrar(CLAVE).json()["token"]}
        self.assertEqual(self.client.get("/api/me", headers=sesion_vieja).status_code, 200)

        pedido = self.pedir("ANA@granja.pe ")
        self.assertEqual(pedido.status_code, 200)
        token = self.token_de(pedido)
        cambio = self.client.post("/api/auth/restablecer-clave", json={"token": token, "clave_nueva": "ClaveNueva#9"})
        self.assertEqual(cambio.status_code, 200, cambio.text)

        self.assertEqual(self.entrar("ClaveNueva#9").status_code, 200)
        self.assertEqual(self.entrar(CLAVE).status_code, 401, "la clave anterior deja de servir")
        self.assertEqual(self.client.get("/api/me", headers=sesion_vieja).status_code, 401, "se cierran las sesiones abiertas")
        repetido = self.client.post("/api/auth/restablecer-clave", json={"token": token, "clave_nueva": "OtraClave#123"})
        self.assertEqual(repetido.status_code, 400, "el enlace es de un solo uso")

    def test_misma_respuesta_exista_o_no_la_cuenta(self):
        existe = self.pedir("ana@granja.pe").json()
        no_existe = self.pedir("nadie@granja.pe").json()
        desactivada = self.pedir("baja@granja.pe").json()
        self.assertEqual(existe["mensaje"], no_existe["mensaje"])
        self.assertEqual(no_existe["mensaje"], desactivada["mensaje"])
        self.assertNotIn("enlace_desarrollo", no_existe)
        self.assertNotIn("enlace_desarrollo", desactivada, "una cuenta desactivada no recibe enlace")

    def test_enlace_vencido_y_enlace_reemplazado(self):
        primero = self.token_de(self.pedir("ana@granja.pe"))
        segundo = self.token_de(self.pedir("ana@granja.pe"))
        anterior = self.client.post("/api/auth/restablecer-clave", json={"token": primero, "clave_nueva": "ClaveNueva#9"})
        self.assertEqual(anterior.status_code, 400, "pedir otro enlace invalida el anterior")
        db = self.Session()
        db.query(Usuario).filter_by(email="ana@granja.pe").update({"reset_expira": datetime.now() - timedelta(minutes=1)})
        db.commit()
        db.close()
        vencido = self.client.post("/api/auth/restablecer-clave", json={"token": segundo, "clave_nueva": "ClaveNueva#9"})
        self.assertIn("venció", vencido.json()["detail"])

    def test_cliente_suspendido_no_recupera(self):
        db = self.Session()
        db.query(Organizacion).update({"estado": "SUSPENDIDA"})
        db.commit()
        db.close()
        self.assertNotIn("enlace_desarrollo", self.pedir("ana@granja.pe").json())

    def test_limites_por_correo_y_por_ip(self):
        for _ in range(3):
            self.assertIn("enlace_desarrollo", self.pedir("ana@granja.pe").json())
        self.assertNotIn("enlace_desarrollo", self.pedir("ana@granja.pe").json(), "4.º pedido en la hora: sin correo")
        for i in range(5):
            self.client.post("/api/auth/olvide-clave", json={"email": f"x{i}@granja.pe"}, headers={"X-Forwarded-For": "9.9.9.9"})
        bloqueado = self.client.post("/api/auth/olvide-clave", json={"email": "y@granja.pe"}, headers={"X-Forwarded-For": "9.9.9.9"})
        self.assertEqual(bloqueado.status_code, 429)

    def test_espacios_al_borde_se_rechazan(self):
        token = self.token_de(self.pedir("ana@granja.pe"))
        r = self.client.post("/api/auth/restablecer-clave", json={"token": token, "clave_nueva": " ClaveEsp12 "})
        self.assertEqual(r.status_code, 400)
        self.assertIn("espacios", r.json()["detail"])
        sesion = {"Authorization": "Bearer " + self.entrar(CLAVE).json()["token"]}
        r = self.client.post("/api/auth/cambiar-clave", headers=sesion, json={"clave_actual": CLAVE, "clave_nueva": "ClaveEsp12 "})
        self.assertEqual(r.status_code, 400)

    def test_cambiar_clave_entrega_sesion_nueva_y_cierra_las_otras(self):
        otra_sesion = {"Authorization": "Bearer " + self.entrar(CLAVE).json()["token"]}
        sesion = {"Authorization": "Bearer " + self.entrar(CLAVE).json()["token"]}
        r = self.client.post("/api/auth/cambiar-clave", headers=sesion, json={"clave_actual": CLAVE, "clave_nueva": "ClaveNueva#9"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.client.get("/api/me", headers={"Authorization": "Bearer " + r.json()["token"]}).status_code, 200)
        self.assertEqual(self.client.get("/api/me", headers=otra_sesion).status_code, 401)


    # ------------------------------------------------------------ contacto propio y accesos
    def test_contacto_de_la_cuenta_y_registro_de_accesos(self):
        sesion = {"Authorization": "Bearer " + self.entrar(CLAVE).json()["token"], "User-Agent": "Mozilla/5.0 (Windows NT 10.0) Chrome/130.0"}
        r = self.client.put("/api/me/contacto", headers=sesion, json={"telefono": "+51 987 654 321", "correo_alterno": "Ana.Respaldo@gmail.com"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["telefono"], "987654321")
        self.assertEqual(r.json()["correo_alterno"], "ana.respaldo@gmail.com")
        self.assertIn("distinto", self.client.put("/api/me/contacto", headers=sesion, json={"correo_alterno": "ana@granja.pe"}).json()["detail"])
        self.assertIn("9 dígitos", self.client.put("/api/me/contacto", headers=sesion, json={"telefono": "12345"}).json()["detail"])
        with patch("app.main.correo.enviar_aviso_cambio") as aviso:
            cambio = self.client.post("/api/auth/cambiar-clave", headers=sesion, json={"clave_actual": CLAVE, "clave_nueva": "Clave#Nueva7"})
        self.assertEqual(cambio.status_code, 200, cambio.text)
        aviso.assert_called_once()
        nueva = {"Authorization": "Bearer " + cambio.json()["token"]}
        accesos = self.client.get("/api/me/accesos", headers=nueva).json()
        self.assertEqual([a["evento"] for a in accesos], ["Cambio de clave", "Inicio de sesión"])
        self.assertIn("Chrome", accesos[0]["navegador"])

if __name__ == "__main__":
    unittest.main()
