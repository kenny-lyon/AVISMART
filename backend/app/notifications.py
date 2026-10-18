"""Avisos por Telegram.

Un solo bot de AviSmart (TELEGRAM_BOT_TOKEN). Cada cliente vincula su propio chat y solo recibe
las alertas de sus lotes. TELEGRAM_CHAT_ID es el canal de la plataforma (avisos de solicitudes),
nunca recibe alertas de los clientes.
"""
import json
import os
import secrets
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from sqlalchemy.orm import Session

from .models import Alerta, Organizacion

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

MINUTOS_CODIGO = 30
TIPOS = {"SALUD": "Salud", "RECORDATORIO": "Vacuna", "AMBIENTE": "Ambiente", "CRECIMIENTO": "Crecimiento"}


def _token() -> str:
    return os.getenv("TELEGRAM_BOT_TOKEN", "").strip()


def _chat_plataforma() -> str:
    return os.getenv("TELEGRAM_CHAT_ID", "").strip()


def bot_configurado() -> bool:
    return bool(_token())


def _llamar(metodo: str, datos: dict | None = None) -> tuple[bool, dict | str]:
    """Llama a la API de Telegram. Devuelve (ok, resultado) o (False, mensaje de error)."""
    token = _token()
    if not token:
        return False, "El bot de Telegram no está configurado"
    solicitud = Request(
        f"https://api.telegram.org/bot{token}/{metodo}",
        data=json.dumps(datos or {}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(solicitud, timeout=8) as respuesta:
            contenido = json.loads(respuesta.read().decode("utf-8"))
        if contenido.get("ok"):
            return True, contenido.get("result")
        return False, str(contenido.get("description", "Telegram rechazó el pedido"))[:500]
    except HTTPError as error:
        try:
            detalle = json.loads(error.read().decode("utf-8")).get("description", str(error))
        except Exception:
            detalle = str(error)
        return False, str(detalle)[:500]
    except (URLError, TimeoutError, OSError) as error:
        return False, str(error)[:500]


def _enviar(texto: str, chat_id: str) -> tuple[bool, str]:
    if not chat_id:
        return False, "No hay un chat de Telegram vinculado"
    ok, resultado = _llamar("sendMessage", {"chat_id": chat_id, "text": texto})
    return (True, "") if ok else (False, str(resultado))


@lru_cache(maxsize=1)
def _usuario_bot_cache(token: str) -> str | None:
    ok, resultado = _llamar("getMe")
    return resultado.get("username") if ok and isinstance(resultado, dict) else None


def usuario_bot() -> str | None:
    return _usuario_bot_cache(_token()) if bot_configurado() else None


# ------------------------------------------------------------------ alertas de clientes
def _organizacion_de(alerta: Alerta) -> Organizacion | None:
    granja = alerta.lote.galpon.granja if alerta.lote and alerta.lote.galpon else None
    return granja.organizacion if granja else None


def notificar_alertas(db: Session, alertas: list[Alerta]) -> None:
    for alerta in alertas:
        if alerta.notificacion_estado == "ENVIADA":
            continue
        organizacion = _organizacion_de(alerta)
        chat = organizacion.telegram_chat_id if organizacion else None
        if not bot_configurado() or not chat:
            alerta.notificacion_estado = "NO_CONFIGURADA"
            alerta.notificacion_error = "El bot no está configurado" if not bot_configurado() else "El cliente no vinculó su chat de Telegram"
            continue
        lote = alerta.lote
        texto = (
            f"AviSmart — Alerta de {TIPOS.get(alerta.tipo, alerta.tipo).lower()}\n\n"
            f"{lote.galpon.granja.nombre} · {lote.galpon.nombre} · {lote.linea}\n"
            f"{alerta.mensaje}"
        )
        ok, error = _enviar(texto, chat)
        alerta.notificacion_estado = "ENVIADA" if ok else "FALLIDA"
        alerta.notificacion_error = error
        alerta.notificada_en = datetime.now() if ok else None
    db.commit()


# ------------------------------------------------------------------ vinculación de un cliente
def estado_organizacion(organizacion: Organizacion) -> dict:
    return {
        "bot_configurado": bot_configurado(),
        "bot_usuario": usuario_bot(),
        "vinculado": bool(organizacion.telegram_chat_id),
        "chat_nombre": organizacion.telegram_chat_nombre,
        "vinculado_en": organizacion.telegram_vinculado_en.isoformat(timespec="minutes") if organizacion.telegram_vinculado_en else None,
    }


def generar_codigo(organizacion: Organizacion) -> dict:
    codigo = "AVI" + secrets.token_hex(4).upper()
    organizacion.telegram_codigo = codigo
    organizacion.telegram_codigo_expira = datetime.now() + timedelta(minutes=MINUTOS_CODIGO)
    bot = usuario_bot()
    return {
        "codigo": codigo,
        "minutos": MINUTOS_CODIGO,
        "bot_usuario": bot,
        "enlace": f"https://t.me/{bot}?start={codigo}" if bot else None,
    }


def verificar_codigo(organizacion: Organizacion) -> tuple[bool, str]:
    """Busca en los mensajes recientes del bot el código del cliente y guarda ese chat."""
    codigo = organizacion.telegram_codigo
    if not codigo or not organizacion.telegram_codigo_expira or organizacion.telegram_codigo_expira < datetime.now():
        return False, "El código venció o no existe. Genera uno nuevo"
    ok, actualizaciones = _llamar("getUpdates", {"allowed_updates": ["message"], "limit": 100})
    if not ok:
        return False, f"No se pudo consultar Telegram: {actualizaciones}"
    for actualizacion in reversed(actualizaciones or []):
        mensaje = actualizacion.get("message") or {}
        if codigo in (mensaje.get("text") or ""):
            chat = mensaje.get("chat") or {}
            organizacion.telegram_chat_id = str(chat.get("id"))
            organizacion.telegram_chat_nombre = (chat.get("title") or " ".join(
                x for x in (chat.get("first_name"), chat.get("last_name")) if x
            ) or chat.get("username") or "Chat de Telegram")[:120]
            organizacion.telegram_vinculado_en = datetime.now()
            organizacion.telegram_codigo = None
            organizacion.telegram_codigo_expira = None
            _enviar(f"AviSmart: este chat quedó vinculado a {organizacion.nombre}. Aquí llegarán las alertas de tus lotes.", organizacion.telegram_chat_id)
            return True, organizacion.telegram_chat_nombre
    return False, "Todavía no vemos el código en Telegram. Envíalo al bot y vuelve a intentar"


def probar_organizacion(organizacion: Organizacion) -> tuple[bool, str]:
    return _enviar(f"AviSmart — Mensaje de prueba\n\nLas alertas de {organizacion.nombre} llegan a este chat.", organizacion.telegram_chat_id or "")


# ------------------------------------------------------------------ canal de la plataforma
def estado_telegram() -> dict:
    return {
        "canal": "Telegram",
        "configurado": bool(_token() and _chat_plataforma()),
        "chat_configurado": bool(_chat_plataforma()),
    }


def probar_telegram() -> tuple[bool, str]:
    return _enviar("AviSmart — Mensaje de prueba\n\nEl canal de la plataforma está conectado.", _chat_plataforma())


def avisar_plataforma(texto: str) -> bool:
    if not (_token() and _chat_plataforma()):
        return False
    ok, _ = _enviar(texto, _chat_plataforma())
    return ok
