"""Protecciones del formulario público de contacto.

Capas: formato y dominio del correo, Turnstile (antibots), límites de envío,
campo trampa (honeypot) y detección de contenido sospechoso. La confirmación
por correo está en correo.py.
"""
import json
import os
import re
from datetime import datetime, timedelta
from functools import lru_cache
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from sqlalchemy.orm import Session

from .models import SolicitudContacto

# Límites iniciales; ajustar según el tráfico real.
POR_IP_15_MIN = 3
POR_CORREO_DIA = 5
CONFIRMACIONES_POR_CORREO_DIA = 3
GLOBAL_POR_HORA = 60
HORAS_PARA_CONFIRMAR = 24
HORAS_HASTA_DEPURAR = 48

FORMATO = re.compile(r"^[a-z0-9](?:[a-z0-9._%+-]{0,62}[a-z0-9])?@(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,24}$")
DESECHABLES = {
    "mailinator.com", "10minutemail.com", "10minutemail.net", "guerrillamail.com", "guerrillamail.net",
    "sharklasers.com", "yopmail.com", "yopmail.net", "tempmail.com", "temp-mail.org", "trashmail.com",
    "getnada.com", "maildrop.cc", "dispostable.com", "throwawaymail.com", "fakeinbox.com", "mintemail.com",
    "mohmal.com", "emailondeck.com", "moakt.com", "tempail.com", "spamgourmet.com", "mailnesia.com",
}
ENLACE = re.compile(r"https?://|www\.", re.IGNORECASE)


def verificar_dns_activo() -> bool:
    return os.getenv("AVISMART_VERIFICAR_DNS", "true").lower() not in ("0", "false", "no")


def formato_valido(email: str) -> bool:
    return bool(FORMATO.match(email)) and ".." not in email


def es_desechable(email: str) -> bool:
    return email.rsplit("@", 1)[-1] in DESECHABLES


@lru_cache(maxsize=512)
def dominio_recibe_correo(dominio: str) -> bool | None:
    """True si el dominio tiene MX (o, en su defecto, una dirección A/AAAA).
    None si la consulta no pudo hacerse (sin internet): no se bloquea por eso."""
    import dns.exception
    import dns.resolver

    resolver = dns.resolver.Resolver()
    resolver.lifetime = 4
    try:
        respuesta = resolver.resolve(dominio, "MX")
        return any(str(r.exchange) not in (".", "") for r in respuesta)
    except (dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
        return False
    except dns.resolver.NoAnswer:
        for tipo in ("A", "AAAA"):
            try:
                resolver.resolve(dominio, tipo)
                return True
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
                continue
            except dns.exception.DNSException:
                return None
        return False
    except dns.exception.DNSException:
        return None


def problema_con_correo(email: str) -> str | None:
    """Mensaje para el usuario si el correo no sirve; None si está bien."""
    if not formato_valido(email):
        return "El correo no tiene un formato válido"
    if es_desechable(email):
        return "No se aceptan correos temporales o desechables"
    if verificar_dns_activo() and dominio_recibe_correo(email.rsplit("@", 1)[1]) is False:
        return "El dominio del correo no existe o no recibe mensajes. Revisa que esté bien escrito"
    return None


# ------------------------------------------------------------------ Turnstile
def turnstile_sitekey() -> str | None:
    return os.getenv("TURNSTILE_SITE_KEY", "").strip() or None


def turnstile_valido(token: str, ip: str | None) -> bool:
    """Se verifica siempre en el servidor. Sin TURNSTILE_SECRET_KEY la capa queda desactivada."""
    secreto = os.getenv("TURNSTILE_SECRET_KEY", "").strip()
    if not secreto:
        return True
    if not token:
        return False
    datos = {"secret": secreto, "response": token}
    if ip:
        datos["remoteip"] = ip
    try:
        solicitud = Request(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data=urlencode(datos).encode(),
            method="POST",
        )
        with urlopen(solicitud, timeout=8) as r:
            return bool(json.loads(r.read().decode()).get("success"))
    except (URLError, TimeoutError, OSError, ValueError):
        return False


# ------------------------------------------------------------- Límites
def limite_superado(db: Session, ip: str | None, email: str) -> str | None:
    ahora = datetime.now()
    consulta = db.query(SolicitudContacto)
    if ip and consulta.filter(SolicitudContacto.ip == ip, SolicitudContacto.creada_en >= ahora - timedelta(minutes=15)).count() >= POR_IP_15_MIN:
        return "Enviaste varias solicitudes seguidas. Intenta de nuevo en unos minutos"
    if consulta.filter(SolicitudContacto.email == email, SolicitudContacto.creada_en >= ahora - timedelta(days=1)).count() >= POR_CORREO_DIA:
        return "Este correo ya envió el máximo de solicitudes por hoy"
    if consulta.filter(SolicitudContacto.creada_en >= ahora - timedelta(hours=1)).count() >= GLOBAL_POR_HORA:
        return "Estamos recibiendo muchas solicitudes. Intenta de nuevo más tarde"
    return None


def confirmaciones_agotadas(db: Session, email: str) -> bool:
    """Evita usar el formulario para bombardear la bandeja de un tercero."""
    desde = datetime.now() - timedelta(days=1)
    enviadas = (
        db.query(SolicitudContacto)
        .filter(SolicitudContacto.email == email, SolicitudContacto.creada_en >= desde, SolicitudContacto.confirmacion_enviada == 1)
        .count()
    )
    return enviadas >= CONFIRMACIONES_POR_CORREO_DIA


# ------------------------------------------------------- Contenido sospechoso
def _normalizar(texto: str) -> str:
    return re.sub(r"[^a-z0-9áéíóúñ]+", " ", texto.lower()).strip()


def parece_texto_sin_sentido(texto: str) -> bool:
    letras = re.sub(r"[^a-záéíóúñ]", "", texto.lower())
    if len(letras) < 8:
        return False
    vocales = sum(c in "aeiouáéíóú" for c in letras)
    palabra_larga = any(len(p) > 30 for p in texto.split())
    repetido = re.search(r"(.)\1{6,}", texto) is not None
    return vocales / len(letras) < 0.2 or palabra_larga or repetido


def motivo_sospecha(db: Session, nombre: str, mensaje: str, honeypot: str) -> str | None:
    if honeypot.strip():
        return "Campo trampa completado (posible bot)"
    if len(ENLACE.findall(mensaje)) >= 2:
        return "Mensaje con varios enlaces"
    if parece_texto_sin_sentido(mensaje) or parece_texto_sin_sentido(nombre):
        return "Texto sin sentido"
    normal = _normalizar(mensaje)
    desde = datetime.now() - timedelta(days=1)
    recientes = db.query(SolicitudContacto.mensaje).filter(SolicitudContacto.creada_en >= desde).all()
    if sum(_normalizar(m) == normal for (m,) in recientes) >= 2:
        return "Mensaje repetido en varias solicitudes"
    return None


def depurar_pendientes(db: Session) -> int:
    """Borra las solicitudes que nunca confirmaron su correo."""
    limite = datetime.now() - timedelta(hours=HORAS_HASTA_DEPURAR)
    return (
        db.query(SolicitudContacto)
        .filter(SolicitudContacto.estado == "PENDIENTE", SolicitudContacto.creada_en < limite)
        .delete(synchronize_session=False)
    )
