import os
import unittest
from datetime import datetime
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.models import Alerta, Galpon, Granja, Lote
from app.notifications import notificar_alertas


class NotificacionesTest(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://", poolclass=StaticPool)
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine)()
        granja = Granja(nombre="Granja", ubicacion="Puno")
        self.db.add(granja)
        self.db.flush()
        galpon = Galpon(granja_id=granja.id, nombre="Galpón 1", capacidad=100)
        self.db.add(galpon)
        self.db.flush()
        lote = Lote(
            galpon_id=galpon.id,
            linea="Ross",
            fecha_ingreso=datetime.now().date(),
            poblacion_inicial=100,
            peso_objetivo_g=2800,
            estado="ACTIVO",
        )
        self.db.add(lote)
        self.db.flush()
        self.alerta = Alerta(
            lote_id=lote.id,
            tipo="SALUD",
            mensaje="Mensaje de prueba",
            estado="NUEVA",
            requiere_veterinario=1,
            observacion="",
            creada_en=datetime.now(),
        )
        self.db.add(self.alerta)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    @patch.dict(os.environ, {}, clear=True)
    def test_sin_configuracion_no_intenta_enviar(self):
        notificar_alertas(self.db, [self.alerta])
        self.assertEqual(self.alerta.notificacion_estado, "NO_CONFIGURADA")

    @patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "token", "TELEGRAM_CHAT_ID": "123"}, clear=True)
    @patch("app.notifications._enviar", return_value=(True, ""))
    def test_registra_envio_exitoso(self, enviar):
        notificar_alertas(self.db, [self.alerta])
        enviar.assert_called_once()
        self.assertEqual(self.alerta.notificacion_estado, "ENVIADA")
        self.assertIsNotNone(self.alerta.notificada_en)

    @patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "token", "TELEGRAM_CHAT_ID": "123"}, clear=True)
    @patch("app.notifications._enviar", return_value=(False, "sin conexión"))
    def test_registra_fallo_sin_perder_alerta(self, enviar):
        notificar_alertas(self.db, [self.alerta])
        enviar.assert_called_once()
        self.assertEqual(self.alerta.notificacion_estado, "FALLIDA")
        self.assertEqual(self.alerta.notificacion_error, "sin conexión")
        self.assertIsNotNone(self.db.get(Alerta, self.alerta.id))


if __name__ == "__main__":
    unittest.main()
