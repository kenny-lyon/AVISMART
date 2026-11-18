"""Sensores IoT del galpón (M7): lecturas y fotos enviadas por el equipo del galpón (ESP32 o el simulador).

Cada galpón puede tener un sensor con su propia clave. La clave se muestra una sola vez y se guarda como resumen
(SHA-256). El equipo envía sus lecturas a POST /api/iot/lecturas con la cabecera X-Sensor-Clave; la lectura se guarda
con el clima de la zona y, si el galpón tiene un lote activo, pasa por las mismas reglas de ambiente que una lectura manual.
CO2, amoníaco y agua son opcionales: cada equipo envía lo que tenga conectado. Las fotos llegan a POST /api/iot/fotos.
"""
import hashlib
import secrets
import uuid
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from . import clima_local, evidencias
from .db import get_db
from .logic import evaluar_clima
from .models import FotoGalpon, Galpon, Granja, LecturaAmbiental, Lote, Usuario
from .notifications import notificar_alertas
from .security import organizacion_de, require

router = APIRouter()
gestor = require("ADMIN", "PRODUCTOR")
cliente = require("ADMIN", "PRODUCTOR", "OPERARIO", "VETERINARIO")

INTERVALO_MINIMO = timedelta(seconds=50)  # un envío por minuto por galpón
MINUTOS_EN_LINEA = 10  # sin lecturas en este tiempo, el sensor figura «sin señal»
MAX_FOTOS_GALPON = 20_000  # al superarlas se borran las más antiguas


class LecturaSensorIn(BaseModel):
    temperatura: float = Field(ge=-10, le=50)
    humedad: float = Field(ge=0, le=100)
    co2_ppm: float | None = Field(default=None, ge=0, le=20_000)
    nh3_ppm: float | None = Field(default=None, ge=0, le=500)
    agua_l: float | None = Field(default=None, ge=0, le=5_000)  # litros desde el envío anterior


def _resumen(clave: str) -> str:
    return hashlib.sha256(clave.encode()).hexdigest()


def estado(galpon: Galpon) -> dict:
    """Estado del sensor para las pantallas: activo, en línea y último envío."""
    ultimo = galpon.sensor_ultimo_envio
    return {
        "activo": bool(galpon.sensor_clave_hash),
        "en_linea": bool(galpon.sensor_clave_hash and ultimo and datetime.now() - ultimo < timedelta(minutes=MINUTOS_EN_LINEA)),
        "ultimo_envio": ultimo.isoformat(timespec="seconds") if ultimo else None,
    }


def _galpon_del_usuario(db: Session, galpon_id: int, usuario: Usuario) -> Galpon:
    galpon = (
        db.query(Galpon).join(Granja, Galpon.granja_id == Granja.id)
        .filter(Galpon.id == galpon_id, Granja.organizacion_id == organizacion_de(usuario)).first()
    )
    if galpon is None:
        raise HTTPException(status_code=404, detail="Galpón no encontrado")
    return galpon


@router.post("/api/galpones/{galpon_id}/sensor")
def activar(galpon_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(gestor)):
    """Genera la clave del sensor (reemplaza la anterior). Se muestra una sola vez."""
    galpon = _galpon_del_usuario(db, galpon_id, usuario)
    clave = "avs_" + secrets.token_urlsafe(24)
    galpon.sensor_clave_hash = _resumen(clave)
    galpon.sensor_ultimo_envio = None
    db.commit()
    return {"clave": clave, "ruta": "/api/iot/lecturas", "sensor": estado(galpon)}


@router.delete("/api/galpones/{galpon_id}/sensor")
def desactivar(galpon_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(gestor)):
    galpon = _galpon_del_usuario(db, galpon_id, usuario)
    galpon.sensor_clave_hash = None
    db.commit()
    return {"sensor": estado(galpon)}


def _galpon_de_la_clave(db: Session, clave: str) -> Galpon:
    galpon = db.query(Galpon).filter(Galpon.sensor_clave_hash == _resumen(clave)).first() if clave else None
    if galpon is None:
        raise HTTPException(status_code=401, detail="Clave de sensor no válida")
    return galpon


def agua_de_hoy(db: Session, galpon_id: int) -> float | None:
    """Litros que contó el medidor del galpón hoy; None si no tiene medidor."""
    litros = [
        l.agua_l for l in db.query(LecturaAmbiental).filter(
            LecturaAmbiental.galpon_id == galpon_id, LecturaAmbiental.agua_l.isnot(None),
            LecturaAmbiental.fecha_hora >= datetime.combine(date.today(), time.min),
        )
    ]
    return round(sum(litros), 1) if litros else None


def ultima_foto(db: Session, galpon_id: int) -> dict | None:
    foto = db.query(FotoGalpon).filter(FotoGalpon.galpon_id == galpon_id).order_by(FotoGalpon.fecha_hora.desc()).first()
    return {"fecha_hora": foto.fecha_hora.isoformat(timespec="seconds")} if foto else None


@router.post("/api/iot/fotos", status_code=201)
async def recibir_foto(archivo: UploadFile = File(...), x_sensor_clave: str = Header(default="", max_length=100), db: Session = Depends(get_db)):
    """Foto periódica de la cámara del galpón. Con la misma clave del sensor."""
    galpon = _galpon_de_la_clave(db, x_sensor_clave)
    ahora = datetime.now()
    ultima = db.query(FotoGalpon).filter(FotoGalpon.galpon_id == galpon.id).order_by(FotoGalpon.fecha_hora.desc()).first()
    if ultima and ahora - ultima.fecha_hora < INTERVALO_MINIMO:
        raise HTTPException(status_code=429, detail="Envía como máximo una foto por minuto")
    contenido = await archivo.read(evidencias.MAX_BYTES + 1)
    if len(contenido) > evidencias.MAX_BYTES:
        raise HTTPException(status_code=400, detail="Cada foto puede pesar como máximo 5 MB")
    tipo = evidencias._tipo_real(contenido)
    if tipo is None or not tipo.startswith("image/"):
        raise HTTPException(status_code=400, detail="Solo se aceptan fotos JPG, PNG o WEBP")
    ruta = f"org_{galpon.granja.organizacion_id}/camara/{galpon.id}/{uuid.uuid4().hex}{evidencias.EXTENSION[tipo]}"
    destino = evidencias.carpeta() / ruta
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(contenido)
    lote = db.query(Lote).filter(Lote.galpon_id == galpon.id, Lote.estado == "ACTIVO").first()
    db.add(FotoGalpon(galpon_id=galpon.id, lote_id=lote.id if lote else None, fecha_hora=ahora, ruta=ruta, tipo=tipo))
    db.flush()
    sobrantes = db.query(FotoGalpon).filter(FotoGalpon.galpon_id == galpon.id).order_by(FotoGalpon.fecha_hora.desc()).offset(MAX_FOTOS_GALPON).all()
    for vieja in sobrantes:
        (evidencias.carpeta() / vieja.ruta).unlink(missing_ok=True)
        db.delete(vieja)
    db.commit()
    return {"ok": True}


@router.get("/api/lotes/{lote_id}/camara/foto")
def ver_foto(lote_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(cliente)):
    """Última foto del galpón del lote."""
    lote = evidencias._lote_del_usuario(db, lote_id, usuario)
    foto = db.query(FotoGalpon).filter(FotoGalpon.galpon_id == lote.galpon_id).order_by(FotoGalpon.fecha_hora.desc()).first()
    ruta = evidencias.carpeta() / foto.ruta if foto else None
    if ruta is None or not ruta.exists():
        raise HTTPException(status_code=404, detail="Todavía no hay fotos de este galpón")
    return FileResponse(ruta, media_type=foto.tipo)


@router.post("/api/iot/lecturas")
def recibir(body: LecturaSensorIn, x_sensor_clave: str = Header(default="", max_length=100), db: Session = Depends(get_db)):
    """Lectura enviada por el equipo del galpón."""
    galpon = _galpon_de_la_clave(db, x_sensor_clave)
    ahora = datetime.now()
    if galpon.sensor_ultimo_envio and ahora - galpon.sensor_ultimo_envio < INTERVALO_MINIMO:
        raise HTTPException(status_code=429, detail="Envía como máximo una lectura por minuto")
    granja = galpon.granja
    exterior = clima_local.consultar(granja.latitud, granja.longitud)
    lectura = LecturaAmbiental(
        galpon_id=galpon.id,
        fecha_hora=ahora.replace(microsecond=0),
        temperatura=body.temperatura,
        humedad=body.humedad,
        origen="SENSOR",
        temp_exterior=exterior["temperatura"] if exterior else None,
        humedad_exterior=exterior["humedad"] if exterior else None,
        co2_ppm=body.co2_ppm,
        nh3_ppm=body.nh3_ppm,
        agua_l=body.agua_l,
    )
    db.add(lectura)
    galpon.sensor_ultimo_envio = ahora
    db.flush()
    lote = db.query(Lote).filter(Lote.galpon_id == galpon.id, Lote.estado == "ACTIVO").first()
    nuevas = evaluar_clima(db, lote, lectura) if lote else []
    db.commit()
    notificar_alertas(db, nuevas)
    return {"ok": True, "lote_activo": lote is not None, "alertas": [a.mensaje for a in nuevas]}
