import os
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import antispam
from app.db import Base, get_db
from app.main import app
from app.models import Organizacion, SolicitudContacto, Usuario
from app.security import hash_password

# Dominios "reales" para las pruebas: no se consulta internet.
DOMINIOS_OK = {"granja.pe", "gmail.com", "avicola.pe"}


def solicitud(**cambios):
    datos = {
        "nombre": "Cliente Interesado",
        "email": "cliente@granja.pe",
        "empresa": "Granja Los Andes",
        "pais": "Perú",
        "aves": "5 000 a 20 000",
        "motivo": "COMERCIAL",
        "plan": "BASICO",
        "mensaje": "Deseo conocer el sistema para dos galpones de engorde.",
    }
    datos.update(cambios)
    return datos


@patch.dict(os.environ, {"AVISMART_DEV": "true", "SMTP_HOST": "", "TURNSTILE_SECRET_KEY": "", "AVISMART_PROXIES_CONFIABLES": "testclient"})
@patch("app.antispam.dominio_recibe_correo", side_effect=lambda d: d in DOMINIOS_OK)
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
        self.ip = 0

    def tearDown(self):
        app.dependency_overrides.clear()
        self.engine.dispose()

    def enviar(self, ip=None, **cambios):
        self.ip += 1
        return self.client.post("/api/contacto", json=solicitud(**cambios), headers={"X-Forwarded-For": ip or f"10.0.0.{self.ip}"})

    def entrar(self, email, password):
        respuesta = self.client.post("/api/auth/login", json={"email": email, "password": password})
        return {"Authorization": f"Bearer {respuesta.json()['token']}"}

    def bandeja(self):
        return self.client.get("/api/plataforma/solicitudes", headers=self.entrar("owner@prueba.local", "propietario123")).json()

    def test_solo_las_confirmadas_llegan_a_la_bandeja(self, _dns):
        alta = self.enviar()
        self.assertEqual(alta.status_code, 201, alta.text)
        self.assertEqual(self.bandeja(), [], "sin confirmar no aparece")

        token = parse_qs(urlparse(alta.json()["enlace_desarrollo"]).query)["token"][0]
        self.assertEqual(self.client.post("/api/contacto/confirmar", json={"token": token}).status_code, 200)
        self.assertEqual(self.client.post("/api/contacto/confirmar", json={"token": token}).status_code, 400, "un solo uso")

        bandeja = self.bandeja()
        self.assertEqual(len(bandeja), 1)
        self.assertEqual(bandeja[0]["estado"], "NUEVA")
        self.assertIsNotNone(bandeja[0]["verificada_en"])

        plataforma = self.entrar("owner@prueba.local", "propietario123")
        cambio = self.client.patch(f"/api/plataforma/solicitudes/{bandeja[0]['id']}", json={"estado": "CONTACTADA"}, headers=plataforma)
        self.assertEqual(cambio.status_code, 200, cambio.text)
        cliente = self.entrar("admin@prueba.local", "administrador123")
        self.assertEqual(self.client.get("/api/plataforma/solicitudes", headers=cliente).status_code, 403)

    def test_enlace_vencido(self, _dns):
        alta = self.enviar()
        token = parse_qs(urlparse(alta.json()["enlace_desarrollo"]).query)["token"][0]
        db = self.Session()
        db.query(SolicitudContacto).update({"token_expira": datetime.now() - timedelta(minutes=1)})
        db.commit()
        db.close()
        respuesta = self.client.post("/api/contacto/confirmar", json={"token": token})
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("venció", respuesta.json()["detail"])

    def test_correos_invalidos_desechables_o_sin_dominio(self, _dns):
        self.assertEqual(self.enviar(email="no-es-correo").status_code, 400)
        self.assertEqual(self.enviar(email="ademir@granja").status_code, 400)
        self.assertIn("temporales", self.enviar(email="bot@mailinator.com").json()["detail"])
        self.assertIn("dominio", self.enviar(email="ademir@gmial.con").json()["detail"])
        self.assertEqual(self.enviar(email="ademir@gmail.com").status_code, 201)

    def test_honeypot_y_contenido_sospechoso_van_aparte(self, _dns):
        trampa = self.enviar(sitio_web="http://spam.example")
        self.assertEqual(trampa.status_code, 201, "el bot no se entera")
        self.assertNotIn("enlace_desarrollo", trampa.json(), "no se envía confirmación")
        self.enviar(email="otro@gmail.com", mensaje="Compra ya http://a.example y http://b.example oferta")
        self.enviar(email="tercero@avicola.pe", mensaje="asdfghjklqwrtzxcvbnmplkjhgfdsazxcv")
        motivos = sorted(s["motivo_sospecha"] for s in self.bandeja())
        self.assertEqual(len(motivos), 3)
        self.assertTrue(all(s["estado"] == "SOSPECHOSA" for s in self.bandeja()))
        self.assertIn("Campo trampa completado (posible bot)", motivos)

    def test_mensaje_repetido_se_marca_sospechoso(self, _dns):
        for i in range(3):
            self.enviar(email=f"persona{i}@gmail.com", mensaje="Hola quiero informacion del sistema avicola por favor")
        estados = [s for s in (self.Session().query(SolicitudContacto).all())]
        self.assertEqual(estados[-1].estado, "SOSPECHOSA")
        self.assertEqual(estados[-1].motivo_sospecha, "Mensaje repetido en varias solicitudes")

    def test_limites_por_ip_y_por_correo(self, _dns):
        for i in range(antispam.POR_IP_15_MIN):
            self.assertEqual(self.enviar(ip="200.1.1.1", email=f"p{i}@gmail.com", mensaje=f"Mensaje distinto número {i} para el equipo").status_code, 201)
        self.assertEqual(self.enviar(ip="200.1.1.1", email="otra@gmail.com").status_code, 429)
        for i in range(antispam.POR_CORREO_DIA):
            self.enviar(email="mismo@gmail.com", mensaje=f"Consulta numero {i} sobre el plan basico de AviSmart")
        self.assertEqual(self.enviar(email="mismo@gmail.com").status_code, 429)
        enviadas = self.Session().query(SolicitudContacto).filter_by(email="mismo@gmail.com", confirmacion_enviada=1).count()
        self.assertEqual(enviadas, antispam.CONFIRMACIONES_POR_CORREO_DIA, "no se bombardea el correo de un tercero")

    @patch.dict(os.environ, {"TURNSTILE_SECRET_KEY": "secreto-de-prueba"})
    def test_turnstile_se_valida_en_el_servidor(self, _dns):
        with patch("app.antispam.urlopen") as abrir:
            abrir.return_value.__enter__.return_value.read.return_value = b'{"success": false}'
            self.assertEqual(self.enviar(turnstile_token="token-falso").status_code, 400)
            self.assertEqual(self.enviar().status_code, 400, "sin token se rechaza")
            abrir.return_value.__enter__.return_value.read.return_value = b'{"success": true}'
            self.assertEqual(self.enviar(turnstile_token="token-bueno").status_code, 201)

    def test_pendientes_viejas_se_depuran(self, _dns):
        self.enviar()
        db = self.Session()
        db.query(SolicitudContacto).update({"creada_en": datetime.now() - timedelta(hours=antispam.HORAS_HASTA_DEPURAR + 1)})
        db.commit()
        db.close()
        self.bandeja()
        self.assertEqual(self.Session().query(SolicitudContacto).count(), 0)


if __name__ == "__main__":
    unittest.main()
