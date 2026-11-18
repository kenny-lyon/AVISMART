"""Pesaje del lote: estadísticas de la muestra, ganancia diaria frente a la curva y alertas de crecimiento.

Criterios de referencia:
- Uniformidad: aves dentro de ±10 % del promedio.
- CV: 6–8 % es bueno; más de 10 % es un lote disparejo y, cerca de la saca, causa problemas en el camal.
- Del día 0 al 21 se recomienda pesar en grupo; desde el 21, ave por ave (guías de Aviagen).
"""
import json
from statistics import mean, pstdev

from fastapi import HTTPException

from .logic import _crear, _existe_alerta, peso_esperado
from .models import Lote, RegistroDiario

CV_ALTO = 10.0
GANANCIA_MINIMA_PCT = 90.0
DIAS_GANANCIA = 7
EDAD_PESO_INDIVIDUAL = 21
# Histograma: franjas de 5 % alrededor del promedio, de −25 % a +25 % (los extremos incluyen lo que quede fuera).
FRANJAS = [(-25 + 5 * i, -20 + 5 * i) for i in range(10)]


def _validar(pesos: list[float], nombre: str) -> None:
    if len(pesos) < 5:
        raise HTTPException(status_code=400, detail=f"Anota al menos 5 pesos de {nombre} para calcular la uniformidad")
    if any(not 25 <= p <= 6000 for p in pesos):
        raise HTTPException(status_code=400, detail="Cada peso de la muestra debe estar entre 25 y 6000 g")


def _percentil(ordenados: list[float], q: float) -> float:
    pos = (len(ordenados) - 1) * q
    i = int(pos)
    j = min(i + 1, len(ordenados) - 1)
    return ordenados[i] + (ordenados[j] - ordenados[i]) * (pos - i)


def estadisticas(pesos: list[float]) -> dict:
    """Promedio, desviación, CV, mínimo, máximo, percentiles, uniformidad e histograma de una muestra."""
    promedio = mean(pesos)
    de = pstdev(pesos)
    ordenados = sorted(pesos)
    histograma = []
    for k, (desde, hasta) in enumerate(FRANJAS):
        bajo, alto = promedio * (1 + desde / 100), promedio * (1 + hasta / 100)
        primera, ultima = k == 0, k == len(FRANJAS) - 1
        aves = sum(1 for p in pesos if (primera or p >= bajo) and (ultima or p < alto))
        histograma.append({"desde_g": round(bajo), "hasta_g": round(alto), "aves": aves, "en_rango": -10 <= desde and hasta <= 10})
    return {
        "aves": len(pesos),
        "promedio": round(promedio, 1),
        "de": round(de, 1),
        "cv": round(de / promedio * 100, 1),
        "minimo": round(ordenados[0], 1),
        "maximo": round(ordenados[-1], 1),
        "p10": round(_percentil(ordenados, 0.1), 1),
        "p50": round(_percentil(ordenados, 0.5), 1),
        "p90": round(_percentil(ordenados, 0.9), 1),
        "uniformidad": round(sum(1 for p in pesos if abs(p - promedio) <= promedio * 0.1) / len(pesos) * 100, 1),
        "histograma": histograma,
    }


def armar_muestra(pesos: list[float], machos: list[float], hembras: list[float], grupos: list[tuple[int, float]]) -> dict | None:
    """Arma la muestra del registro. Devuelve None si solo se anotó el peso promedio."""
    if grupos:
        if pesos or machos or hembras:
            raise HTTPException(status_code=400, detail="Usa el pesaje en grupo o el de ave por ave, no los dos")
        aves = sum(a for a, _ in grupos)
        promedio = sum(kg for _, kg in grupos) * 1000 / aves
        if not 25 <= promedio <= 6000:
            raise HTTPException(status_code=400, detail="El peso por ave del pesaje en grupo debe quedar entre 25 y 6000 g")
        return {"tipo": "GRUPO", "aves": aves, "promedio": round(promedio, 1), "cv": None, "uniformidad": None,
                "guardar": {"grupos": [{"aves": a, "kg": kg} for a, kg in grupos]}}
    if machos or hembras:
        if pesos:
            raise HTTPException(status_code=400, detail="Anota los pesos como lote mixto o separados por sexo, no los dos")
        if machos:
            _validar(machos, "machos")
        if hembras:
            _validar(hembras, "hembras")
        todos = machos + hembras
        guardar = {"machos": machos, "hembras": hembras}
    elif pesos:
        _validar(pesos, "aves")
        todos = pesos
        guardar = {"mixto": pesos}
    else:
        return None
    e = estadisticas(todos)
    return {"tipo": "INDIVIDUAL", "aves": e["aves"], "promedio": e["promedio"], "cv": e["cv"], "uniformidad": e["uniformidad"], "guardar": guardar}


def detalle(registro: RegistroDiario) -> dict | None:
    """Estadísticas guardadas de un registro, por sexo si se anotaron así."""
    if not registro.muestra_pesos:
        return None
    datos = json.loads(registro.muestra_pesos)
    if "grupos" in datos:
        return {"tipo": "GRUPO", "fecha": registro.fecha.isoformat(), "grupos": datos["grupos"], "aves": registro.muestra_aves,
                "promedio": registro.peso_muestra_g}
    machos, hembras = datos.get("machos") or [], datos.get("hembras") or []
    todos = datos.get("mixto") or machos + hembras
    salida = {"tipo": "INDIVIDUAL", "fecha": registro.fecha.isoformat(), "origen": datos.get("origen", "MANUAL"), **estadisticas(todos)}
    salida["por_sexo"] = {
        nombre: estadisticas(lista) for nombre, lista in (("machos", machos), ("hembras", hembras)) if len(lista) >= 5
    } or None
    return salida


def ganancia(lote: Lote, registros: list[RegistroDiario]) -> dict | None:
    """Ganancia diaria real de los últimos días frente a la que marca la curva de la línea."""
    if len(registros) < 2:
        return None
    ultimo = registros[-1]
    desde = ultimo.fecha.toordinal() - DIAS_GANANCIA
    base = next((r for r in registros if r.fecha.toordinal() >= desde and r is not ultimo), None)
    if base is None:
        return None
    dias = (ultimo.fecha - base.fecha).days
    if dias < 3:
        return None
    d0, d1 = (base.fecha - lote.fecha_ingreso).days, (ultimo.fecha - lote.fecha_ingreso).days
    real = (ultimo.peso_muestra_g - base.peso_muestra_g) / dias
    meta = (peso_esperado(d1, lote.linea) - peso_esperado(d0, lote.linea)) / dias
    if meta <= 0:
        return None
    return {"real_g": round(real, 1), "meta_g": round(meta, 1), "pct": round(real / meta * 100, 1), "dias": dias,
            "desde_dia": d0, "hasta_dia": d1}


def resumen(lote: Lote, registros: list[RegistroDiario]) -> dict:
    """Bloque «Pesaje» del panel."""
    con_muestra = [r for r in registros if r.muestra_pesos]
    dia = (registros[-1].fecha - lote.fecha_ingreso).days if registros else 0
    return {
        "ultima_muestra": detalle(con_muestra[-1]) if con_muestra else None,
        "ganancia": ganancia(lote, registros),
        "cv_alto": CV_ALTO,
        "metodo_sugerido": "GRUPO" if dia < EDAD_PESO_INDIVIDUAL else "INDIVIDUAL",
    }


def evaluar(db, lote: Lote, registro: RegistroDiario, registros: list[RegistroDiario]) -> list:
    """Alertas de ganancia baja y de lote disparejo al guardar el registro."""
    nuevas = []
    hoy = registro.fecha
    dia = (hoy - lote.fecha_ingreso).days
    g = ganancia(lote, registros)
    # Antes del día 7 los pesos de pollito varían mucho y la alerta daría falsos avisos.
    if g and dia >= 7 and g["pct"] < GANANCIA_MINIMA_PCT and not _existe_alerta(db, lote.id, "CRECIMIENTO", hoy, "Ganancia"):
        nuevas.append(_crear(
            db, lote.id, "CRECIMIENTO",
            f"Ganancia diaria de {g['real_g']:.0f} g en los últimos {g['dias']} días, frente a {g['meta_g']:.0f} g de la curva "
            f"({g['pct']:.0f} %). Revisa alimento, agua, temperatura y salud del lote.",
            False,
        ))
    if registro.muestra_cv is not None and registro.muestra_cv > CV_ALTO and not _existe_alerta(db, lote.id, "CRECIMIENTO", hoy, "Lote disparejo"):
        saca = lote.edad_saca_dias or 42
        cerca = dia >= saca - 7
        nuevas.append(_crear(
            db, lote.id, "CRECIMIENTO",
            f"Lote disparejo: CV de {registro.muestra_cv:.1f} % (lo bueno es 6–8 %), uniformidad {registro.uniformidad_pct:.0f} %. "
            + ("Faltan pocos días para la saca: las aves muy chicas o muy grandes dan problemas en el camal; considera separarlas."
               if cerca else "Revisa el espacio en comederos y bebederos, y separa las aves rezagadas."),
            False,
        ))
    return nuevas
