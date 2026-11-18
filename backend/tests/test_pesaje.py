"""Pesaje: en grupo, por sexo, estadísticas de la muestra, ganancia diaria y alertas de crecimiento."""
import json
import unittest

from app.logic import peso_esperado
from app.models import Alerta, RegistroDiario
from app.pesaje import estadisticas
from tests import test_datos_ia


class PesajeTest(unittest.TestCase):
    # Mismo lote de prueba (Cobb 500, día 20) que las pruebas de datos para la IA.
    setUp = test_datos_ia.DatosIaTest.setUp
    tearDown = test_datos_ia.DatosIaTest.tearDown
    registrar = test_datos_ia.DatosIaTest.registrar

    def panel(self):
        return self.client.get(f"/api/lotes/{self.lote}/panel", headers=self.h["prod"]).json()

    def alertas(self, inicio):
        db = self.Session()
        try:
            return [a.mensaje for a in db.query(Alerta).filter(Alerta.mensaje.startswith(inicio))]
        finally:
            db.close()

    def test_estadisticas_de_la_muestra(self):
        e = estadisticas([900, 1000, 1000, 1000, 1100, 1200])
        self.assertEqual((e["minimo"], e["maximo"], e["p50"]), (900, 1200, 1000))
        self.assertEqual(sum(f["aves"] for f in e["histograma"]), 6, "cada ave cae en una franja")
        self.assertEqual(len(e["histograma"]), 10)
        self.assertAlmostEqual(e["cv"], e["de"] / e["promedio"] * 100, delta=0.1)

    def test_pesaje_en_grupo(self):
        self.assertIn("no los dos", self.registrar(grupos=[{"aves": 10, "kg": 9}], pesos_muestra=[900] * 5).json()["detail"])
        esperado = peso_esperado(20, "Cobb 500")
        r = self.registrar(grupos=[{"aves": 10, "kg": round(esperado * 10 / 1000, 2)}, {"aves": 10, "kg": round(esperado * 10 / 1000, 2)}])
        self.assertEqual(r.status_code, 200, r.text)
        db = self.Session()
        registro = db.query(RegistroDiario).one()
        self.assertAlmostEqual(registro.peso_muestra_g, esperado, delta=1, msg="kilos entre aves")
        self.assertEqual(registro.muestra_aves, 20)
        self.assertIsNone(registro.uniformidad_pct, "en grupo no se puede medir la uniformidad")
        self.assertIn("grupos", json.loads(registro.muestra_pesos))
        db.close()
        muestra = self.panel()["pesaje"]["ultima_muestra"]
        self.assertEqual(muestra["tipo"], "GRUPO")
        self.assertEqual(self.panel()["pesaje"]["metodo_sugerido"], "GRUPO", "antes del día 21 se sugiere en grupo")

    def test_machos_y_hembras_con_lote_disparejo(self):
        base = peso_esperado(20, "Cobb 500")
        machos = [base * f for f in (1.1, 1.2, 1.25, 1.15, 1.3)]
        hembras = [base * f for f in (0.8, 0.85, 0.75, 0.9, 0.82)]
        self.assertIn("hembras", self.registrar(pesos_machos=machos, pesos_hembras=hembras[:2]).json()["detail"])
        r = self.registrar(pesos_machos=machos, pesos_hembras=hembras)
        self.assertEqual(r.status_code, 200, r.text)
        muestra = self.panel()["pesaje"]["ultima_muestra"]
        self.assertEqual(muestra["aves"], 10)
        self.assertGreater(muestra["por_sexo"]["machos"]["promedio"], muestra["por_sexo"]["hembras"]["promedio"])
        self.assertGreater(muestra["cv"], 10)
        self.assertEqual(len(self.alertas("Lote disparejo")), 1)

    def test_ganancia_diaria_baja_avisa(self):
        self.assertEqual(self.registrar(7, peso_muestra_g=peso_esperado(13, "Cobb 500")).status_code, 200)
        r = self.registrar(0, peso_muestra_g=peso_esperado(20, "Cobb 500") * 0.85)
        self.assertEqual(r.status_code, 200, r.text)
        g = self.panel()["pesaje"]["ganancia"]
        self.assertEqual(g["dias"], 7)
        self.assertLess(g["pct"], 90)
        self.assertEqual(len(self.alertas("Ganancia diaria")), 1)

    def test_ganancia_normal_no_avisa(self):
        self.registrar(7, peso_muestra_g=peso_esperado(13, "Cobb 500"))
        self.registrar(0, peso_muestra_g=peso_esperado(20, "Cobb 500"))
        self.assertAlmostEqual(self.panel()["pesaje"]["ganancia"]["pct"], 100, delta=1)
        self.assertEqual(self.alertas("Ganancia diaria"), [])


    def test_balanza_filtra_y_alimenta_el_registro(self):
        clave = self.client.post(f"/api/galpones/{self.galpon}/sensor", headers=self.h["prod"]).json()["clave"]
        esperado = peso_esperado(20, "Cobb 500")
        buenas = [esperado * f for f in (0.95, 1.0, 1.05, 0.98, 1.02, 0.9)]
        enviar = lambda pesos, c=clave: self.client.post("/api/iot/pesos", headers={"X-Sensor-Clave": c}, json={"pesos": pesos})  # noqa: E731
        self.assertEqual(enviar([900], "avs_falsa").status_code, 401)
        r = enviar(buenas + [esperado * 0.3, esperado * 2])
        self.assertEqual(r.json()["validas"], 6, "descarta el ave subiendo y las dos aves juntas")
        self.assertEqual(enviar(buenas).status_code, 429, "una tanda por minuto")

        b = self.panel()["balanza"]
        self.assertEqual((b["pesadas"], b["validas"]), (8, 6))
        self.assertEqual(b["descartadas"], {"LIVIANA": 1, "DOBLE": 1})
        self.assertAlmostEqual(b["estadisticas"]["promedio"], sum(buenas) / 6, delta=0.5)

        self.assertIn("no los dos", self.registrar(usar_balanza=True, pesos_muestra=buenas[:5]).json()["detail"])
        r = self.registrar(usar_balanza=True)
        self.assertEqual(r.status_code, 200, r.text)
        muestra = self.panel()["pesaje"]["ultima_muestra"]
        self.assertEqual((muestra["origen"], muestra["aves"]), ("BALANZA", 6))
        self.assertIn("5 pesadas", self.registrar(1, usar_balanza=True).json()["detail"], "ayer no hubo pesadas")


if __name__ == "__main__":
    unittest.main()
