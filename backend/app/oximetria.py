"""Oximetría del lote: saturación de oxígeno (SpO2) de una muestra de aves, medida por el veterinario.

En altura, una SpO2 que baja es señal temprana del síndrome ascítico. No hay un valor de corte único, porque la saturación
normal cambia con la altitud: por eso la alerta compara cada medición con la anterior del mismo lote.
"""
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from . import evidencias
from .db import get_db
from .models import Alerta, MedicionOxigeno, Usuario
from .notifications import notificar_alertas
from .security import require

router = APIRouter()
cliente = require("ADMIN", "PRODUCTOR", "OPERARIO", "VETERINARIO")
veterinario = require("VETERINARIO")

CAIDA_ALERTA = 5  # puntos de SpO2 frente a la medición anterior


class MedicionIn(BaseModel):
    fecha: date
    aves_medidas: int = Field(ge=1, le=200)
    spo2_promedio: float = Field(ge=50, le=100)
    spo2_minimo: float | None = Field(default=None, ge=30, le=100)
    nota: str = Field(default="", max_length=500)


def _medicion(m: MedicionOxigeno, nombres: dict[int, str]) -> dict:
    return {
        "id": m.id,
        "fecha": m.fecha.isoformat(),
        "aves_medidas": m.aves_medidas,
        "spo2_promedio": m.spo2_promedio,
        "spo2_minimo": m.spo2_minimo,
        "nota": m.nota,
        "veterinario": nombres.get(m.veterinario_id),
    }


@router.get("/api/lotes/{lote_id}/oximetria")
def listar(lote_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(cliente)):
    lote = evidencias._lote_del_usuario(db, lote_id, usuario)
    filas = db.query(MedicionOxigeno).filter(MedicionOxigeno.lote_id == lote.id).order_by(MedicionOxigeno.fecha.desc()).all()
    nombres = {u.id: u.nombre for u in db.query(Usuario).filter(Usuario.id.in_({m.veterinario_id for m in filas} or {0}))}
    return {"activo": lote.estado == "ACTIVO", "caida_alerta": CAIDA_ALERTA, "mediciones": [_medicion(m, nombres) for m in filas]}


@router.post("/api/lotes/{lote_id}/oximetria", status_code=201)
def registrar(lote_id: int, body: MedicionIn, db: Session = Depends(get_db), usuario: Usuario = Depends(veterinario)):
    lote = evidencias._lote_del_usuario(db, lote_id, usuario)
    if lote.estado != "ACTIVO":
        raise HTTPException(status_code=400, detail="El lote ya está cerrado")
    if body.fecha < lote.fecha_ingreso or body.fecha > date.today():
        raise HTTPException(status_code=400, detail="La fecha queda fuera del lote")
    if body.spo2_minimo is not None and body.spo2_minimo > body.spo2_promedio:
        raise HTTPException(status_code=400, detail="La saturación mínima no puede ser mayor que el promedio")
    if db.query(MedicionOxigeno).filter_by(lote_id=lote.id, fecha=body.fecha).first():
        raise HTTPException(status_code=400, detail="Ya hay una medición para esa fecha")
    anterior = (
        db.query(MedicionOxigeno).filter(MedicionOxigeno.lote_id == lote.id, MedicionOxigeno.fecha < body.fecha)
        .order_by(MedicionOxigeno.fecha.desc()).first()
    )
    db.add(MedicionOxigeno(
        lote_id=lote.id, fecha=body.fecha, aves_medidas=body.aves_medidas, spo2_promedio=body.spo2_promedio,
        spo2_minimo=body.spo2_minimo, nota=body.nota.strip(), veterinario_id=usuario.id,
    ))
    nuevas = []
    if anterior and anterior.spo2_promedio - body.spo2_promedio >= CAIDA_ALERTA:
        nuevas.append(Alerta(
            lote_id=lote.id, tipo="SALUD", estado="NUEVA", requiere_veterinario=0, observacion="", creada_en=datetime.now(),
            mensaje=f"Oxígeno en sangre en descenso: {body.spo2_promedio:.1f} % frente a {anterior.spo2_promedio:.1f} % de la medición anterior. "
                    "Riesgo de síndrome ascítico: revisa ventilación y temperatura.",
        ))
    db.add_all(nuevas)
    db.commit()
    notificar_alertas(db, nuevas)
    return {"ok": True, "alerta": bool(nuevas)}
