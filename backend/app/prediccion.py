"""Predicción del lote a la edad de saca, sin entrenar un modelo: curva de la línea más la tendencia reciente.

Peso: la curva oficial a la edad de saca, ajustada por cuánto se ha alejado el lote de ella en los últimos pesajes.
Mortalidad: la tasa diaria de los últimos días, proyectada sobre los días que faltan.
Cuando haya campañas reales suficientes, este cálculo se reemplaza por un modelo entrenado con el mismo resultado.
"""
from statistics import mean, pstdev

from .logic import peso_esperado
from .models import Lote, RegistroDiario

DIAS_TENDENCIA = 7
MIN_REGISTROS = 3


def predecir(lote: Lote, registros: list[RegistroDiario], dia_actual: int) -> dict | None:
    """Registros en orden de fecha. None si todavía no hay datos suficientes."""
    edad_saca = lote.edad_saca_dias or 42
    if len(registros) < MIN_REGISTROS:
        return None
    if lote.estado != "ACTIVO" or dia_actual >= edad_saca:
        return {"disponible": False, "motivo": f"El lote ya alcanzó la edad de saca (día {edad_saca})."}

    recientes = registros[-DIAS_TENDENCIA:]
    razones = [r.peso_muestra_g / peso_esperado((r.fecha - lote.fecha_ingreso).days, lote.linea) for r in recientes]
    razon, variacion = mean(razones), pstdev(razones)
    curva = peso_esperado(edad_saca, lote.linea)
    peso = curva * razon

    muertes = sum(r.mortalidad for r in registros)
    vivas = max(lote.poblacion_inicial - muertes, 0)
    bajas_recientes = sum(r.mortalidad for r in recientes)
    tasa = bajas_recientes / (vivas + bajas_recientes) / len(recientes) if vivas + bajas_recientes else 0
    restantes = edad_saca - dia_actual
    bajas_futuras = vivas * (1 - (1 - tasa) ** restantes)
    objetivo = lote.peso_objetivo_g
    return {
        "disponible": True,
        "edad_saca": edad_saca,
        "dias_restantes": restantes,
        "peso_g": round(peso),
        "peso_min_g": round(curva * (razon - variacion)),
        "peso_max_g": round(curva * (razon + variacion)),
        "peso_objetivo_g": objetivo,
        "diferencia_objetivo_g": round(peso - objetivo) if objetivo else None,
        "mortalidad_final_pct": round((muertes + bajas_futuras) / lote.poblacion_inicial * 100, 2) if lote.poblacion_inicial else None,
        "aves_finales": round(vivas - bajas_futuras),
        "dias_usados": len(recientes),
        "confianza": "media" if len(registros) >= 14 else "baja",
    }
