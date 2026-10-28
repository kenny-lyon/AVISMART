"""Clima de la zona de la granja (Open-Meteo, sin clave) para compararlo con el interior del galpón.

Se consulta con la latitud y longitud de la granja. Si el servicio no responde, el sistema sigue igual (RNF-06):
la lectura del galpón se guarda sin el dato exterior.
"""
import json
import time
from datetime import datetime
from urllib.parse import urlencode
from urllib.request import urlopen

URL = "https://api.open-meteo.com/v1/forecast"
CACHE_SEG = 15 * 60
_cache: dict[tuple[float, float], tuple[float, dict]] = {}


def consultar(latitud: float | None, longitud: float | None) -> dict | None:
    """Temperatura y humedad actuales de la zona, y la mínima y máxima de las próximas 24 horas."""
    if latitud is None or longitud is None:
        return None
    clave = (round(latitud, 2), round(longitud, 2))
    guardado = _cache.get(clave)
    if guardado and time.time() - guardado[0] < CACHE_SEG:
        return guardado[1]
    parametros = {
        "latitude": latitud,
        "longitude": longitud,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m",
        "hourly": "temperature_2m",
        "forecast_hours": 24,
        "timezone": "America/Lima",
    }
    try:
        with urlopen(f"{URL}?{urlencode(parametros)}", timeout=6) as respuesta:
            datos = json.load(respuesta)
        horas = datos["hourly"]["time"]
        temps = datos["hourly"]["temperature_2m"]
        i_min = min(range(len(temps)), key=lambda i: temps[i])
        i_max = max(range(len(temps)), key=lambda i: temps[i])
        clima = {
            "temperatura": float(datos["current"]["temperature_2m"]),
            "humedad": float(datos["current"]["relative_humidity_2m"]),
            # Velocidad en km/h y dirección de donde viene el viento (grados, 0 = norte).
            "viento_kmh": float(datos["current"]["wind_speed_10m"]),
            "viento_direccion": float(datos["current"]["wind_direction_10m"]),
            "minima": float(temps[i_min]),
            "hora_minima": horas[i_min],
            "maxima": float(temps[i_max]),
            "hora_maxima": horas[i_max],
            "consultado": datetime.now().isoformat(timespec="minutes"),
        }
    except Exception:  # noqa: BLE001 — sin Internet o respuesta inesperada: se sigue sin el dato
        return None
    _cache[clave] = (time.time(), clima)
    return clima
