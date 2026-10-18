from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "avismart.db"

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def ensure_schema() -> None:
    """Agrega columnas nuevas en SQLite sin borrar la base existente."""
    with engine.begin() as conn:
        usuario_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(usuarios)")).fetchall()}
        if "debe_cambiar_clave" not in usuario_cols:
            conn.execute(text("ALTER TABLE usuarios ADD COLUMN debe_cambiar_clave INTEGER DEFAULT 0"))
        for columna, tipo in (("version_sesion", "INTEGER DEFAULT 0"), ("reset_token_hash", "VARCHAR(64)"), ("reset_expira", "DATETIME")):
            if columna not in usuario_cols:
                conn.execute(text(f"ALTER TABLE usuarios ADD COLUMN {columna} {tipo}"))
        # La versión actual unifica al propietario y al administrador de granja.
        conn.execute(text("UPDATE usuarios SET rol = 'ADMIN' WHERE rol = 'SUPERADMIN'"))
        # El rol del personal de galpón pasó a llamarse OPERARIO (antes OPERATIVO).
        conn.execute(text("UPDATE usuarios SET rol = 'OPERARIO' WHERE rol = 'OPERATIVO'"))
        conn.execute(
            text(
                "UPDATE usuarios SET email = 'operario@avismart.local' WHERE email = 'operativo@avismart.local' "
                "AND NOT EXISTS (SELECT 1 FROM usuarios WHERE email = 'operario@avismart.local')"
            )
        )
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(galpones)")).fetchall()}
        if "camara_nombre" not in cols:
            conn.execute(text("ALTER TABLE galpones ADD COLUMN camara_nombre VARCHAR(120) DEFAULT 'Cámara principal'"))
        if "camara_modo" not in cols:
            conn.execute(text("ALTER TABLE galpones ADD COLUMN camara_modo VARCHAR(20) DEFAULT 'SIMULADA'"))
        if "camara_activa" not in cols:
            conn.execute(text("ALTER TABLE galpones ADD COLUMN camara_activa INTEGER DEFAULT 1"))
        lote_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(lotes)")).fetchall()}
        if "fecha_cierre" not in lote_cols:
            conn.execute(text("ALTER TABLE lotes ADD COLUMN fecha_cierre DATE"))
        for columna, tipo in (
            ("proveedor", "VARCHAR(120)"),
            ("guia", "VARCHAR(60)"),
            ("sexo", "VARCHAR(10)"),
            ("cantidad_recibida", "INTEGER"),
            ("descarte_llegada", "INTEGER"),
            ("peso_llegada_g", "FLOAT"),
            ("precio_pollito", "FLOAT"),
            ("edad_saca_dias", "INTEGER"),
            ("observaciones", "TEXT"),
        ):
            if columna not in lote_cols:
                conn.execute(text(f"ALTER TABLE lotes ADD COLUMN {columna} {tipo}"))
        alerta_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(alertas)")).fetchall()}
        if "notificacion_estado" not in alerta_cols:
            conn.execute(text("ALTER TABLE alertas ADD COLUMN notificacion_estado VARCHAR(20) DEFAULT 'PENDIENTE'"))
        if "notificacion_error" not in alerta_cols:
            conn.execute(text("ALTER TABLE alertas ADD COLUMN notificacion_error TEXT DEFAULT ''"))
        if "notificada_en" not in alerta_cols:
            conn.execute(text("ALTER TABLE alertas ADD COLUMN notificada_en DATETIME"))
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_registro_lote_fecha "
                "ON registros_diarios (lote_id, fecha)"
            )
        )
        org_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(organizaciones)")).fetchall()}
        for columna, tipo in (
            ("telegram_chat_id", "VARCHAR(40)"),
            ("telegram_chat_nombre", "VARCHAR(120)"),
            ("telegram_vinculado_en", "DATETIME"),
            ("telegram_codigo", "VARCHAR(20)"),
            ("telegram_codigo_expira", "DATETIME"),
        ):
            if org_cols and columna not in org_cols:
                conn.execute(text(f"ALTER TABLE organizaciones ADD COLUMN {columna} {tipo}"))
        vacuna_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(vacunaciones)")).fetchall()}
        for columna, tipo in (
            ("aprobada_por", "INTEGER"),
            ("fecha_aplicacion", "DATE"),
            ("aplicada_por", "INTEGER"),
            ("nota_aplicacion", "TEXT DEFAULT ''"),
        ):
            if vacuna_cols and columna not in vacuna_cols:
                conn.execute(text(f"ALTER TABLE vacunaciones ADD COLUMN {columna} {tipo}"))
        alerta_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(alertas)")).fetchall()}
        if alerta_cols and "vacuna_id" not in alerta_cols:
            conn.execute(text("ALTER TABLE alertas ADD COLUMN vacuna_id INTEGER REFERENCES vacunaciones(id)"))
            # Vincula los recordatorios antiguos con su vacuna por el texto exacto del mensaje.
            vacunas = conn.execute(text("SELECT id, lote_id, nombre FROM vacunaciones")).fetchall()
            for alerta_id, lote_id, mensaje in conn.execute(
                text("SELECT id, lote_id, mensaje FROM alertas WHERE tipo = 'RECORDATORIO'")
            ).fetchall():
                candidatas = [v for v in vacunas if v[1] == lote_id and mensaje.startswith(f"La vacuna {v[2]} debía")]
                if candidatas:
                    elegida = max(candidatas, key=lambda v: len(v[2]))
                    conn.execute(text("UPDATE alertas SET vacuna_id = :v WHERE id = :a"), {"v": elegida[0], "a": alerta_id})
        solicitud_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(solicitudes_contacto)")).fetchall()}
        for columna, tipo in (
            ("ip", "VARCHAR(64)"),
            ("token_hash", "VARCHAR(64)"),
            ("token_expira", "DATETIME"),
            ("confirmacion_enviada", "INTEGER DEFAULT 0"),
            ("verificada_en", "DATETIME"),
            ("motivo_sospecha", "VARCHAR(120)"),
        ):
            if solicitud_cols and columna not in solicitud_cols:
                conn.execute(text(f"ALTER TABLE solicitudes_contacto ADD COLUMN {columna} {tipo}"))
        usuario_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(usuarios)")).fetchall()}
        if "organizacion_id" not in usuario_cols:
            conn.execute(text("ALTER TABLE usuarios ADD COLUMN organizacion_id INTEGER REFERENCES organizaciones(id)"))
        granja_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(granjas)")).fetchall()}
        if "organizacion_id" not in granja_cols:
            conn.execute(text("ALTER TABLE granjas ADD COLUMN organizacion_id INTEGER REFERENCES organizaciones(id)"))
        # Los datos creados antes de separar clientes pasan a una organización "Demostración".
        sueltos = conn.execute(
            text(
                "SELECT (SELECT COUNT(*) FROM usuarios WHERE organizacion_id IS NULL AND rol <> 'PLATAFORMA')"
                " + (SELECT COUNT(*) FROM granjas WHERE organizacion_id IS NULL)"
            )
        ).scalar()
        if sueltos:
            org_id = conn.execute(text("SELECT id FROM organizaciones WHERE nombre = 'Demostración'")).scalar()
            if org_id is None:
                org_id = conn.execute(
                    text(
                        "INSERT INTO organizaciones (nombre, estado, creada_en) "
                        "VALUES ('Demostración', 'ACTIVA', datetime('now', 'localtime')) RETURNING id"
                    )
                ).scalar()
            conn.execute(
                text("UPDATE usuarios SET organizacion_id = :org WHERE organizacion_id IS NULL AND rol <> 'PLATAFORMA'"),
                {"org": org_id},
            )
            conn.execute(text("UPDATE granjas SET organizacion_id = :org WHERE organizacion_id IS NULL"), {"org": org_id})


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
