"""Eliminación definitiva de un cliente: respaldo completo de la base, exportación de sus datos y borrado."""
import json
import os
import re
import sqlite3
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from .logic import clave_umbral
from .models import (
    Alerta,
    CambioAlimento,
    CierreLote,
    Configuracion,
    FaseAlimento,
    Galpon,
    Granja,
    IntentoLogin,
    IntentoRecuperacion,
    LecturaAmbiental,
    Lote,
    Organizacion,
    RegistroDiario,
    SolicitudContacto,
    Tratamiento,
    Usuario,
    Vacunacion,
)

# Campos que no salen en la exportación: son secretos, no datos del cliente.
OCULTOS = {"password_hash", "reset_token_hash", "reset_expira", "telegram_codigo", "telegram_codigo_expira"}


def carpeta_respaldos() -> Path:
    carpeta = Path(os.getenv("AVISMART_RESPALDOS") or Path(__file__).resolve().parent.parent / "respaldos")
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


def _etiqueta(nombre: str) -> str:
    limpio = re.sub(r"[^a-z0-9]+", "_", nombre.lower()).strip("_")
    return (limpio or "cliente")[:40] + "_" + datetime.now().strftime("%Y%m%d_%H%M%S")


def _fila(objeto) -> dict:
    datos = {}
    for columna in inspect(objeto).mapper.column_attrs:
        if columna.key in OCULTOS:
            continue
        valor = getattr(objeto, columna.key)
        datos[columna.key] = valor.isoformat() if isinstance(valor, (date, datetime)) else valor
    return datos


def _ids(db: Session, organizacion_id: int) -> dict:
    granjas = [g.id for g in db.query(Granja.id).filter(Granja.organizacion_id == organizacion_id)]
    galpones = [g.id for g in db.query(Galpon.id).filter(Galpon.granja_id.in_(granjas))] if granjas else []
    lotes = [l.id for l in db.query(Lote.id).filter(Lote.galpon_id.in_(galpones))] if galpones else []
    return {"granjas": granjas, "galpones": galpones, "lotes": lotes}


def _consultas(db: Session, organizacion: Organizacion) -> dict:
    """Todo lo que pertenece al cliente, tabla por tabla, en orden de borrado seguro."""
    ids = _ids(db, organizacion.id)
    por_lote = lambda modelo: db.query(modelo).filter(modelo.lote_id.in_(ids["lotes"] or [0]))  # noqa: E731
    usuarios = db.query(Usuario).filter(Usuario.organizacion_id == organizacion.id)
    correos = [u.email for u in usuarios]
    return {
        "alertas": por_lote(Alerta),
        "fases_alimento": por_lote(FaseAlimento),
        "cambios_alimento": por_lote(CambioAlimento),
        "registros_diarios": por_lote(RegistroDiario),
        "vacunaciones": por_lote(Vacunacion),
        "tratamientos": por_lote(Tratamiento),
        "cierres_lote": por_lote(CierreLote),
        "lecturas_ambientales": db.query(LecturaAmbiental).filter(LecturaAmbiental.galpon_id.in_(ids["galpones"] or [0])),
        "lotes": db.query(Lote).filter(Lote.id.in_(ids["lotes"] or [0])),
        "galpones": db.query(Galpon).filter(Galpon.id.in_(ids["galpones"] or [0])),
        "granjas": db.query(Granja).filter(Granja.id.in_(ids["granjas"] or [0])),
        "intentos_login": db.query(IntentoLogin).filter(IntentoLogin.email.in_(correos or [""])),
        "intentos_recuperacion": db.query(IntentoRecuperacion).filter(IntentoRecuperacion.email.in_(correos or [""])),
        "usuarios": usuarios,
        "configuracion": db.query(Configuracion).filter(Configuracion.clave == clave_umbral(organizacion.id)),
    }


def exportar(db: Session, organizacion: Organizacion) -> dict:
    tablas = {nombre: [_fila(o) for o in consulta.all()] for nombre, consulta in _consultas(db, organizacion).items()}
    tablas.pop("intentos_login")
    tablas.pop("intentos_recuperacion")
    return {
        "sistema": "AviSmart",
        "tipo": "exportacion_de_cliente",
        "exportado_en": datetime.now().isoformat(timespec="seconds"),
        "cliente": _fila(organizacion),
        "tablas": tablas,
    }


def respaldar_base(db: Session, etiqueta: str) -> Path:
    """Copia completa y consistente de la base SQLite, aunque esté en uso."""
    destino = carpeta_respaldos() / f"avismart_antes_eliminar_{etiqueta}.db"
    origen = db.connection().connection.driver_connection
    copia = sqlite3.connect(destino)
    try:
        origen.backup(copia)
    finally:
        copia.close()
    return destino


def eliminar(db: Session, organizacion: Organizacion) -> dict:
    """Respalda, exporta y borra el cliente. Devuelve la exportación y los nombres de los archivos."""
    etiqueta = _etiqueta(organizacion.nombre)
    respaldo = respaldar_base(db, etiqueta)
    datos = exportar(db, organizacion)
    carpeta = carpeta_respaldos() / "clientes"
    carpeta.mkdir(exist_ok=True)
    exportacion = carpeta / f"cliente_{etiqueta}.json"
    exportacion.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")

    for consulta in _consultas(db, organizacion).values():
        consulta.delete(synchronize_session=False)
    if organizacion.solicitud_id:
        solicitud = db.get(SolicitudContacto, organizacion.solicitud_id)
        if solicitud is not None and solicitud.estado == "CLIENTE":
            solicitud.estado = "BAJA"
            solicitud.atendida_en = datetime.now()
    db.delete(organizacion)
    db.commit()
    return {"respaldo": respaldo.name, "exportacion": exportacion.name, "datos": datos}
