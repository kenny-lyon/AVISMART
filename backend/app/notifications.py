import json
import os
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from sqlalchemy.orm import Session

from .models import Alerta

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def estado_telegram() -> dict:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    return {
        "canal": "Telegram",
        "configurado": bool(token and chat_id),
        "chat_configurado": bool(chat_id),
    }


def _enviar(texto: str) -> tuple[bool, str]:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return False, "Telegram no está configurado"

    solicitud = Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps({"chat_id": chat_id, "text": texto}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(solicitud, timeout=6) as respuesta:
            contenido = json.loads(respuesta.read().decode("utf-8"))
        if contenido.get("ok"):
            return True, ""
        return False, str(contenido.get("description", "Telegram rechazó el mensaje"))[:500]
    except HTTPError as error:
        try:
            detalle = json.loads(error.read().decode("utf-8")).get("description", str(error))
        except Exception:
            detalle = str(error)
        return False, detalle[:500]
    except (URLError, TimeoutError, OSError) as error:
        return False, str(error)[:500]


def notificar_alertas(db: Session, alertas: list[Alerta]) -> None:
    configurado = estado_telegram()["configurado"]
    for alerta in alertas:
        if alerta.notificacion_estado == "ENVIADA":
            continue
        if not configurado:
            alerta.notificacion_estado = "NO_CONFIGURADA"
            alerta.notificacion_error = "Telegram no está configurado"
            continue
        lote = alerta.lote
        texto = (
            "AviSmart — Alerta\n\n"
            f"Lote: {lote.linea} · {lote.galpon.nombre}\n"
            f"Tipo: {alerta.tipo}\n"
            f"{alerta.mensaje}"
        )
        ok, error = _enviar(texto)
        alerta.notificacion_estado = "ENVIADA" if ok else "FALLIDA"
        alerta.notificacion_error = error
        alerta.notificada_en = datetime.now() if ok else None
    db.commit()


def probar_telegram() -> tuple[bool, str]:
    return _enviar("AviSmart — Mensaje de prueba\n\nEl canal de alertas está conectado correctamente.")
