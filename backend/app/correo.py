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
from html import escape
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


def telefono_emergencia() -> str:
    return os.getenv("AVISMART_TELEFONO_EMERGENCIA", "931113015").strip()


def enviar_aviso_cambio(destino: str, nombre: str, cuando: str = "", ip: str | None = None) -> bool:
    """Aviso de seguridad después de cambiar o restablecer la clave, con cómo pedir ayuda."""
    numero = telefono_emergencia()
    visible = f"{numero[:3]} {numero[3:6]} {numero[6:]}" if len(numero) == 9 else numero
    whatsapp = f"https://wa.me/51{numero}"
    contacto = f"{url_publica()}/contacto"
    detalle = f"Fecha: {cuando}" + (f" · Conexión: {ip}" if ip else "")
    return _enviar(
        destino,
        "Tu clave de AviSmart fue cambiada",
        f"Hola {nombre}:\n\nLa clave de tu cuenta de AviSmart se cambió y se cerraron todas las sesiones abiertas.\n{detalle}\n\n"
        "Si no fuiste tú:\n"
        f"1. Escríbenos de inmediato por WhatsApp al {visible} ({whatsapp}) o desde el formulario de Contacto ({contacto}), con el motivo «Soporte técnico».\n"
        "2. Cambia también la clave de tu correo: quien cambió tu clave pudo haber entrado a él.\n"
        "Verificaremos tu identidad, cerraremos el acceso y te daremos una clave nueva.",
        _html(
            "Tu clave fue cambiada",
            f"<p>Hola {nombre}:</p><p>La clave de tu cuenta de AviSmart se cambió y se cerraron todas las sesiones abiertas.</p>"
            f'<p style="color:#637069;font-size:13px">{detalle}</p>'
            "<p><b>Si no fuiste tú:</b></p><ol>"
            f'<li>Escríbenos de inmediato por WhatsApp al <a href="{whatsapp}"><b>{visible}</b></a> o desde el '
            f'<a href="{contacto}">formulario de Contacto</a>, con el motivo «Soporte técnico».</li>'
            "<li>Cambia también la clave de tu correo: quien cambió tu clave pudo haber entrado a él.</li></ol>"
            "<p>Verificaremos tu identidad, cerraremos el acceso y te daremos una clave nueva.</p>",
        ),
    )


def enviar_acceso(destino: str, nombre: str, clave: str, empresa: str | None = None, restablecida: bool = False) -> bool:
    """Datos de acceso con la clave temporal: al entrar, el sistema le pide crear su propia clave."""
    enlace = f"{url_publica()}/login"
    nombre_h, empresa_h = escape(nombre), escape(empresa or "")
    if restablecida:
        asunto = "Tu clave de AviSmart fue restablecida"
        intro = "Se restableció la clave de tu cuenta en AviSmart. Estos son tus nuevos datos de acceso:"
    else:
        asunto = "Bienvenido a AviSmart: tus datos de acceso"
        intro = f"Ya tienes tu cuenta en AviSmart{f' para {empresa}' if empresa else ''}. Estos son tus datos de acceso:"
        intro_h = f"Ya tienes tu cuenta en AviSmart{f' para <b>{empresa_h}</b>' if empresa else ''}. Estos son tus datos de acceso:"
    return _enviar(
        destino,
        asunto,
        f"Hola {nombre}:\n\n{intro}\n\nCorreo: {destino}\nClave temporal: {clave}\n\nEntra en: {enlace}\n\n"
        "La clave temporal sirve solo para el primer ingreso: al entrar, el sistema te pedirá crear tu propia clave.\n"
        f"Si no esperabas este correo, llámanos al {telefono_emergencia()}.",
        _html(
            "Clave restablecida" if restablecida else "Bienvenido a AviSmart",
            f"<p>Hola {nombre_h}:</p><p>{intro if restablecida else intro_h}</p>"
            '<table style="border-collapse:collapse;margin:8px 0 4px">'
            f'<tr><td style="padding:4px 12px 4px 0;color:#637069">Correo</td><td><b>{escape(destino)}</b></td></tr>'
            f'<tr><td style="padding:4px 12px 4px 0;color:#637069">Clave temporal</td>'
            f'<td><b style="font-family:Consolas,monospace;font-size:16px;letter-spacing:1px">{escape(clave)}</b></td></tr></table>'
            f"{_boton(enlace, 'Entrar a AviSmart')}"
            '<p style="color:#637069;font-size:13px">La clave temporal sirve solo para el primer ingreso: al entrar, el sistema te pedirá '
            f"crear tu propia clave. Si no esperabas este correo, llámanos al {telefono_emergencia()}.</p>",
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
