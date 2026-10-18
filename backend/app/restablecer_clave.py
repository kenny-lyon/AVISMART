"""Recuperación de emergencia desde el servidor (no depende del correo).

Uso:
    .\\.venv\\Scripts\\python.exe -m app.restablecer_clave --email propietario@dominio.com

Genera una clave temporal, la muestra una sola vez, obliga a cambiarla al entrar
y cierra todas las sesiones abiertas de la cuenta.
"""
import argparse
import secrets

from .db import Base, SessionLocal, engine, ensure_schema
from .models import Usuario
from .security import establecer_clave


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera una clave temporal nueva para una cuenta de AviSmart.")
    parser.add_argument("--email", required=True)
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    ensure_schema()
    db = SessionLocal()
    try:
        email = args.email.strip().lower()
        usuario = db.query(Usuario).filter(Usuario.email == email).first()
        if usuario is None:
            raise SystemExit("No existe una cuenta con ese correo.")
        clave = secrets.token_urlsafe(10)
        establecer_clave(usuario, clave, temporal=True)
        usuario.activo = 1
        db.commit()
        print(f"Cuenta: {usuario.nombre} ({usuario.rol})")
        print(f"Correo: {email}")
        print(f"Clave temporal (se muestra una sola vez): {clave}")
        print("Deberá cambiarla al ingresar. Se cerraron todas sus sesiones abiertas.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
