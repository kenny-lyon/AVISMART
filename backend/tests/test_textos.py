"""Nombres de granjas, clientes, personas y guías: se normalizan y se rechazan los absurdos."""
import unittest

from app.textos import guia_remision, nombre_lugar, nombre_persona


class TextosTest(unittest.TestCase):
    def rechaza(self, funcion, valor, motivo):
        with self.assertRaises(ValueError) as error:
            funcion(valor)
        self.assertIn(motivo, str(error.exception))

    def test_nombres_de_lugar(self):
        self.assertEqual(nombre_lugar("  Granja   avícola  San Martín  "), "Granja avícola San Martín")
        for valor in ("Avícola Ruelas S.A.C.", "El Rocío & Hnos.", "Granja N° 2 (Juliaca)"):
            self.assertEqual(nombre_lugar(valor), valor)
        self.rechaza(nombre_lugar, "Granja " + "abcde" * 8, "como máximo 40")
        self.rechaza(nombre_lugar, "asssssss", "demasiadas veces")
        self.rechaza(nombre_lugar, "12345", "al menos 3 letras")
        self.rechaza(nombre_lugar, "Granja <script>", "solo puede tener")

    def test_nombres_de_persona(self):
        self.assertEqual(nombre_persona("josé  maría o'neill-ríos"), "josé maría o'neill-ríos")
        self.rechaza(nombre_persona, "Juan123", "solo puede tener letras")
        self.rechaza(nombre_persona, "Juaaan", "demasiadas veces")
        self.rechaza(nombre_persona, "Jo", "al menos 3")

    def test_guia(self):
        self.assertEqual(guia_remision(" t001-004512 "), "T001-004512")
        self.assertEqual(guia_remision(""), "")
        self.rechaza(guia_remision, "T001-" + "9" * 30, "como máximo 20")
        self.rechaza(guia_remision, "ABC", "por ejemplo")


if __name__ == "__main__":
    unittest.main()
