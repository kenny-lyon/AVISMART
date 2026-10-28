"""Detección de nombres tecleados al azar."""
import unittest

from app.textos import nombre_lugar, nombre_persona, parece_sin_sentido


class SinSentidoTest(unittest.TestCase):
    def test_detecta_texto_al_azar(self):
        for valor in ("qwdqwdqwddqwdqwdqwd", "asdasdasd", "jajaja", "xkcdfgh", "asdfgh granja", "Granja qwer", "dfghjk",
                      "Granja 123123123", "Granja 12345678", "Avícola ---..."):
            with self.subTest(valor=valor):
                self.assertTrue(parece_sin_sentido(valor))
        with self.assertRaises(ValueError):
            nombre_lugar("qwdqwdqwddqwdqwd")
        with self.assertRaises(ValueError):
            nombre_persona("Asdfgh Qwerty")

    def test_acepta_nombres_reales(self):
        for valor in ("Granja avícola San Martín", "Avícola Ruelas S.A.C.", "IASA (Inversiones Avipecuarias)", "Chimú Agropecuaria",
                      "Granja paradero-150", "Huepetuhe", "Ccora Quispe", "Nelson Catunta Huisa", "Instrumentos", "Avícola Schmidt"):
            with self.subTest(valor=valor):
                self.assertFalse(parece_sin_sentido(valor))


if __name__ == "__main__":
    unittest.main()
