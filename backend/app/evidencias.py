"""Evidencias del lote: archivos (fotos y PDF) por sección.

Flujo: mientras se llena «Abrir lote», cada archivo se sube como temporal (sin lote). Al abrir el lote se vinculan
y la guía de remisión es obligatoria. Después se pueden agregar más mientras el lote esté activo; al cerrarlo quedan fijas.
El registro del día sigue el mismo flujo con sus secciones (bajas, consumo y pesaje), que son opcionales.
Los archivos se guardan fuera de la web pública y solo los descarga el personal del mismo cliente.
"""
import os
import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .db import get_db
from .models import AdjuntoLote, Galpon, Granja, Lote, Usuario
from .security import organizacion_de, require

router = APIRouter()

SECCIONES = {
    "GALPON": "Galpón preparado",
    "GUIA": "Guía de remisión",
    "ORIGEN": "Factura u otros documentos",
    "VACUNAS": "Certificado de vacunación",
    "RECEPCION": "Fotos de la recepción",
    "BAJAS": "Fotos de las bajas",
    "CONSUMO": "Alimento y agua",
    "PESAJE": "Pesaje de la muestra",
    "REVISION": "Evidencias del veterinario",
}
# Estas pertenecen a un registro del día, no a la apertura del lote.
SECCIONES_REGISTRO = ("BAJAS", "CONSUMO", "PESAJE", "REVISION")
MAX_BYTES = 5 * 1024 * 1024
MAX_POR_SECCION = 5
# Se revisa el contenido real del archivo (firma), no solo la extensión.
FIRMAS = {
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "application/pdf": (b"%PDF-",),
}
EXTENSION = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "application/pdf": ".pdf"}

personal_cliente = require("ADMIN", "PRODUCTOR", "OPERARIO", "VETERINARIO")
gestor_lote = require("ADMIN", "PRODUCTOR")
# El operario también registra el día y puede adjuntar sus evidencias.
quien_registra = require("ADMIN", "PRODUCTOR", "OPERARIO")
# El veterinario adjunta sus evidencias al evaluar las bajas (necropsia, laboratorio).
quien_adjunta = require("ADMIN", "PRODUCTOR", "OPERARIO", "VETERINARIO")


def carpeta() -> Path:
    destino = Path(os.getenv("AVISMART_ADJUNTOS") or Path(__file__).resolve().parent.parent / "adjuntos")
    destino.mkdir(parents=True, exist_ok=True)
    return destino


def _tipo_real(contenido: bytes) -> str | None:
    if contenido[:4] == b"RIFF" and contenido[8:12] == b"WEBP":
        return "image/webp"
    for tipo, firmas in FIRMAS.items():
        if any(contenido.startswith(f) for f in firmas):
            return tipo
    return None


def _nombre_seguro(nombre: str) -> str:
    base = Path(nombre or "archivo").name
    base = re.sub(r"[^\w .()-]", "", base, flags=re.UNICODE).strip() or "archivo"
    return base[:120]


def _lote_del_usuario(db: Session, lote_id: int, usuario: Usuario) -> Lote:
    lote = (
        db.query(Lote)
        .join(Galpon, Lote.galpon_id == Galpon.id)
        .join(Granja, Galpon.granja_id == Granja.id)
        .filter(Lote.id == lote_id, Granja.organizacion_id == organizacion_de(usuario))
        .first()
    )
    if lote is None:
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    return lote


def _depurar_temporales(db: Session) -> None:
    limite = datetime.now() - timedelta(hours=24)
    for viejo in db.query(AdjuntoLote).filter(AdjuntoLote.lote_id.is_(None), AdjuntoLote.subido_en < limite).all():
        (carpeta() / viejo.ruta).unlink(missing_ok=True)
        db.delete(viejo)


def _a_dict(a: AdjuntoLote, nombres: dict[int, str] | None = None, fechas: dict[int, str] | None = None) -> dict:
    return {
        "registro_fecha": (fechas or {}).get(a.registro_id),
        "id": a.id,
        "seccion": a.seccion,
        "seccion_nombre": SECCIONES.get(a.seccion, a.seccion),
        "nombre": a.nombre,
        "tipo": a.tipo,
        "tamano": a.tamano,
        "subido_por": (nombres or {}).get(a.subido_por),
        "subido_en": a.subido_en.isoformat(timespec="minutes"),
    }


async def _guardar(db: Session, archivo: UploadFile, seccion: str, usuario: Usuario, lote: Lote | None) -> AdjuntoLote:
    if seccion not in SECCIONES:
        raise HTTPException(status_code=400, detail="La sección de la evidencia no es válida")
    contenido = await archivo.read(MAX_BYTES + 1)
    if len(contenido) > MAX_BYTES:
        raise HTTPException(status_code=400, detail="Cada archivo puede pesar como máximo 5 MB")
    if not contenido:
        raise HTTPException(status_code=400, detail="El archivo está vacío")
    tipo = _tipo_real(contenido)
    if tipo is None:
        raise HTTPException(status_code=400, detail="Solo se aceptan fotos (JPG, PNG o WEBP) y documentos PDF")
    org = organizacion_de(usuario)
    if lote is not None:
        ya = db.query(AdjuntoLote).filter(AdjuntoLote.lote_id == lote.id, AdjuntoLote.seccion == seccion).count()
        if ya >= MAX_POR_SECCION:
            raise HTTPException(status_code=400, detail=f"Ya hay {MAX_POR_SECCION} archivos en «{SECCIONES[seccion]}»")
    ruta = f"org_{org}/{uuid.uuid4().hex}{EXTENSION[tipo]}"
    destino = carpeta() / ruta
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(contenido)
    adjunto = AdjuntoLote(
        organizacion_id=org,
        lote_id=lote.id if lote else None,
        seccion=seccion,
        nombre=_nombre_seguro(archivo.filename or ""),
        tipo=tipo,
        tamano=len(contenido),
        ruta=ruta,
        subido_por=usuario.id,
        subido_en=datetime.now(),
    )
    db.add(adjunto)
    db.commit()
    db.refresh(adjunto)
    return adjunto


@router.post("/api/adjuntos/temporales")
async def subir_temporal(
    seccion: str = Form(...),
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(quien_adjunta),
):
    """Evidencia que se adjunta mientras se llena «Abrir lote», el registro del día o la revisión de bajas (se vincula al guardar)."""
    permitidas = {"OPERARIO": ("BAJAS", "CONSUMO", "PESAJE"), "VETERINARIO": ("REVISION",)}.get(usuario.rol)
    if permitidas is not None and seccion not in permitidas:
        raise HTTPException(status_code=403, detail="Tu cuenta no tiene permiso para esta acción")
    _depurar_temporales(db)
    return _a_dict(await _guardar(db, archivo, seccion, usuario, None))


def vincular(db: Session, lote: Lote, ids: list[int], usuario: Usuario) -> None:
    """Al abrir el lote: vincula las evidencias temporales del propio cliente. La guía es obligatoria."""
    org = organizacion_de(usuario)
    adjuntos = (
        db.query(AdjuntoLote)
        .filter(AdjuntoLote.id.in_(ids or [0]), AdjuntoLote.lote_id.is_(None), AdjuntoLote.organizacion_id == org)
        .all()
    )
    adjuntos = [a for a in adjuntos if a.seccion not in SECCIONES_REGISTRO]
    if not any(a.seccion == "GUIA" for a in adjuntos):
        raise HTTPException(status_code=400, detail="Adjunta la foto o el PDF de la guía de remisión para abrir el lote")
    por_seccion: dict[str, int] = {}
    for a in adjuntos:
        por_seccion[a.seccion] = por_seccion.get(a.seccion, 0) + 1
        if por_seccion[a.seccion] > MAX_POR_SECCION:
            raise HTTPException(status_code=400, detail=f"Como máximo {MAX_POR_SECCION} archivos por sección")
        a.lote_id = lote.id


def vincular_registro(db: Session, lote: Lote, registro_id: int, ids: list[int], usuario: Usuario) -> None:
    """Al guardar el registro del día: vincula sus evidencias temporales (opcionales) del propio cliente."""
    adjuntos = (
        db.query(AdjuntoLote)
        .filter(AdjuntoLote.id.in_(ids or [0]), AdjuntoLote.lote_id.is_(None), AdjuntoLote.organizacion_id == organizacion_de(usuario),
                AdjuntoLote.seccion.in_(("BAJAS", "CONSUMO", "PESAJE")))
        .all()
    )
    for seccion in ("BAJAS", "CONSUMO", "PESAJE"):
        if sum(1 for a in adjuntos if a.seccion == seccion) > MAX_POR_SECCION:
            raise HTTPException(status_code=400, detail=f"Como máximo {MAX_POR_SECCION} archivos en «{SECCIONES[seccion]}»")
    for a in adjuntos:
        a.lote_id = lote.id
        a.registro_id = registro_id


def vincular_revision(db: Session, lote: Lote, registro_id: int, ids: list[int], usuario: Usuario) -> None:
    """Al guardar la revisión de bajas: vincula las evidencias del veterinario al registro de ese día."""
    for a in (
        db.query(AdjuntoLote)
        .filter(AdjuntoLote.id.in_(ids or [0]), AdjuntoLote.lote_id.is_(None), AdjuntoLote.organizacion_id == organizacion_de(usuario),
                AdjuntoLote.seccion == "REVISION")
        .all()
    ):
        a.lote_id = lote.id
        a.registro_id = registro_id


@router.get("/api/lotes/{lote_id}/adjuntos")
def listar(lote_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(personal_cliente)):
    lote = _lote_del_usuario(db, lote_id, usuario)
    filas = db.query(AdjuntoLote).filter(AdjuntoLote.lote_id == lote.id).order_by(AdjuntoLote.subido_en).all()
    nombres = {u.id: u.nombre for u in db.query(Usuario).filter(Usuario.id.in_({a.subido_por for a in filas} or {0}))}
    fechas = {r.id: r.fecha.isoformat() for r in lote.registros}
    return {"secciones": SECCIONES, "editable": lote.estado == "ACTIVO", "adjuntos": [_a_dict(a, nombres, fechas) for a in filas]}


@router.post("/api/lotes/{lote_id}/adjuntos")
async def agregar(
    lote_id: int,
    seccion: str = Form(...),
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(gestor_lote),
):
    lote = _lote_del_usuario(db, lote_id, usuario)
    if lote.estado != "ACTIVO":
        raise HTTPException(status_code=400, detail="El lote está cerrado: sus evidencias ya no se pueden cambiar")
    if seccion in SECCIONES_REGISTRO:
        raise HTTPException(status_code=400, detail="Las evidencias de bajas, consumo y pesaje se adjuntan en el registro del día")
    return _a_dict(await _guardar(db, archivo, seccion, usuario, lote))


def _adjunto_del_usuario(db: Session, adjunto_id: int, usuario: Usuario) -> AdjuntoLote:
    adjunto = db.get(AdjuntoLote, adjunto_id)
    if adjunto is None or adjunto.organizacion_id != organizacion_de(usuario):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return adjunto


@router.get("/api/adjuntos/{adjunto_id}/archivo")
def descargar(adjunto_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(personal_cliente)):
    adjunto = _adjunto_del_usuario(db, adjunto_id, usuario)
    ruta = carpeta() / adjunto.ruta
    if not ruta.exists():
        raise HTTPException(status_code=404, detail="El archivo ya no está disponible")
    return FileResponse(ruta, media_type=adjunto.tipo, filename=adjunto.nombre)


@router.delete("/api/adjuntos/{adjunto_id}")
def eliminar(adjunto_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(quien_adjunta)):
    adjunto = _adjunto_del_usuario(db, adjunto_id, usuario)
    # El operario y el veterinario solo quitan lo que acaban de subir, antes de guardarlo.
    if usuario.rol in ("OPERARIO", "VETERINARIO") and not (adjunto.lote_id is None and adjunto.subido_por == usuario.id):
        raise HTTPException(status_code=403, detail="Tu cuenta no tiene permiso para esta acción")
    if adjunto.lote_id is not None:
        lote = db.get(Lote, adjunto.lote_id)
        if lote.estado != "ACTIVO":
            raise HTTPException(status_code=400, detail="El lote está cerrado: sus evidencias ya no se pueden cambiar")
        if adjunto.seccion == "GUIA":
            guias = db.query(AdjuntoLote).filter(AdjuntoLote.lote_id == lote.id, AdjuntoLote.seccion == "GUIA").count()
            if guias <= 1:
                raise HTTPException(status_code=400, detail="La guía de remisión es obligatoria: agrega otra antes de quitar esta")
    (carpeta() / adjunto.ruta).unlink(missing_ok=True)
    db.delete(adjunto)
    db.commit()
    return {"ok": True}


def resumen(db: Session, lote_id: int) -> list[tuple[str, int]]:
    """(sección, cantidad) para los reportes."""
    filas = db.query(AdjuntoLote).filter(AdjuntoLote.lote_id == lote_id).all()
    return [(nombre, sum(1 for a in filas if a.seccion == clave)) for clave, nombre in SECCIONES.items() if any(a.seccion == clave for a in filas)]
