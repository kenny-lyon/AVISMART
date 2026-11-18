"""Balanza automática del galpón (M7): una plataforma con celda de carga donde las aves se suben solas.

El equipo (ESP32 + HX711, o el simulador) detecta cada peso estable y los envía en tandas a POST /api/iot/pesos con la
misma clave del sensor del galpón. AviSmart descarta las lecturas imposibles para la edad del lote:
- LIVIANA: menos del 60 % del peso de referencia (el ave estaba subiendo o bajando).
- DOBLE: más del 150 % (dos aves a la vez).
El peso de referencia es la curva de la línea ajustada por cómo viene el lote en su último pesaje, para no descartar de
más en un lote atrasado o adelantado. Con las válidas del día se calcula promedio, CV, uniformidad e histograma, y el
registro diario puede usarlas como muestra.
"""
import random
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from . import evidencias
from .db import get_db
from .iot import INTERVALO_MINIMO, MINUTOS_EN_LINEA, _galpon_de_la_clave, cliente
from .logic import peso_esperado
from .models import Lote, PesadaBalanza, RegistroDiario, Usuario
from .pesaje import estadisticas

router = APIRouter()

MINIMO_RELATIVO = 0.6
MAXIMO_RELATIVO = 1.5
MIN_VALIDAS = 5
# Para el registro diario basta una muestra grande; más aves no cambian el promedio y engordan la base.
MAX_MUESTRA = 500


class PesosIn(BaseModel):
    pesos: list[float] = Field(min_length=1, max_length=300)


def referencia(db: Session, lote: Lote, dia: date) -> float:
    """Peso esperado para ese día, ajustado por el último pesaje del registro diario."""
    edad = (dia - lote.fecha_ingreso).days
    curva = peso_esperado(edad, lote.linea)
    ultimo = (
        db.query(RegistroDiario).filter(RegistroDiario.lote_id == lote.id, RegistroDiario.fecha < dia)
        .order_by(RegistroDiario.fecha.desc()).first()
    )
    if ultimo is None:
        return curva
    razon = ultimo.peso_muestra_g / peso_esperado((ultimo.fecha - lote.fecha_ingreso).days, lote.linea)
    return curva * min(max(razon, 0.7), 1.3)


def clasificar(peso: float, ref: float) -> str | None:
    if peso < ref * MINIMO_RELATIVO:
        return "LIVIANA"
    if peso > ref * MAXIMO_RELATIVO:
        return "DOBLE"
    return None


@router.post("/api/iot/pesos")
def recibir(body: PesosIn, x_sensor_clave: str = Header(default="", max_length=100), db: Session = Depends(get_db)):
    """Tanda de pesos estables de la balanza (como máximo una por minuto)."""
    galpon = _galpon_de_la_clave(db, x_sensor_clave)
    ahora = datetime.now().replace(microsecond=0)
    ultima = db.query(PesadaBalanza).filter(PesadaBalanza.galpon_id == galpon.id).order_by(PesadaBalanza.fecha_hora.desc()).first()
    if ultima and ahora - ultima.fecha_hora < INTERVALO_MINIMO:
        raise HTTPException(status_code=429, detail="Envía los pesos como máximo una vez por minuto")
    if any(not 10 <= p <= 8000 for p in body.pesos):
        raise HTTPException(status_code=422, detail="Cada peso debe estar entre 10 y 8000 g")
    lote = db.query(Lote).filter(Lote.galpon_id == galpon.id, Lote.estado == "ACTIVO").first()
    ref = referencia(db, lote, ahora.date()) if lote else None
    validas = 0
    for p in body.pesos:
        descarte = clasificar(p, ref) if ref else None
        validas += descarte is None
        db.add(PesadaBalanza(galpon_id=galpon.id, lote_id=lote.id if lote else None, fecha_hora=ahora, peso_g=round(p, 1), descarte=descarte))
    db.commit()
    return {"ok": True, "lote_activo": lote is not None, "recibidas": len(body.pesos), "validas": validas if lote else 0}


def pesos_del_dia(db: Session, lote: Lote, dia: date) -> tuple[list[float], int, dict]:
    """(pesos válidos, total de pesadas, descartadas por motivo) del lote en ese día."""
    pesadas = db.query(PesadaBalanza).filter(
        PesadaBalanza.lote_id == lote.id,
        PesadaBalanza.fecha_hora >= datetime.combine(dia, time.min),
        PesadaBalanza.fecha_hora < datetime.combine(dia + timedelta(days=1), time.min),
    ).all()
    validas = [p.peso_g for p in pesadas if p.descarte is None]
    motivos = {"LIVIANA": 0, "DOBLE": 0}
    for p in pesadas:
        if p.descarte:
            motivos[p.descarte] = motivos.get(p.descarte, 0) + 1
    return validas, len(pesadas), motivos


def muestra(validas: list[float]) -> list[float]:
    """Hasta MAX_MUESTRA pesos tomados al azar del día (siempre los mismos para el mismo día)."""
    if len(validas) <= MAX_MUESTRA:
        return validas
    return random.Random(len(validas)).sample(validas, MAX_MUESTRA)


def resumen(db: Session, lote: Lote, dia: date | None = None) -> dict | None:
    """Bloque «Balanza» del panel; None si el galpón nunca envió pesos."""
    dia = dia or date.today()
    ultima = db.query(PesadaBalanza).filter(PesadaBalanza.galpon_id == lote.galpon_id).order_by(PesadaBalanza.fecha_hora.desc()).first()
    if ultima is None:
        return None
    validas, total, motivos = pesos_del_dia(db, lote, dia)
    return {
        "fecha": dia.isoformat(),
        "en_linea": datetime.now() - ultima.fecha_hora < timedelta(minutes=MINUTOS_EN_LINEA),
        "ultimo_envio": ultima.fecha_hora.isoformat(timespec="seconds"),
        "pesadas": total,
        "validas": len(validas),
        "descartadas": motivos,
        "suficiente": len(validas) >= MIN_VALIDAS,
        "estadisticas": estadisticas(validas) if len(validas) >= MIN_VALIDAS else None,
    }


@router.get("/api/lotes/{lote_id}/balanza")
def ver(lote_id: int, fecha: date | None = Query(default=None), db: Session = Depends(get_db), usuario: Usuario = Depends(cliente)):
    lote = evidencias._lote_del_usuario(db, lote_id, usuario)
    return resumen(db, lote, fecha) or {"fecha": (fecha or date.today()).isoformat(), "pesadas": 0, "validas": 0, "suficiente": False}
