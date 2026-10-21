import unittest
from datetime import date, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.logic import evaluar_clima, evaluar_registro, peso_esperado
from app.models import Configuracion, LecturaAmbiental, Lote, RegistroDiario


class CurvasTest(unittest.TestCase):
    def test_curvas_ross_y_cobb_son_independientes(self):
        self.assertEqual(peso_esperado(0, "Ross"), 44)
        self.assertEqual(peso_esperado(21, "Ross"), 1012)
        self.assertEqual(peso_esperado(21, "Cobb"), 1116)
        self.assertEqual(peso_esperado(49, "Ross"), 3681)
        self.assertEqual(peso_esperado(49, "Cobb"), 4001)

    def test_cuatro_lineas_con_su_curva_y_nombres_antiguos(self):
        self.assertEqual(peso_esperado(42, "Ross 308"), 2998)
        self.assertEqual(peso_esperado(42, "Cobb 500"), 3278)
        self.assertEqual(peso_esperado(42, "Hubbard"), 3028)
        self.assertEqual(peso_esperado(42, "Arbor Acres"), 2981)
        self.assertEqual(peso_esperado(28, "Ross"), peso_esperado(28, "Ross 308"), "los lotes antiguos siguen con su curva")

    def test_interpolacion_entre_semanas(self):
        esperado = 213 + (533 - 213) * (3 / 7)
        self.assertAlmostEqual(peso_esperado(10, "Ross"), esperado)


class AlertasTest(unittest.TestCase):
    def setUp(self):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine)()
        self.ingreso = date(2026, 1, 1)
        self.lote = Lote(
            id=1,
            galpon_id=1,
            linea="Ross",
            fecha_ingreso=self.ingreso,
            poblacion_inicial=5000,
            peso_objetivo_g=2800,
            estado="ACTIVO",
        )
        self.db.add(self.lote)
        self.db.add(Configuracion(clave="mortalidad_diaria", valor="20"))
        for offset in range(1, 4):
            self.db.add(
                RegistroDiario(
                    lote_id=1,
                    usuario_id=1,
                    fecha=self.ingreso + timedelta(days=offset),
                    mortalidad=2,
                    alimento_kg=100,
                    agua_l=200,
                    peso_muestra_g=peso_esperado(offset, "Ross"),
                )
            )
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_un_registro_puede_generar_alertas_independientes(self):
        registro = RegistroDiario(
            lote_id=1,
            usuario_id=1,
            fecha=self.ingreso + timedelta(days=4),
            mortalidad=25,
            alimento_kg=50,
            agua_l=100,
            peso_muestra_g=80,
        )
        self.db.add(registro)
        self.db.flush()

        alertas = evaluar_registro(self.db, self.lote, registro)
        mensajes = [alerta.mensaje for alerta in alertas]

        self.assertEqual(len(alertas), 4)
        self.assertTrue(any(m.startswith("Mortalidad") for m in mensajes))
        self.assertTrue(any(m.startswith("El alimento") for m in mensajes))
        self.assertTrue(any(m.startswith("El agua") for m in mensajes))
        self.assertTrue(any(m.startswith("Peso") for m in mensajes))

    def test_temperatura_y_humedad_generan_alertas_separadas(self):
        lectura = LecturaAmbiental(
            galpon_id=1,
            fecha_hora=datetime(2026, 1, 5, 10, 0),
            temperatura=20,
            humedad=80,
            origen="SIMULADO",
        )

        alertas = evaluar_clima(self.db, self.lote, lectura)

        self.assertEqual(len(alertas), 2)
        self.assertTrue(any(a.mensaje.startswith("Temperatura") for a in alertas))
        self.assertTrue(any(a.mensaje.startswith("Humedad") for a in alertas))


if __name__ == "__main__":
    unittest.main()
