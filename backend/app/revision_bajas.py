"""Revisión de bajas por el médico veterinario.

Cada día con al menos una baja queda «por revisar». El veterinario ve las fotos que subió el personal y deja su dictamen:
mortalidad normal, requiere visita (con fecha, avisa al productor) o posible brote (alerta urgente al productor y al personal,
para indicar el tratamiento de inmediato). Puede adjuntar sus propias evidencias (necropsia, laboratorio).
"""
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from . import evidencias
from .db import get_db
from .logic import umbral_mortalidad
from .models import AdjuntoLote, Alerta, RegistroDiario, RevisionBajas, Usuario
from .notifications import notificar_alertas
from .security import organizacion_de, require

router = APIRouter()

DICTAMENES = {"NORMAL": "Mortalidad normal", "VISITA": "Requiere visita", "BROTE": "Posible brote"}
CAUSAS = [
    "Síndrome ascítico (mal de altura)",
    "Muerte súbita",
    "Amontonamiento por frío",
    "Enfermedad respiratoria",
    "Enfermedad entérica o coccidiosis",
    "Onfalitis o mala calidad del pollito",
    "Problemas de patas",
    "Golpe de calor",
    "Otra causa",
]
DIAS_VISITA = 14

cliente = require("ADMIN", "PRODUCTOR", "OPERARIO", "VETERINARIO")
veterinario = require("VETERINARIO")


class RevisionIn(BaseModel):
    dictamen: str
    causa: str = Field(min_length=2, max_length=80)
    observaciones: str = Field(default="", max_length=1000)
    fecha_visita: date | None = None
    adjuntos: list[int] = Field(default_factory=list, max_length=5)


def _nombres(db: Session, ids: set[int]) -> dict[int, str]:
    return {u.id: u.nombre for u in db.query(Usuario).filter(Usuario.id.in_(ids or {0}))}


def _revision(r: RevisionBajas, nombres: dict[int, str], adjuntos: list[dict]) -> dict:
    return {
        "dictamen": r.dictamen,
        "dictamen_nombre": DICTAMENES.get(r.dictamen, r.dictamen),
        "causa": r.causa,
        "observaciones": r.observaciones,
        "fecha_visita": r.fecha_visita.isoformat() if r.fecha_visita else None,
        "veterinario": nombres.get(r.veterinario_id),
        "creada_en": r.creada_en.isoformat(timespec="minutes"),
        "evidencias": adjuntos,
    }


@router.get("/api/catalogo/causas-bajas")
def catalogo(_: Usuario = Depends(cliente)):
    return {"dictamenes": DICTAMENES, "causas": CAUSAS, "dias_visita": DIAS_VISITA}


@router.get("/api/lotes/{lote_id}/bajas")
def listar(lote_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(cliente)):
    """Días con bajas del lote, del más reciente al más antiguo, con sus fotos y la revisión del veterinario."""
    lote = evidencias._lote_del_usuario(db, lote_id, usuario)
    umbral = umbral_mortalidad(db, organizacion_de(usuario))
    registros = sorted(lote.registros, key=lambda r: r.fecha)
    vivas = lote.poblacion_inicial
    filas = []
    for r in registros:
        if r.mortalidad > 0:
            filas.append((r, vivas))
        vivas -= r.mortalidad
    ids = [r.id for r, _ in filas]
    revisiones = {v.registro_id: v for v in db.query(RevisionBajas).filter(RevisionBajas.registro_id.in_(ids or [0]))}
    archivos = db.query(AdjuntoLote).filter(AdjuntoLote.registro_id.in_(ids or [0]), AdjuntoLote.seccion.in_(("BAJAS", "REVISION"))).all()
    nombres = _nombres(db, {a.subido_por for a in archivos} | {v.veterinario_id for v in revisiones.values()})
    dias = []
    for r, vivas_ese_dia in reversed(filas):
        propios = [evidencias._a_dict(a, nombres) for a in archivos if a.registro_id == r.id]
        revision = revisiones.get(r.id)
        dias.append({
            "registro_id": r.id,
            "fecha": r.fecha.isoformat(),
            "dia": (r.fecha - lote.fecha_ingreso).days,
            "mortalidad": r.mortalidad,
            "porcentaje": round(r.mortalidad / vivas_ese_dia * 100, 2) if vivas_ese_dia else 0,
            "prioridad": r.mortalidad > umbral,
            "fotos": [a for a in propios if a["seccion"] == "BAJAS"],
            "revision": _revision(revision, nombres, [a for a in propios if a["seccion"] == "REVISION"]) if revision else None,
        })
    return {
        "umbral": umbral,
        "activo": lote.estado == "ACTIVO",
        "pendientes": sum(1 for d in dias if d["revision"] is None),
        "dias": dias,
    }


@router.post("/api/registros/{registro_id}/revision")
def revisar(registro_id: int, body: RevisionIn, db: Session = Depends(get_db), usuario: Usuario = Depends(veterinario)):
    registro = db.get(RegistroDiario, registro_id)
    if registro is None:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    lote = evidencias._lote_del_usuario(db, registro.lote_id, usuario)
    if lote.estado != "ACTIVO":
        raise HTTPException(status_code=400, detail="El lote ya está cerrado")
    if registro.mortalidad <= 0:
        raise HTTPException(status_code=400, detail="Ese día no tuvo bajas")
    if db.query(RevisionBajas).filter(RevisionBajas.registro_id == registro.id).first():
        raise HTTPException(status_code=400, detail="Las bajas de ese día ya fueron evaluadas")
    if body.dictamen not in DICTAMENES:
        raise HTTPException(status_code=400, detail="Elige un dictamen válido")
    if body.causa not in CAUSAS:
        raise HTTPException(status_code=400, detail="Elige la causa probable de la lista")
    observaciones = body.observaciones.strip()
    if body.causa == "Otra causa" and len(observaciones) < 5:
        raise HTTPException(status_code=400, detail="Describe la causa en las observaciones")
    if body.dictamen == "BROTE" and len(observaciones) < 10:
        raise HTTPException(status_code=400, detail="En un posible brote, escribe qué observaste y qué debe hacer el personal")
    fecha_visita = None
    if body.dictamen == "VISITA":
        if body.fecha_visita is None:
            raise HTTPException(status_code=400, detail="Indica la fecha de la visita")
        if not date.today() <= body.fecha_visita <= date.today() + timedelta(days=DIAS_VISITA):
            raise HTTPException(status_code=400, detail=f"La visita debe ser desde hoy y dentro de los próximos {DIAS_VISITA} días")
        fecha_visita = body.fecha_visita

    revision = RevisionBajas(
        registro_id=registro.id,
        lote_id=lote.id,
        veterinario_id=usuario.id,
        dictamen=body.dictamen,
        causa=body.causa,
        observaciones=observaciones,
        fecha_visita=fecha_visita,
        creada_en=datetime.now(),
    )
    db.add(revision)
    evidencias.vincular_revision(db, lote, registro.id, body.adjuntos, usuario)

    # La alerta de mortalidad de ese día queda atendida con el dictamen.
    inicio = datetime.combine(registro.fecha, datetime.min.time())
    for alerta in db.query(Alerta).filter(
        Alerta.lote_id == lote.id, Alerta.tipo == "SALUD", Alerta.estado != "ATENDIDA",
        Alerta.mensaje.startswith("Mortalidad"), Alerta.creada_en >= inicio, Alerta.creada_en < inicio + timedelta(days=1),
    ):
        alerta.estado = "ATENDIDA"
        alerta.observacion = f"{DICTAMENES[body.dictamen]}: {body.causa}."
        alerta.atendida_por = usuario.id

    nuevas = []
    dia = f"bajas del {registro.fecha:%d/%m/%Y}: {registro.mortalidad} aves"
    if body.dictamen == "VISITA":
        nuevas.append(Alerta(
            lote_id=lote.id, tipo="VISITA", estado="NUEVA", requiere_veterinario=0, observacion="", creada_en=datetime.now(),
            mensaje=f"Visita del veterinario el {fecha_visita:%d/%m/%Y} ({dia}). Causa probable: {body.causa}."
                    + (f" {observaciones}" if observaciones else ""),
        ))
    elif body.dictamen == "BROTE":
        nuevas.append(Alerta(
            lote_id=lote.id, tipo="SALUD", estado="NUEVA", requiere_veterinario=0, observacion="", creada_en=datetime.now(),
            mensaje=f"Posible brote ({dia}). Causa probable: {body.causa}. Indicación del veterinario: {observaciones}",
        ))
    db.add_all(nuevas)
    db.commit()
    notificar_alertas(db, nuevas)
    return {"ok": True, "dictamen": body.dictamen}
