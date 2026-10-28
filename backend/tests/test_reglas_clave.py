"""Reglas de una clave nueva: 8 a 15 caracteres, letras, números y símbolos, sin repeticiones."""
import unittest

from app.security import problema_con_clave_nueva


class ReglasClaveTest(unittest.TestCase):
    def test_rechaza_claves_debiles_o_absurdas(self):
        casos = {
            "a" * 200: "como máximo 15",
            "Clave#MuyLarga2026": "como máximo 15",
            "a" * 12: "letras, números y símbolos",
            "Galpon2026": "al menos un símbolo",
            "Ga#26zzzz": "más de 3 veces seguidas",
            "ab#1ab#1ab": "al menos 5 distintos",
            "Co#rta1": "al menos 8",
            " Clave#26": "espacios",
        }
        for clave, motivo in casos.items():
            with self.subTest(clave=clave[:20]):
                self.assertIn(motivo, problema_con_clave_nueva(clave) or "")

    def test_acepta_claves_razonables(self):
        for clave in ("Clave#Segura9", "galpon-26", "Puno.2026", "Ab12345@xyz"):
            with self.subTest(clave=clave):
                self.assertIsNone(problema_con_clave_nueva(clave))


if __name__ == "__main__":
    unittest.main()
