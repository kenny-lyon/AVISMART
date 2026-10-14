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
from .models import Usuario

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


def create_token(usuario: Usuario) -> str:
    payload = {
        "sub": str(usuario.id),
        "rol": usuario.rol,
        "exp": datetime.now(timezone.utc) + timedelta(hours=12),
    }
    return jwt.encode(payload, SECRET, algorithm=ALGO)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> Usuario:
    if creds is None:
        raise HTTPException(status_code=401, detail="Debe iniciar sesión")
    try:
        payload = jwt.decode(creds.credentials, SECRET, algorithms=[ALGO])
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Sesión inválida")
    usuario = db.get(Usuario, user_id)
    if usuario is None or not usuario.activo:
        raise HTTPException(status_code=401, detail="Sesión inválida")
    if organizacion_suspendida(usuario):
        raise HTTPException(status_code=401, detail="El acceso de su organización está suspendido")
    return usuario


def organizacion_suspendida(usuario: Usuario) -> bool:
    return usuario.organizacion is not None and usuario.organizacion.estado != "ACTIVA"


def get_ready_user(usuario: Usuario = Depends(get_current_user)) -> Usuario:
    if usuario.debe_cambiar_clave:
        raise HTTPException(status_code=403, detail="Debe cambiar la clave temporal antes de continuar")
    return usuario


def organizacion_de(usuario: Usuario) -> int:
    """Organización del usuario cliente. Las cuentas de plataforma no operan granjas avícolas."""
    if usuario.organizacion_id is None:
        raise HTTPException(status_code=403, detail="Esta sección es para las cuentas de una organización")
    return usuario.organizacion_id


def require(*roles: str):
    def checker(usuario: Usuario = Depends(get_ready_user)) -> Usuario:
        if usuario.rol not in roles:
            raise HTTPException(status_code=403, detail="No tiene permiso para esta acción")
        return usuario

    return checker
