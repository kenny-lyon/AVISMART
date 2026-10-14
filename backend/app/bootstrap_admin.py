import argparse
import secrets

from .db import Base, SessionLocal, engine, ensure_schema
from .models import Usuario
from .security import hash_password


def main() -> None:
    parser = argparse.ArgumentParser(description="Crea una cuenta de Propietario de la plataforma AviSmart.")
    parser.add_argument("--nombre", required=True)
    parser.add_argument("--email", required=True)
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    ensure_schema()
    db = SessionLocal()
    try:
        email = args.email.strip().lower()
        if db.query(Usuario).filter(Usuario.email == email).first():
            raise SystemExit("Ya existe una cuenta con ese correo.")
        clave = secrets.token_urlsafe(10)
        usuario = Usuario(
            nombre=args.nombre.strip(),
            email=email,
            password_hash=hash_password(clave),
            rol="PLATAFORMA",
            organizacion_id=None,
            activo=1,
            debe_cambiar_clave=1,
        )
        db.add(usuario)
        db.commit()
        print("Cuenta de Propietario de la plataforma creada.")
        print(f"Correo: {email}")
        print(f"Clave temporal (se muestra una sola vez): {clave}")
        print("El usuario deberá cambiarla al ingresar.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
