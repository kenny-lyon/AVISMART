"""Simulador del sensor del galpón: hace lo mismo que el ESP32, enviando temperatura y humedad cada cierto tiempo.

Uso (desde backend/):
    .venv\\Scripts\\python -m app.simulador_iot --clave avs_xxxxx
    .venv\\Scripts\\python -m app.simulador_iot --clave avs_xxxxx --cada 60 --base 22 --veces 10
    .venv\\Scripts\\python -m app.simulador_iot --clave avs_xxxxx --balanza 2450 --pesadas 30 --solo-balanza

La temperatura sigue el ciclo del día (más fría de madrugada, más cálida a media tarde) con algo de ruido.
De vez en cuando simula una falla de la calefacción o la ventilación, para que se vea saltar la alerta de ambiente.
"""
import argparse
import json
import math
import random
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def lectura(base: float, falla: bool) -> tuple[float, float]:
    hora = datetime.now().hour + datetime.now().minute / 60
    ciclo = math.sin((hora - 9) / 24 * 2 * math.pi)  # mínimo cerca de las 3 a. m., máximo cerca de las 3 p. m.
    temperatura = base + 1.8 * ciclo + random.uniform(-0.4, 0.4)
    humedad = 62 - 4 * ciclo + random.uniform(-2, 2)
    if falla:
        temperatura += random.choice((-7, 7))
    return round(temperatura, 1), round(min(max(humedad, 20), 95))


def aire_y_agua(segundos: int, agua_dia: float, falla: bool) -> dict:
    """Lo que enviaría un ESP32 con módulos de CO2, amoníaco y medidor de agua."""
    return {
        "co2_ppm": round(random.uniform(1500, 2400) + (1500 if falla else 0)),
        "nh3_ppm": round(random.uniform(8, 16) + (15 if falla else 0), 1),
        "agua_l": round(agua_dia / 86400 * segundos * random.uniform(0.8, 1.2), 2),
    }


def enviar_foto(url: str, clave: str, ruta: str) -> str:
    limite = uuid.uuid4().hex
    cuerpo = (f'--{limite}\r\nContent-Disposition: form-data; name="archivo"; filename="galpon.jpg"\r\n'
              "Content-Type: image/jpeg\r\n\r\n").encode() + Path(ruta).read_bytes() + f"\r\n--{limite}--\r\n".encode()
    pedido = Request(f"{url.rstrip('/')}/api/iot/fotos", data=cuerpo, method="POST",
                     headers={"Content-Type": f"multipart/form-data; boundary={limite}", "X-Sensor-Clave": clave})
    try:
        with urlopen(pedido, timeout=30):
            return "foto ok"
    except HTTPError as error:
        return f"foto rechazada ({error.code})"
    except URLError as error:
        return f"foto sin conexión: {error.reason}"


def pesadas(peso: float, cantidad: int, cv: float = 8.0) -> list[float]:
    """Pesos estables como los detectaría la balanza: la mayoría de un ave, algunos de un ave subiendo y de dos aves."""
    salida = []
    for _ in range(cantidad):
        azar = random.random()
        if azar < 0.06:
            salida.append(round(peso * random.uniform(0.15, 0.5)))  # el ave aún subía o ya bajaba
        elif azar < 0.10:
            salida.append(round(random.gauss(peso, peso * cv / 100) + random.gauss(peso, peso * cv / 100)))  # dos aves
        else:
            salida.append(round(random.gauss(peso, peso * cv / 100)))
    return [max(p, 10) for p in salida]


def enviar_pesos(url: str, clave: str, pesos: list[float]) -> str:
    pedido = Request(f"{url.rstrip('/')}/api/iot/pesos", data=json.dumps({"pesos": pesos}).encode(), method="POST",
                     headers={"Content-Type": "application/json", "X-Sensor-Clave": clave})
    try:
        with urlopen(pedido, timeout=15) as r:
            datos = json.load(r)
        if not datos["lote_activo"]:
            return f"balanza: {datos['recibidas']} pesos (el galpón no tiene lote activo)"
        return f"balanza: {datos['recibidas']} pesos, {datos['validas']} válidos"
    except HTTPError as error:
        return f"balanza rechazada ({error.code})"
    except URLError as error:
        return f"balanza sin conexión: {error.reason}"


def enviar(url: str, clave: str, temperatura: float, humedad: float, extras: dict | None = None) -> str:
    pedido = Request(
        f"{url.rstrip('/')}/api/iot/lecturas",
        data=json.dumps({"temperatura": temperatura, "humedad": humedad, **(extras or {})}).encode(),
        headers={"Content-Type": "application/json", "X-Sensor-Clave": clave},
        method="POST",
    )
    try:
        with urlopen(pedido, timeout=15) as r:
            datos = json.load(r)
        if datos["alertas"]:
            return "ALERTA: " + " | ".join(datos["alertas"])
        return "ok" if datos["lote_activo"] else "ok (el galpón no tiene lote activo)"
    except HTTPError as error:
        try:
            return f"rechazada ({error.code}): {json.load(error)['detail']}"
        except Exception:  # noqa: BLE001
            return f"rechazada ({error.code})"
    except URLError as error:
        return f"sin conexión: {error.reason}"


def main():
    # La consola de Windows puede no tener todos los caracteres: nunca debe detener al simulador.
    sys.stdout.reconfigure(errors="replace")
    p = argparse.ArgumentParser(description="Simulador del sensor de temperatura y humedad de un galpón")
    p.add_argument("--clave", required=True, help="Clave del sensor que muestra AviSmart al activarlo")
    p.add_argument("--url", default="http://127.0.0.1:8000", help="Dirección de AviSmart")
    p.add_argument("--cada", type=int, default=60, help="Segundos entre lecturas (mínimo 60)")
    p.add_argument("--base", type=float, default=22.0, help="Temperatura promedio del galpón en °C")
    p.add_argument("--veces", type=int, default=0, help="Cantidad de lecturas (0 = sin fin)")
    p.add_argument("--falla-cada", type=int, default=15, help="Cada cuántas lecturas simular una falla (0 = nunca)")
    p.add_argument("--aire", action="store_true", help="Simular también CO2, amoníaco y medidor de agua")
    p.add_argument("--agua-dia", type=float, default=1900, help="Litros de agua por día del lote (con --aire)")
    p.add_argument("--foto", help="Foto (JPG) que se envía como si fuera la cámara del galpón")
    p.add_argument("--balanza", type=float, metavar="GRAMOS", help="Simular la balanza automática con aves de este peso promedio")
    p.add_argument("--pesadas", type=int, default=25, help="Aves que suben a la balanza entre un envío y otro (con --balanza)")
    p.add_argument("--solo-balanza", action="store_true", help="No enviar temperatura ni humedad, solo los pesos")
    a = p.parse_args()
    cada = max(a.cada, 60)
    n = 0
    print(f"Sensor simulado enviando a {a.url} cada {cada} s. Ctrl+C para detener.")
    try:
        while a.veces == 0 or n < a.veces:
            n += 1
            falla = a.falla_cada > 0 and n % a.falla_cada == 0
            t, h = lectura(a.base, falla)
            extras = aire_y_agua(cada, a.agua_dia, falla) if a.aire else None
            if not a.solo_balanza:
                print(f"{datetime.now():%H:%M:%S}  {t:5.1f} °C  {h:3.0f} %  ->  {enviar(a.url, a.clave, t, h, extras)}", flush=True)
            if a.balanza:
                print(f"{datetime.now():%H:%M:%S}  {enviar_pesos(a.url, a.clave, pesadas(a.balanza, a.pesadas))}", flush=True)
            if a.foto:
                print(f"{datetime.now():%H:%M:%S}  {enviar_foto(a.url, a.clave, a.foto)}", flush=True)
            if a.veces == 0 or n < a.veces:
                time.sleep(cada)
    except KeyboardInterrupt:
        print("\nSimulador detenido.")


if __name__ == "__main__":
    main()
