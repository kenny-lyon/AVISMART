"""Envío del correo de confirmación de solicitudes de contacto.

Se configura en backend/.env con SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD y SMTP_FROM.
Sin esa configuración no se envía nada: el enlace queda en el registro del servidor y,
con AVISMART_DEV=true, también se devuelve al navegador para poder probar.
"""
import logging
import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
log = logging.getLogger("avismart.correo")


def smtp_configurado() -> bool:
    return all(os.getenv(k, "").strip() for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD"))


def modo_desarrollo() -> bool:
    return os.getenv("AVISMART_DEV", "false").lower() in ("1", "true", "si", "sí")


def url_publica() -> str:
    return os.getenv("AVISMART_URL_PUBLICA", "http://127.0.0.1:5173").rstrip("/")


def enlace_confirmacion(token: str) -> str:
    return f"{url_publica()}/confirmar?token={token}"


def _boton(enlace: str, texto: str) -> str:
    return (
        f'<p><a href="{enlace}" style="display:inline-block;padding:12px 20px;background:#f1c84b;color:#102f25;'
        f'text-decoration:none;border-radius:6px;font-weight:bold">{texto}</a></p>'
    )


def _html(titulo: str, cuerpo: str) -> str:
    return (
        '<div style="font-family:Arial,sans-serif;max-width:520px;color:#17231d">'
        f'<h2 style="color:#102f25">{titulo}</h2>{cuerpo}'
        '<p style="color:#637069;font-size:12px;margin-top:24px">AviSmart · Gestión avícola</p></div>'
    )


def enviar_confirmacion(destino: str, nombre: str, enlace: str, horas: int) -> bool:
    """Confirmación de una solicitud de contacto."""
    return _enviar(
        destino,
        "Confirma tu solicitud en AviSmart",
        f"Hola {nombre}:\n\nRecibimos tu solicitud de contacto en AviSmart. Para enviarla a nuestro equipo, "
        f"confirma tu correo abriendo este enlace (válido por {horas} horas):\n\n{enlace}\n\n"
        "Si no fuiste tú, ignora este mensaje: la solicitud se eliminará sola.",
        _html(
            "Confirma tu solicitud",
            f"<p>Hola {nombre}:</p><p>Recibimos tu solicitud de contacto en AviSmart. Para enviarla a nuestro equipo, "
            f"confirma tu correo:</p>{_boton(enlace, 'Confirmar mi correo')}"
            f'<p style="color:#637069;font-size:13px">El enlace vence en {horas} horas. Si no fuiste tú, ignora este mensaje.</p>',
        ),
        enlace,
    )


def enviar_recuperacion(destino: str, nombre: str, enlace: str, minutos: int) -> bool:
    """Enlace para crear una clave nueva."""
    return _enviar(
        destino,
        "Restablece tu clave de AviSmart",
        f"Hola {nombre}:\n\nRecibimos un pedido para restablecer tu clave de AviSmart. Para crear una nueva, "
        f"abre este enlace (válido por {minutos} minutos y de un solo uso):\n\n{enlace}\n\n"
        "Si no fuiste tú, ignora este mensaje: tu clave actual sigue funcionando.",
        _html(
            "Restablece tu clave",
            f"<p>Hola {nombre}:</p><p>Recibimos un pedido para restablecer tu clave de AviSmart.</p>"
            f"{_boton(enlace, 'Crear una clave nueva')}"
            f'<p style="color:#637069;font-size:13px">El enlace vence en {minutos} minutos y sirve una sola vez. '
            "Si no fuiste tú, ignora este mensaje: tu clave actual sigue funcionando.</p>",
        ),
        enlace,
    )


def enviar_aviso_cambio(destino: str, nombre: str) -> bool:
    """Aviso de seguridad después de restablecer la clave."""
    return _enviar(
        destino,
        "Tu clave de AviSmart fue cambiada",
        f"Hola {nombre}:\n\nLa clave de tu cuenta de AviSmart se cambió y se cerraron todas las sesiones abiertas.\n\n"
        "Si no fuiste tú, contacta de inmediato al equipo de AviSmart.",
        _html(
            "Tu clave fue cambiada",
            f"<p>Hola {nombre}:</p><p>La clave de tu cuenta de AviSmart se cambió y se cerraron todas las sesiones abiertas.</p>"
            "<p><b>Si no fuiste tú</b>, contacta de inmediato al equipo de AviSmart.</p>",
        ),
    )


def enviar_aviso_solicitud(destino: str, empresa: str, nombre: str, mensaje: str) -> bool:
    """Aviso a la plataforma: llegó una solicitud de contacto confirmada."""
    enlace = f"{url_publica()}/plataforma/solicitudes"
    return _enviar(
        destino,
        f"Nueva solicitud en AviSmart: {empresa}",
        f"{nombre} ({empresa}) confirmó su correo y su solicitud ya está en la bandeja.\n\n«{mensaje[:300]}»\n\nRevísala en: {enlace}",
        _html(
            "Nueva solicitud de contacto",
            f"<p><b>{nombre}</b> ({empresa}) confirmó su correo y su solicitud ya está en la bandeja.</p>"
            f'<p style="color:#637069">«{mensaje[:300]}»</p>{_boton(enlace, "Ver solicitudes")}',
        ),
    )


def _enviar(destino: str, asunto: str, texto: str, html: str, enlace: str | None = None) -> bool:
    """True si el correo salió. False si no hay SMTP o falló (el enlace queda en el log)."""
    if not smtp_configurado():
        if enlace:
            log.warning("SMTP sin configurar. %s para %s: %s", asunto, destino, enlace)
            print(f"[AviSmart] {asunto} para {destino}: {enlace}", flush=True)
        return False

    mensaje = EmailMessage()
    mensaje["Subject"] = asunto
    mensaje["From"] = os.getenv("SMTP_FROM", "").strip() or os.getenv("SMTP_USER", "")
    mensaje["To"] = destino
    mensaje.set_content(texto + "\n\nAviSmart · Gestión avícola")
    mensaje.add_alternative(html, subtype="html")
    puerto = int(os.getenv("SMTP_PORT", "587"))
    try:
        if puerto == 465:
            with smtplib.SMTP_SSL(os.environ["SMTP_HOST"], puerto, context=ssl.create_default_context(), timeout=15) as s:
                s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
                s.send_message(mensaje)
        else:
            with smtplib.SMTP(os.environ["SMTP_HOST"], puerto, timeout=15) as s:
                s.starttls(context=ssl.create_default_context())
                s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
                s.send_message(mensaje)
        return True
    except (smtplib.SMTPException, OSError) as error:
        log.error("No se pudo enviar «%s» a %s: %s", asunto, destino, error)
        print(f"[AviSmart] Falló el envío a {destino}: {error}." + (f" Enlace: {enlace}" if enlace else ""), flush=True)
        return False
