import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .db import get_db
from .models import Organizacion, Usuario

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

SECRET = os.getenv("AVISMART_JWT_SECRET") or secrets.token_urlsafe(48)
ALGO = "HS256"
bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split("$", 1)
    except ValueError:
        return False
    check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000).hex()
    return secrets.compare_digest(check, digest)


HORAS_SOPORTE = 4


class UsuarioSoporte:
    """La cuenta de plataforma dentro de un cliente, con los permisos de su productor.

    No es una fila de la base: lo que registra queda a nombre de la persona real de la plataforma
    (su id), y su clave no se puede cambiar desde aquí.
    """

    soporte = True

    def __init__(self, real: Usuario, organizacion: Organizacion):
        self.real = real
        self.id = real.id
        self.nombre = real.nombre
        self.email = real.email
        self.rol = "PRODUCTOR"
        self.activo = 1
        self.debe_cambiar_clave = 0
        self.version_sesion = real.version_sesion
        self.organizacion_id = organizacion.id
        self.organizacion = organizacion


def create_token(usuario: Usuario, soporte_org: int | None = None) -> str:
    payload = {
        "sub": str(usuario.id),
        "rol": usuario.rol,
        "ver": usuario.version_sesion or 0,
        "exp": datetime.now(timezone.utc) + timedelta(hours=HORAS_SOPORTE if soporte_org else 12),
    }
    if soporte_org:
        payload["sop"] = soporte_org
    return jwt.encode(payload, SECRET, algorithm=ALGO)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> Usuario:
    if creds is None:
        raise HTTPException(status_code=401, detail="Inicia sesión para continuar")
    try:
        payload = jwt.decode(creds.credentials, SECRET, algorithms=[ALGO])
        user_id = int(payload["sub"])
        version = int(payload.get("ver", 0))
    except (jwt.PyJWTError, KeyError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Tu sesión expiró. Vuelve a iniciar sesión")
    usuario = db.get(Usuario, user_id)
    if usuario is None or not usuario.activo:
        raise HTTPException(status_code=401, detail="Tu sesión expiró. Vuelve a iniciar sesión")
    if version != (usuario.version_sesion or 0):
        # La clave cambió después de abrir esta sesión.
        raise HTTPException(status_code=401, detail="Tu sesión se cerró porque la clave cambió. Vuelve a entrar")
    if payload.get("sop"):
        # Modo soporte: solo una cuenta de plataforma puede entrar a un cliente.
        organizacion = db.get(Organizacion, int(payload["sop"])) if usuario.rol == "PLATAFORMA" else None
        if organizacion is None:
            raise HTTPException(status_code=401, detail="El modo soporte terminó. Vuelve a entrar desde la ficha del cliente")
        return UsuarioSoporte(usuario, organizacion)
    if organizacion_suspendida(usuario):
        raise HTTPException(status_code=401, detail="El acceso de tu empresa está suspendido. Comunícate con AviSmart")
    return usuario


# Tope = largo de las claves que sugiere Google Chrome (15); las temporales de AviSmart tienen 14.
CLAVE_MIN, CLAVE_MAX = 8, 15


def problema_con_clave_nueva(clave: str) -> str | None:
    """Mismas reglas que muestra la pantalla: largo, letras, números y símbolos, y nada de caracteres repetidos."""
    if len(clave) < CLAVE_MIN:
        return f"La clave debe tener al menos {CLAVE_MIN} caracteres"
    if len(clave) > CLAVE_MAX:
        return f"La clave puede tener como máximo {CLAVE_MAX} caracteres"
    if clave != clave.strip():
        return "La clave no puede empezar ni terminar con espacios"
    if not any(c.isalpha() for c in clave) or not any(c.isdigit() for c in clave):
        return "La clave debe combinar letras, números y símbolos"
    if not any(not c.isalnum() and not c.isspace() for c in clave):
        return "La clave debe incluir al menos un símbolo (por ejemplo # . - @)"
    if len(set(clave.lower())) < 5:
        return "La clave repite demasiado los mismos caracteres. Usa al menos 5 distintos"
    if any(clave[i] == clave[i + 1] == clave[i + 2] == clave[i + 3] for i in range(len(clave) - 3)):
        return "La clave no puede repetir el mismo carácter más de 3 veces seguidas"
    return None


def establecer_clave(usuario: Usuario, clave: str, temporal: bool) -> None:
    """Guarda la clave y cierra todas las sesiones abiertas de la cuenta."""
    usuario.password_hash = hash_password(clave)
    usuario.debe_cambiar_clave = 1 if temporal else 0
    usuario.version_sesion = (usuario.version_sesion or 0) + 1
    usuario.reset_token_hash = None
    usuario.reset_expira = None


def organizacion_suspendida(usuario: Usuario) -> bool:
    return usuario.organizacion is not None and usuario.organizacion.estado != "ACTIVA"


def get_ready_user(usuario: Usuario = Depends(get_current_user)) -> Usuario:
    if usuario.debe_cambiar_clave:
        raise HTTPException(status_code=403, detail="Cambia tu clave temporal antes de continuar")
    return usuario


def organizacion_de(usuario: Usuario) -> int:
    """Organización del usuario cliente. Las cuentas de plataforma no operan granjas avícolas."""
    if usuario.organizacion_id is None:
        raise HTTPException(status_code=403, detail="Esta sección es para las cuentas de una granja cliente")
    return usuario.organizacion_id


def require(*roles: str):
    def checker(usuario: Usuario = Depends(get_ready_user)) -> Usuario:
        if usuario.rol not in roles:
            raise HTTPException(status_code=403, detail="Tu cuenta no tiene permiso para esta acción")
        return usuario

    return checker
