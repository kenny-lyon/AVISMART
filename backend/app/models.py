from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Organizacion(Base):
    """Cliente de AviSmart. Sus usuarios y granjas avícolas solo ven sus propios datos."""

    __tablename__ = "organizaciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(160))
    estado: Mapped[str] = mapped_column(String(20), default="ACTIVA")
    creada_en: Mapped[datetime] = mapped_column(DateTime)
    solicitud_id: Mapped[int | None] = mapped_column(ForeignKey("solicitudes_contacto.id"), nullable=True)
    # Chat de Telegram propio del cliente (sus alertas solo van ahí).
    telegram_chat_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    telegram_chat_nombre: Mapped[str | None] = mapped_column(String(120), nullable=True)
    telegram_vinculado_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    telegram_codigo: Mapped[str | None] = mapped_column(String(20), nullable=True)
    telegram_codigo_expira: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    usuarios: Mapped[list["Usuario"]] = relationship(back_populates="organizacion")
    granjas: Mapped[list["Granja"]] = relationship(back_populates="organizacion")


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    rol: Mapped[str] = mapped_column(String(20))
    activo: Mapped[int] = mapped_column(Integer, default=1)
    debe_cambiar_clave: Mapped[int] = mapped_column(Integer, default=0)
    # Sube cada vez que cambia la clave: invalida todas las sesiones abiertas.
    version_sesion: Mapped[int] = mapped_column(Integer, default=0)
    # Recuperación "¿Olvidaste tu clave?": se guarda solo el hash del enlace.
    reset_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    reset_expira: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Vacío solo para las cuentas PLATAFORMA (propietario de AviSmart).
    organizacion_id: Mapped[int | None] = mapped_column(ForeignKey("organizaciones.id"), nullable=True, index=True)

    organizacion: Mapped[Organizacion | None] = relationship(back_populates="usuarios")
    registros: Mapped[list["RegistroDiario"]] = relationship(back_populates="usuario")


class IntentoLogin(Base):
    """Intentos fallidos de ingreso, para bloquear temporalmente la adivinación de claves."""

    __tablename__ = "intentos_login"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(160), index=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime, index=True)


class IntentoRecuperacion(Base):
    """Registro de pedidos de "¿Olvidaste tu clave?" para limitar abusos."""

    __tablename__ = "intentos_recuperacion"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(160), index=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime, index=True)


class SolicitudContacto(Base):
    __tablename__ = "solicitudes_contacto"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160), index=True)
    telefono: Mapped[str | None] = mapped_column(String(20), nullable=True)
    empresa: Mapped[str] = mapped_column(String(160), default="")
    pais: Mapped[str] = mapped_column(String(80))
    aves: Mapped[str] = mapped_column(String(60), default="")
    motivo: Mapped[str] = mapped_column(String(40))
    plan: Mapped[str] = mapped_column(String(40), default="POR_DEFINIR")
    mensaje: Mapped[str] = mapped_column(Text)
    # PENDIENTE (sin confirmar el correo) · NUEVA (verificada) · CONTACTADA · CLIENTE · DESCARTADA · SOSPECHOSA
    # · BAJA (fue cliente y ese cliente se eliminó)
    estado: Mapped[str] = mapped_column(String(20), default="NUEVA")
    creada_en: Mapped[datetime] = mapped_column(DateTime)
    atendida_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    token_expira: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    confirmacion_enviada: Mapped[int] = mapped_column(Integer, default=0)
    verificada_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    motivo_sospecha: Mapped[str | None] = mapped_column(String(120), nullable=True)


class Granja(Base):
    __tablename__ = "granjas"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(160))
    ubicacion: Mapped[str] = mapped_column(String(160))
    # Ubigeo y punto exacto en el mapa (vacíos en granjas antiguas).
    departamento: Mapped[str | None] = mapped_column(String(60), nullable=True)
    provincia: Mapped[str | None] = mapped_column(String(80), nullable=True)
    distrito: Mapped[str | None] = mapped_column(String(80), nullable=True)
    latitud: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitud: Mapped[float | None] = mapped_column(Float, nullable=True)
    organizacion_id: Mapped[int | None] = mapped_column(ForeignKey("organizaciones.id"), nullable=True, index=True)
    organizacion: Mapped[Organizacion | None] = relationship(back_populates="granjas")
    galpones: Mapped[list["Galpon"]] = relationship(back_populates="granja")


class Galpon(Base):
    __tablename__ = "galpones"

    id: Mapped[int] = mapped_column(primary_key=True)
    granja_id: Mapped[int] = mapped_column(ForeignKey("granjas.id"))
    nombre: Mapped[str] = mapped_column(String(120))
    capacidad: Mapped[int] = mapped_column(Integer)
    camara_nombre: Mapped[str] = mapped_column(String(120), default="Cámara principal")
    camara_modo: Mapped[str] = mapped_column(String(20), default="SIMULADA")
    camara_activa: Mapped[int] = mapped_column(Integer, default=1)
    granja: Mapped[Granja] = relationship(back_populates="galpones")
    lotes: Mapped[list["Lote"]] = relationship(back_populates="galpon")
    lecturas: Mapped[list["LecturaAmbiental"]] = relationship(back_populates="galpon")


class Lote(Base):
    __tablename__ = "lotes"

    id: Mapped[int] = mapped_column(primary_key=True)
    galpon_id: Mapped[int] = mapped_column(ForeignKey("galpones.id"))
    linea: Mapped[str] = mapped_column(String(20))
    fecha_ingreso: Mapped[date] = mapped_column(Date)
    poblacion_inicial: Mapped[int] = mapped_column(Integer)
    peso_objetivo_g: Mapped[int] = mapped_column(Integer, default=2800)
    # Recepción de los pollitos (vacíos en lotes antiguos).
    proveedor: Mapped[str | None] = mapped_column(String(120), nullable=True)
    guia: Mapped[str | None] = mapped_column(String(60), nullable=True)
    sexo: Mapped[str | None] = mapped_column(String(10), nullable=True)
    cantidad_recibida: Mapped[int | None] = mapped_column(Integer, nullable=True)
    descarte_llegada: Mapped[int | None] = mapped_column(Integer, nullable=True)
    peso_llegada_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    precio_pollito: Mapped[float | None] = mapped_column(Float, nullable=True)
    edad_saca_dias: Mapped[int | None] = mapped_column(Integer, nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    estado: Mapped[str] = mapped_column(String(20), default="ACTIVO")
    fecha_cierre: Mapped[date | None] = mapped_column(Date, nullable=True)
    galpon: Mapped[Galpon] = relationship(back_populates="lotes")
    registros: Mapped[list["RegistroDiario"]] = relationship(back_populates="lote")
    vacunas: Mapped[list["Vacunacion"]] = relationship(back_populates="lote")
    tratamientos: Mapped[list["Tratamiento"]] = relationship(back_populates="lote")
    alertas: Mapped[list["Alerta"]] = relationship(back_populates="lote")
    cierre: Mapped["CierreLote | None"] = relationship(back_populates="lote", uselist=False)


class CierreLote(Base):
    __tablename__ = "cierres_lote"

    id: Mapped[int] = mapped_column(primary_key=True)
    lote_id: Mapped[int] = mapped_column(ForeignKey("lotes.id"), unique=True)
    fecha_cierre: Mapped[date] = mapped_column(Date)
    aves_vendidas: Mapped[int] = mapped_column(Integer)
    peso_total_kg: Mapped[float] = mapped_column(Float)
    precio_venta_kg: Mapped[float] = mapped_column(Float)
    ingreso_total: Mapped[float] = mapped_column(Float)
    costo_pollitos: Mapped[float] = mapped_column(Float)
    costo_alimento: Mapped[float] = mapped_column(Float)
    costo_sanidad: Mapped[float] = mapped_column(Float)
    otros_costos: Mapped[float] = mapped_column(Float)
    total_costos: Mapped[float] = mapped_column(Float)
    margen: Mapped[float] = mapped_column(Float)
    observaciones: Mapped[str] = mapped_column(Text, default="")
    cerrado_por: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime)

    lote: Mapped[Lote] = relationship(back_populates="cierre")


class RegistroDiario(Base):
    __tablename__ = "registros_diarios"
    __table_args__ = (UniqueConstraint("lote_id", "fecha", name="uq_registro_lote_fecha"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    lote_id: Mapped[int] = mapped_column(ForeignKey("lotes.id"))
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    fecha: Mapped[date] = mapped_column(Date)
    mortalidad: Mapped[int] = mapped_column(Integer)
    alimento_kg: Mapped[float] = mapped_column(Float)
    agua_l: Mapped[float] = mapped_column(Float)
    peso_muestra_g: Mapped[float] = mapped_column(Float)
    # Fase de alimento que se dio ese día (Preinicio, Inicio, Crecimiento, Acabado o Retiro).
    fase_alimento: Mapped[str | None] = mapped_column(String(30), nullable=True)
    lote: Mapped[Lote] = relationship(back_populates="registros")
    usuario: Mapped[Usuario] = relationship(back_populates="registros")


class Vacunacion(Base):
    __tablename__ = "vacunaciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    lote_id: Mapped[int] = mapped_column(ForeignKey("lotes.id"))
    nombre: Mapped[str] = mapped_column(String(120))
    fecha_programada: Mapped[date] = mapped_column(Date)
    # PENDIENTE (fecha propuesta) -> PROGRAMADA (fecha aprobada por el veterinario)
    # -> APLICADA (registrada por el personal) -> VALIDADA (conformidad del veterinario).
    # OBSERVADA: el veterinario no dio conformidad en alguna de las dos revisiones.
    estado: Mapped[str] = mapped_column(String(20), default="PENDIENTE")
    observacion: Mapped[str] = mapped_column(Text, default="")
    aprobada_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    fecha_aplicacion: Mapped[date | None] = mapped_column(Date, nullable=True)
    aplicada_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    nota_aplicacion: Mapped[str] = mapped_column(Text, default="")
    validado_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    lote: Mapped[Lote] = relationship(back_populates="vacunas")


class Tratamiento(Base):
    __tablename__ = "tratamientos"

    id: Mapped[int] = mapped_column(primary_key=True)
    lote_id: Mapped[int] = mapped_column(ForeignKey("lotes.id"))
    medicamento: Mapped[str] = mapped_column(String(120))
    dosis: Mapped[str] = mapped_column(String(80))
    via: Mapped[str] = mapped_column(String(40))
    fecha_inicio: Mapped[date] = mapped_column(Date)
    dias_tratamiento: Mapped[int] = mapped_column(Integer)
    dias_carencia: Mapped[int] = mapped_column(Integer)
    aves_tratadas: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estado: Mapped[str] = mapped_column(String(20), default="PENDIENTE")
    diagnostico: Mapped[str] = mapped_column(Text, default="")
    validado_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    # Tratamiento indicado por el veterinario (estado INDICADO hasta que el personal lo inicia).
    indicado_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    iniciado_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    lote: Mapped[Lote] = relationship(back_populates="tratamientos")


class LecturaAmbiental(Base):
    __tablename__ = "lecturas_ambientales"

    id: Mapped[int] = mapped_column(primary_key=True)
    galpon_id: Mapped[int] = mapped_column(ForeignKey("galpones.id"))
    fecha_hora: Mapped[datetime] = mapped_column(DateTime)
    temperatura: Mapped[float] = mapped_column(Float)
    humedad: Mapped[float] = mapped_column(Float)
    origen: Mapped[str] = mapped_column(String(20), default="SIMULADO")
    galpon: Mapped[Galpon] = relationship(back_populates="lecturas")


class Alerta(Base):
    __tablename__ = "alertas"

    id: Mapped[int] = mapped_column(primary_key=True)
    lote_id: Mapped[int] = mapped_column(ForeignKey("lotes.id"))
    tipo: Mapped[str] = mapped_column(String(30))
    mensaje: Mapped[str] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(String(20), default="NUEVA")
    requiere_veterinario: Mapped[int] = mapped_column(Integer, default=0)
    observacion: Mapped[str] = mapped_column(Text, default="")
    creada_en: Mapped[datetime] = mapped_column(DateTime)
    # Recordatorios de vacuna: a qué vacuna pertenecen (antes se buscaban por el nombre).
    vacuna_id: Mapped[int | None] = mapped_column(ForeignKey("vacunaciones.id"), nullable=True, index=True)
    # Aviso al personal de un tratamiento indicado por el veterinario.
    tratamiento_id: Mapped[int | None] = mapped_column(ForeignKey("tratamientos.id"), nullable=True, index=True)
    atendida_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    notificacion_estado: Mapped[str] = mapped_column(String(20), default="PENDIENTE")
    notificacion_error: Mapped[str] = mapped_column(Text, default="")
    notificada_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    lote: Mapped[Lote] = relationship(back_populates="alertas")


class Configuracion(Base):
    __tablename__ = "configuracion"

    clave: Mapped[str] = mapped_column(String(80), primary_key=True)
    valor: Mapped[str] = mapped_column(String(80))


class FaseAlimento(Base):
    """Plan de alimentación del lote: qué alimento corresponde a cada rango de días."""

    __tablename__ = "fases_alimento"

    id: Mapped[int] = mapped_column(primary_key=True)
    lote_id: Mapped[int] = mapped_column(ForeignKey("lotes.id"), index=True)
    nombre: Mapped[str] = mapped_column(String(30))
    dia_desde: Mapped[int] = mapped_column(Integer)
    dia_hasta: Mapped[int] = mapped_column(Integer)
    presentacion: Mapped[str] = mapped_column(String(40), default="")
    producto: Mapped[str] = mapped_column(String(120), default="")


class CambioAlimento(Base):
    """Historial de variaciones del plan de alimentación (quién, cuándo y por qué)."""

    __tablename__ = "cambios_alimento"

    id: Mapped[int] = mapped_column(primary_key=True)
    lote_id: Mapped[int] = mapped_column(ForeignKey("lotes.id"), index=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    fecha: Mapped[datetime] = mapped_column(DateTime)
    motivo: Mapped[str] = mapped_column(Text)
    detalle: Mapped[str] = mapped_column(Text, default="")
