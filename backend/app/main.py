import os
import secrets
from datetime import date, datetime

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from . import catalogo
from .db import Base, SessionLocal, engine, ensure_schema, get_db
from .logic import (
    carencias_activas,
    clave_umbral,
    cerrar_recordatorios_vacuna,
    dia_vida,
    evaluar_clima,
    evaluar_registro,
    evaluar_vacunas_vencidas,
    fechas_tratamiento,
    indicadores,
    umbral_mortalidad,
)
from .models import (
    Alerta,
    CierreLote,
    Configuracion,
    Galpon,
    Granja,
    LecturaAmbiental,
    Lote,
    Organizacion,
    RegistroDiario,
    SolicitudContacto,
    Tratamiento,
    Usuario,
    Vacunacion,
)
from .notifications import estado_telegram, notificar_alertas, probar_telegram
from .security import (
    create_token,
    get_current_user,
    hash_password,
    organizacion_de,
    organizacion_suspendida,
    require,
    verify_password,
)
from .seed import asegurar_tratamiento_demo, seed


def _arranque():
    Base.metadata.create_all(bind=engine)
    ensure_schema()
    db = SessionLocal()
    try:
        if os.getenv("AVISMART_DEMO", "false").lower() in ("1", "true", "si", "sí"):
            seed(db)
            asegurar_tratamiento_demo(db)
        nuevas = evaluar_vacunas_vencidas(db)
        db.commit()
        notificar_alertas(db, nuevas)
    finally:
        db.close()


_arranque()

app = FastAPI(title="AviSmart")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LoginIn(BaseModel):
    email: str
    password: str


class LoteIn(BaseModel):
    galpon_id: int
    linea: str
    fecha_ingreso: date
    proveedor: str = Field(min_length=2, max_length=120)
    guia: str = Field(default="", max_length=60)
    sexo: str = "MIXTO"
    cantidad_recibida: int = Field(gt=0, le=200_000)
    descarte_llegada: int = Field(default=0, ge=0)
    peso_llegada_g: float = Field(ge=25, le=70)
    precio_pollito: float = Field(ge=0, le=50)
    peso_objetivo_g: int = Field(default=2800, ge=1000, le=5000)
    edad_saca_dias: int = Field(default=42, ge=21, le=70)
    observaciones: str = Field(default="", max_length=1000)


class RegistroIn(BaseModel):
    fecha: date
    mortalidad: int = Field(ge=0)
    alimento_kg: float = Field(ge=0)
    agua_l: float = Field(ge=0)
    peso_muestra_g: float = Field(gt=0)


class ClimaIn(BaseModel):
    temperatura: float
    humedad: float = Field(ge=0, le=100)


class VacunaIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    fecha_programada: date


class TratamientoIn(BaseModel):
    medicamento: str = Field(min_length=2, max_length=120)
    dosis: str = Field(min_length=1, max_length=80)
    via: str
    fecha_inicio: date
    dias_tratamiento: int = Field(ge=1, le=30)
    dias_carencia: int = Field(ge=0, le=60)
    aves_tratadas: int | None = Field(default=None, ge=1)


class ValidarIn(BaseModel):
    decision: str
    observacion: str = ""


class UmbralIn(BaseModel):
    mortalidad_diaria: int = Field(ge=1, le=500)


class CierreIn(BaseModel):
    fecha_cierre: date
    aves_vendidas: int = Field(gt=0)
    peso_total_kg: float = Field(gt=0)
    precio_venta_kg: float = Field(gt=0)
    costo_pollitos: float = Field(ge=0)
    costo_alimento: float = Field(ge=0)
    costo_sanidad: float = Field(ge=0)
    otros_costos: float = Field(default=0, ge=0)
    observaciones: str = Field(default="", max_length=1000)


class CambioClaveIn(BaseModel):
    clave_actual: str
    clave_nueva: str = Field(min_length=10, max_length=128)


class UsuarioCrearIn(BaseModel):
    nombre: str = Field(min_length=3, max_length=120)
    email: str = Field(min_length=5, max_length=160)
    rol: str


class UsuarioEstadoIn(BaseModel):
    activo: bool


class ContactoIn(BaseModel):
    nombre: str = Field(min_length=3, max_length=120)
    email: str = Field(min_length=5, max_length=160)
    empresa: str = Field(default="", max_length=160)
    pais: str = Field(min_length=2, max_length=80)
    aves: str = Field(default="", max_length=60)
    motivo: str = Field(min_length=2, max_length=40)
    plan: str = Field(default="POR_DEFINIR", max_length=40)
    mensaje: str = Field(min_length=10, max_length=1500)


class SolicitudEstadoIn(BaseModel):
    estado: str


class GranjaIn(BaseModel):
    nombre: str = Field(min_length=3, max_length=160)
    ubicacion: str = Field(min_length=2, max_length=160)


class GalponIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    capacidad: int = Field(gt=0, le=200_000)


class OrganizacionIn(BaseModel):
    nombre: str = Field(min_length=3, max_length=160)
    productor_nombre: str = Field(min_length=3, max_length=120)
    productor_email: str = Field(min_length=5, max_length=160)
    solicitud_id: int | None = None


class OrganizacionEstadoIn(BaseModel):
    estado: str


ROLES_CLIENTE = ("ADMIN", "PRODUCTOR", "OPERATIVO", "VETERINARIO")
ROLES_PERSONAL = ("PRODUCTOR", "OPERATIVO", "VETERINARIO")
cliente = require(*ROLES_CLIENTE)

# Qué cuentas puede crear y gestionar cada rol. ADMIN solo existe en organizaciones antiguas (Demostración).
CREA = {
    "PLATAFORMA": ("PLATAFORMA",),
    "ADMIN": ROLES_PERSONAL,
    "PRODUCTOR": ("OPERATIVO", "VETERINARIO"),
}
GESTIONA = {
    "PLATAFORMA": ("PLATAFORMA",),
    "ADMIN": ("ADMIN",) + ROLES_PERSONAL,
    "PRODUCTOR": ("OPERATIVO", "VETERINARIO"),
}
# Desde la ficha de un cliente, la plataforma gestiona a todo su personal.
PLATAFORMA_CREA_EN_CLIENTE = ROLES_PERSONAL
PLATAFORMA_GESTIONA_EN_CLIENTE = ROLES_CLIENTE
# Roles de los que siempre debe quedar al menos una cuenta activa en su ámbito.
ROLES_RESPONSABLES = ("PLATAFORMA", "ADMIN", "PRODUCTOR")


def _usuario(u: Usuario) -> dict:
    return {
        "id": u.id,
        "nombre": u.nombre,
        "email": u.email,
        "rol": u.rol,
        "activo": bool(u.activo),
        "debe_cambiar_clave": bool(u.debe_cambiar_clave),
        "organizacion": (
            {"id": u.organizacion.id, "nombre": u.organizacion.nombre} if u.organizacion else None
        ),
    }


def _galpon(g: Galpon) -> dict:
    return {"id": g.id, "nombre": g.nombre, "capacidad": g.capacidad, "granja_id": g.granja_id, "granja": g.granja.nombre}


def _granja(g: Granja) -> dict:
    return {
        "id": g.id,
        "nombre": g.nombre,
        "ubicacion": g.ubicacion,
        "galpones": [_galpon(x) for x in sorted(g.galpones, key=lambda x: x.id)],
    }


def _organizacion(db: Session, o: Organizacion) -> dict:
    granja_ids = [g.id for g in o.granjas]
    lotes_activos = (
        db.query(Lote).join(Galpon).filter(Galpon.granja_id.in_(granja_ids), Lote.estado == "ACTIVO").count()
        if granja_ids
        else 0
    )
    return {
        "id": o.id,
        "nombre": o.nombre,
        "estado": o.estado,
        "creada_en": o.creada_en.isoformat(timespec="minutes") if o.creada_en else None,
        "solicitud_id": o.solicitud_id,
        "usuarios_activos": sum(1 for u in o.usuarios if u.activo),
        "granjas": len(o.granjas),
        "lotes_activos": lotes_activos,
        "responsables": [
            _usuario(u) for u in sorted(o.usuarios, key=lambda u: (u.rol != "PRODUCTOR", u.id)) if u.rol in ("PRODUCTOR", "ADMIN")
        ],
        "personal": {rol: sum(1 for u in o.usuarios if u.rol == rol and u.activo) for rol in ROLES_PERSONAL},
    }


def _solicitud(s: SolicitudContacto) -> dict:
    return {
        "id": s.id,
        "nombre": s.nombre,
        "email": s.email,
        "empresa": s.empresa,
        "pais": s.pais,
        "aves": s.aves,
        "motivo": s.motivo,
        "plan": s.plan,
        "mensaje": s.mensaje,
        "estado": s.estado,
        "creada_en": s.creada_en.isoformat(timespec="minutes"),
        "atendida_en": s.atendida_en.isoformat(timespec="minutes") if s.atendida_en else None,
    }


def _lote(lote: Lote) -> dict:
    return {
        "id": lote.id,
        "linea": lote.linea,
        "fecha_ingreso": lote.fecha_ingreso.isoformat(),
        "poblacion_inicial": lote.poblacion_inicial,
        "peso_objetivo_g": lote.peso_objetivo_g,
        "proveedor": lote.proveedor,
        "guia": lote.guia,
        "sexo": lote.sexo,
        "cantidad_recibida": lote.cantidad_recibida,
        "descarte_llegada": lote.descarte_llegada,
        "peso_llegada_g": lote.peso_llegada_g,
        "precio_pollito": lote.precio_pollito,
        "costo_pollitos": round(lote.precio_pollito * (lote.cantidad_recibida or lote.poblacion_inicial), 2) if lote.precio_pollito is not None else None,
        "edad_saca_dias": lote.edad_saca_dias,
        "observaciones": lote.observaciones,
        "estado": lote.estado,
        "fecha_cierre": lote.fecha_cierre.isoformat() if lote.fecha_cierre else None,
        "dia_vida": dia_vida(lote),
        "galpon_id": lote.galpon_id,
        "galpon": lote.galpon.nombre,
        "granja_id": lote.galpon.granja_id,
        "granja": lote.galpon.granja.nombre,
        "ubicacion": lote.galpon.granja.ubicacion,
    }


def _alerta(a: Alerta) -> dict:
    return {
        "id": a.id,
        "lote_id": a.lote_id,
        "lote": f"{a.lote.linea} · {a.lote.galpon.nombre}",
        "tipo": a.tipo,
        "mensaje": a.mensaje,
        "estado": a.estado,
        "requiere_veterinario": bool(a.requiere_veterinario),
        "observacion": a.observacion,
        "creada_en": a.creada_en.isoformat(timespec="minutes"),
        "notificacion_estado": a.notificacion_estado or "PENDIENTE",
        "notificacion_error": a.notificacion_error or "",
        "notificada_en": a.notificada_en.isoformat(timespec="minutes") if a.notificada_en else None,
    }


def _tratamiento(t: Tratamiento) -> dict:
    ultima, libre = fechas_tratamiento(t.fecha_inicio, t.dias_tratamiento, t.dias_carencia)
    hoy = date.today()
    return {
        "id": t.id,
        "lote_id": t.lote_id,
        "medicamento": t.medicamento,
        "dosis": t.dosis,
        "via": t.via,
        "fecha_inicio": t.fecha_inicio.isoformat(),
        "dias_tratamiento": t.dias_tratamiento,
        "dias_carencia": t.dias_carencia,
        "aves_tratadas": t.aves_tratadas,
        "ultima_dosis": ultima.isoformat(),
        "libre_faena": libre.isoformat(),
        "en_carencia": t.estado != "OBSERVADA" and hoy < libre,
        "dias_restantes": max((libre - hoy).days, 0),
        "estado": t.estado,
        "diagnostico": t.diagnostico,
    }


def _vacuna(v: Vacunacion) -> dict:
    return {
        "id": v.id,
        "lote_id": v.lote_id,
        "nombre": v.nombre,
        "fecha_programada": v.fecha_programada.isoformat(),
        "estado": v.estado,
        "observacion": v.observacion,
    }


def _cierre(c: CierreLote) -> dict:
    return {
        "id": c.id,
        "lote_id": c.lote_id,
        "fecha_cierre": c.fecha_cierre.isoformat(),
        "aves_vendidas": c.aves_vendidas,
        "peso_total_kg": c.peso_total_kg,
        "precio_venta_kg": c.precio_venta_kg,
        "ingreso_total": c.ingreso_total,
        "costo_pollitos": c.costo_pollitos,
        "costo_alimento": c.costo_alimento,
        "costo_sanidad": c.costo_sanidad,
        "otros_costos": c.otros_costos,
        "total_costos": c.total_costos,
        "margen": c.margen,
        "observaciones": c.observaciones,
        "cerrado_por": c.cerrado_por,
        "created_at": c.created_at.isoformat(timespec="minutes"),
    }


def _cargar_lote(db: Session, lote_id: int, usuario: Usuario) -> Lote:
    """Carga el lote solo si pertenece a la organización del usuario; si no, responde 404."""
    lote = (
        db.query(Lote)
        .join(Galpon, Lote.galpon_id == Galpon.id)
        .join(Granja, Galpon.granja_id == Granja.id)
        .options(joinedload(Lote.galpon).joinedload(Galpon.granja))
        .filter(Lote.id == lote_id, Granja.organizacion_id == organizacion_de(usuario))
        .first()
    )
    if lote is None:
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    return lote


@app.get("/api/salud")
def salud():
    return {"ok": True, "nombre": "AviSmart"}


@app.post("/api/contacto", status_code=201)
def registrar_contacto(body: ContactoIn, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise HTTPException(status_code=400, detail="El correo no es válido")
    if body.motivo not in ("DEMO", "COMERCIAL", "SOPORTE", "ALIANZA"):
        raise HTTPException(status_code=400, detail="El motivo no es válido")
    solicitud = SolicitudContacto(
        nombre=body.nombre.strip(),
        email=email,
        empresa=body.empresa.strip(),
        pais=body.pais.strip(),
        aves=body.aves.strip(),
        motivo=body.motivo,
        plan=body.plan.strip() or "POR_DEFINIR",
        mensaje=body.mensaje.strip(),
        estado="NUEVA",
        creada_en=datetime.now(),
    )
    db.add(solicitud)
    db.commit()
    db.refresh(solicitud)
    return {"ok": True, "id": solicitud.id, "mensaje": "Solicitud recibida"}


@app.post("/api/auth/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == body.email.strip().lower()).first()
    if usuario is None or not usuario.activo or not verify_password(body.password, usuario.password_hash):
        raise HTTPException(status_code=401, detail="Correo o clave incorrectos")
    if organizacion_suspendida(usuario):
        raise HTTPException(status_code=401, detail="El acceso de su organización está suspendido")
    return {"token": create_token(usuario), "usuario": _usuario(usuario)}


@app.get("/api/me")
def me(usuario: Usuario = Depends(get_current_user)):
    return _usuario(usuario)


@app.post("/api/auth/cambiar-clave")
def cambiar_clave(
    body: CambioClaveIn,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    if not verify_password(body.clave_actual, usuario.password_hash):
        raise HTTPException(status_code=400, detail="La clave actual no es correcta")
    if body.clave_actual == body.clave_nueva:
        raise HTTPException(status_code=400, detail="La nueva clave debe ser diferente")
    usuario.password_hash = hash_password(body.clave_nueva)
    usuario.debe_cambiar_clave = 0
    db.commit()
    return _usuario(usuario)


def _granjas_de(db: Session, org: int) -> list[Granja]:
    return (
        db.query(Granja)
        .options(joinedload(Granja.galpones))
        .filter(Granja.organizacion_id == org)
        .order_by(Granja.id.asc())
        .all()
    )


@app.get("/api/resumen")
def resumen(db: Session = Depends(get_db), usuario: Usuario = Depends(cliente)):
    org = organizacion_de(usuario)
    granjas = _granjas_de(db, org)
    lotes = (
        db.query(Lote)
        .join(Galpon, Lote.galpon_id == Galpon.id)
        .join(Granja, Galpon.granja_id == Granja.id)
        .options(joinedload(Lote.galpon).joinedload(Galpon.granja))
        .filter(Granja.organizacion_id == org)
        .order_by(Lote.id.asc())
        .all()
    )
    granja = granjas[0] if granjas else None
    return {
        "organizacion": {"id": org, "nombre": usuario.organizacion.nombre},
        "granja": {"id": granja.id, "nombre": granja.nombre, "ubicacion": granja.ubicacion} if granja else None,
        "granjas": [_granja(g) for g in granjas],
        "galpones": [_galpon(x) for g in granjas for x in sorted(g.galpones, key=lambda x: x.id)],
        "lotes": [_lote(l) for l in lotes],
        "umbral_mortalidad": umbral_mortalidad(db, org),
    }


def _cargar_granja(db: Session, granja_id: int, usuario: Usuario) -> Granja:
    granja = db.get(Granja, granja_id)
    if granja is None or granja.organizacion_id != organizacion_de(usuario):
        raise HTTPException(status_code=404, detail="Granja avícola no encontrada")
    return granja


def _cargar_galpon(db: Session, galpon_id: int, usuario: Usuario) -> Galpon:
    galpon = db.get(Galpon, galpon_id)
    if galpon is None or galpon.granja.organizacion_id != organizacion_de(usuario):
        raise HTTPException(status_code=404, detail="Galpón no encontrado")
    return galpon


@app.get("/api/granjas")
def listar_granjas(db: Session = Depends(get_db), usuario: Usuario = Depends(cliente)):
    return [_granja(g) for g in _granjas_de(db, organizacion_de(usuario))]


@app.post("/api/granjas", status_code=201)
def crear_granja(body: GranjaIn, db: Session = Depends(get_db), usuario: Usuario = Depends(require("ADMIN", "PRODUCTOR"))):
    granja = Granja(nombre=body.nombre.strip(), ubicacion=body.ubicacion.strip(), organizacion_id=organizacion_de(usuario))
    db.add(granja)
    db.commit()
    db.refresh(granja)
    return _granja(granja)


@app.put("/api/granjas/{granja_id}")
def editar_granja(
    granja_id: int,
    body: GranjaIn,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(require("ADMIN", "PRODUCTOR")),
):
    granja = _cargar_granja(db, granja_id, usuario)
    granja.nombre = body.nombre.strip()
    granja.ubicacion = body.ubicacion.strip()
    db.commit()
    return _granja(granja)


@app.post("/api/granjas/{granja_id}/galpones", status_code=201)
def crear_galpon(
    granja_id: int,
    body: GalponIn,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(require("ADMIN", "PRODUCTOR")),
):
    granja = _cargar_granja(db, granja_id, usuario)
    nombre = body.nombre.strip()
    if any(g.nombre.lower() == nombre.lower() for g in granja.galpones):
        raise HTTPException(status_code=400, detail="Ya existe un galpón con ese nombre en la granja avícola")
    galpon = Galpon(
        granja_id=granja.id,
        nombre=nombre,
        capacidad=body.capacidad,
        camara_nombre="Cámara principal",
        camara_modo="SIMULADA",
        camara_activa=1,
    )
    db.add(galpon)
    db.commit()
    db.refresh(galpon)
    return _galpon(galpon)


@app.put("/api/galpones/{galpon_id}")
def editar_galpon(
    galpon_id: int,
    body: GalponIn,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(require("ADMIN", "PRODUCTOR")),
):
    galpon = _cargar_galpon(db, galpon_id, usuario)
    nombre = body.nombre.strip()
    if any(g.id != galpon.id and g.nombre.lower() == nombre.lower() for g in galpon.granja.galpones):
        raise HTTPException(status_code=400, detail="Ya existe un galpón con ese nombre en la granja avícola")
    mayor = max((l.poblacion_inicial for l in galpon.lotes if l.estado == "ACTIVO"), default=0)
    if body.capacidad < mayor:
        raise HTTPException(status_code=400, detail=f"Hay un lote activo de {mayor} aves; la capacidad no puede ser menor")
    galpon.nombre = nombre
    galpon.capacidad = body.capacidad
    db.commit()
    return _galpon(galpon)


@app.post("/api/lotes")
def crear_lote(
    body: LoteIn,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(require("PRODUCTOR", "ADMIN")),
):
    if body.linea not in ("Ross", "Cobb"):
        raise HTTPException(status_code=400, detail="La línea tiene que ser Ross o Cobb")
    if body.sexo not in ("MIXTO", "MACHOS", "HEMBRAS"):
        raise HTTPException(status_code=400, detail="El sexo tiene que ser mixto, machos o hembras")
    if body.fecha_ingreso > date.today():
        raise HTTPException(status_code=400, detail="La fecha de ingreso no puede ser futura")
    if body.descarte_llegada >= body.cantidad_recibida:
        raise HTTPException(status_code=400, detail="Los descartados deben ser menos que los pollitos recibidos")
    galpon = _cargar_galpon(db, body.galpon_id, usuario)
    ocupado = db.query(Lote).filter(Lote.galpon_id == galpon.id, Lote.estado == "ACTIVO").first()
    if ocupado:
        raise HTTPException(
            status_code=400,
            detail=f"{galpon.nombre} ya tiene un lote activo ({ocupado.linea}, ingreso {ocupado.fecha_ingreso.strftime('%d/%m/%Y')}). Ciérralo antes de abrir otro.",
        )
    poblacion = body.cantidad_recibida - body.descarte_llegada
    if poblacion > galpon.capacidad:
        raise HTTPException(status_code=400, detail=f"Los pollitos superan la capacidad de {galpon.nombre} ({galpon.capacidad} aves)")
    lote = Lote(
        galpon_id=body.galpon_id,
        linea=body.linea,
        fecha_ingreso=body.fecha_ingreso,
        poblacion_inicial=poblacion,
        peso_objetivo_g=body.peso_objetivo_g,
        proveedor=body.proveedor.strip(),
        guia=body.guia.strip(),
        sexo=body.sexo,
        cantidad_recibida=body.cantidad_recibida,
        descarte_llegada=body.descarte_llegada,
        peso_llegada_g=body.peso_llegada_g,
        precio_pollito=body.precio_pollito,
        edad_saca_dias=body.edad_saca_dias,
        observaciones=body.observaciones.strip(),
        estado="ACTIVO",
    )
    db.add(lote)
    db.commit()
    db.refresh(lote)
    lote = _cargar_lote(db, lote.id, usuario)
    return _lote(lote)


def _camara(db: Session, galpon: Galpon, lote: Lote | None = None) -> dict:
    lectura = (
        db.query(LecturaAmbiental)
        .filter(LecturaAmbiental.galpon_id == galpon.id)
        .order_by(LecturaAmbiental.fecha_hora.desc())
        .first()
    )
    return {
        "galpon_id": galpon.id,
        "galpon": galpon.nombre,
        "nombre": galpon.camara_nombre or "Cámara principal",
        "modo": galpon.camara_modo or "SIMULADA",
        "activa": bool(galpon.camara_activa if galpon.camara_activa is not None else 1),
        "lote_id": lote.id if lote else None,
        "lote": f"{lote.linea} · día {dia_vida(lote)}" if lote else None,
        "granja": galpon.granja.nombre if galpon.granja else None,
        "ubicacion": galpon.granja.ubicacion if galpon.granja else None,
        "lectura": (
            {
                "temperatura": lectura.temperatura,
                "humedad": lectura.humedad,
                "fecha_hora": lectura.fecha_hora.isoformat(timespec="minutes"),
            }
            if lectura
            else None
        ),
    }


@app.get("/api/lotes/{lote_id}/panel")
def panel(lote_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(cliente)):
    lote = _cargar_lote(db, lote_id, usuario)
    nuevas = evaluar_vacunas_vencidas(db, lote)
    if nuevas:
        db.commit()
        notificar_alertas(db, nuevas)
    data = indicadores(db, lote)
    data["lote"] = _lote(lote)
    data["umbral_mortalidad"] = umbral_mortalidad(db, organizacion_de(usuario))
    data["carencias"] = carencias_activas(db, lote.id)
    data["vacunas_vencidas"] = [
        {
            "id": v.id,
            "nombre": v.nombre,
            "fecha_programada": v.fecha_programada.isoformat(),
            "dias_atraso": (date.today() - v.fecha_programada).days,
        }
        for v in db.query(Vacunacion)
        .filter(
            Vacunacion.lote_id == lote.id,
            Vacunacion.estado == "PENDIENTE",
            Vacunacion.fecha_programada <= date.today(),
        )
        .all()
    ]
    return data


@app.get("/api/lotes/{lote_id}/camara")
def camara_lote(lote_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(cliente)):
    lote = _cargar_lote(db, lote_id, usuario)
    return _camara(db, lote.galpon, lote)


@app.post("/api/lotes/{lote_id}/registros")
def crear_registro(
    lote_id: int,
    body: RegistroIn,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(require("PRODUCTOR", "OPERATIVO")),
):
    lote = _cargar_lote(db, lote_id, usuario)
    if lote.estado != "ACTIVO":
        raise HTTPException(status_code=400, detail="El lote ya está cerrado")
    if body.fecha < lote.fecha_ingreso or body.fecha > date.today():
        raise HTTPException(status_code=400, detail="La fecha queda fuera del lote")
    existe = (
        db.query(RegistroDiario)
        .filter(RegistroDiario.lote_id == lote.id, RegistroDiario.fecha == body.fecha)
        .first()
    )
    if existe:
        raise HTTPException(status_code=400, detail="Ya hay un registro para esa fecha")
    muertes = sum(r.mortalidad for r in lote.registros)
    if body.mortalidad > lote.poblacion_inicial - muertes:
        raise HTTPException(status_code=400, detail="La mortalidad supera las aves que quedan")

    registro = RegistroDiario(
        lote_id=lote.id,
        usuario_id=usuario.id,
        fecha=body.fecha,
        mortalidad=body.mortalidad,
        alimento_kg=body.alimento_kg,
        agua_l=body.agua_l,
        peso_muestra_g=body.peso_muestra_g,
    )
    db.add(registro)
    db.flush()
    nuevas = evaluar_registro(db, lote, registro)
    db.commit()
    notificar_alertas(db, nuevas)
    return {"ok": True, "alertas": [_alerta(a) for a in nuevas]}


@app.post("/api/lotes/{lote_id}/clima")
def crear_clima(
    lote_id: int,
    body: ClimaIn,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(require("PRODUCTOR", "OPERATIVO", "ADMIN")),
):
    lote = _cargar_lote(db, lote_id, usuario)
    if lote.estado != "ACTIVO":
        raise HTTPException(status_code=400, detail="El lote ya está cerrado")
    lectura = LecturaAmbiental(
        galpon_id=lote.galpon_id,
        fecha_hora=datetime.now().replace(second=0, microsecond=0),
        temperatura=body.temperatura,
        humedad=body.humedad,
        origen="SIMULADO",
    )
    db.add(lectura)
    db.flush()
    nuevas = evaluar_clima(db, lote, lectura)
    db.commit()
    notificar_alertas(db, nuevas)
    return {
        "ok": True,
        "lectura": {"temperatura": lectura.temperatura, "humedad": lectura.humedad},
        "alertas": [_alerta(a) for a in nuevas],
    }


@app.get("/api/lotes/{lote_id}/sanidad")
def sanidad(lote_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(cliente)):
    _cargar_lote(db, lote_id, usuario)
    vacunas = (
        db.query(Vacunacion)
        .filter(Vacunacion.lote_id == lote_id)
        .order_by(Vacunacion.fecha_programada.asc())
        .all()
    )
    tratamientos = (
        db.query(Tratamiento)
        .filter(Tratamiento.lote_id == lote_id)
        .order_by(Tratamiento.fecha_inicio.desc())
        .all()
    )
    return {"vacunas": [_vacuna(v) for v in vacunas], "tratamientos": [_tratamiento(t) for t in tratamientos]}


@app.get("/api/catalogo/sanidad")
def catalogo_sanidad(_: Usuario = Depends(cliente)):
    return {"vacunas": catalogo.VACUNAS, "medicamentos": catalogo.MEDICAMENTOS}


@app.post("/api/lotes/{lote_id}/sanidad")
def crear_vacuna(
    lote_id: int,
    body: VacunaIn,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(require("PRODUCTOR", "OPERATIVO")),
):
    lote = _cargar_lote(db, lote_id, usuario)
    if lote.estado != "ACTIVO":
        raise HTTPException(status_code=400, detail="El lote ya está cerrado")
    if catalogo.vacuna(body.nombre.strip()) is None:
        raise HTTPException(status_code=400, detail="Elige una vacuna del catálogo")
    vacuna = Vacunacion(
        lote_id=lote.id,
        nombre=body.nombre.strip(),
        fecha_programada=body.fecha_programada,
        estado="PENDIENTE",
        observacion="",
        validado_por=None,
    )
    db.add(vacuna)
    db.commit()
    db.refresh(vacuna)
    return _vacuna(vacuna)


VIAS = ("Agua de bebida", "Alimento", "Inyección")


@app.post("/api/lotes/{lote_id}/tratamientos")
def crear_tratamiento(
    lote_id: int,
    body: TratamientoIn,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(require("PRODUCTOR", "OPERATIVO")),
):
    lote = _cargar_lote(db, lote_id, usuario)
    if lote.estado != "ACTIVO":
        raise HTTPException(status_code=400, detail="El lote ya está cerrado")
    producto = catalogo.medicamento(body.medicamento.strip())
    if producto is None:
        raise HTTPException(status_code=400, detail="Elige un medicamento del catálogo")
    if body.dosis.strip() not in producto["dosis"]:
        raise HTTPException(status_code=400, detail="La dosis no corresponde a ese medicamento")
    if body.via not in producto["vias"]:
        raise HTTPException(status_code=400, detail="La vía no corresponde a ese medicamento")
    if body.fecha_inicio < lote.fecha_ingreso:
        raise HTTPException(status_code=400, detail="La fecha queda antes del ingreso del lote")
    if body.aves_tratadas and body.aves_tratadas > lote.poblacion_inicial:
        raise HTTPException(status_code=400, detail="Las aves tratadas superan la población del lote")
    tratamiento = Tratamiento(
        lote_id=lote.id,
        medicamento=body.medicamento.strip(),
        dosis=body.dosis.strip(),
        via=body.via,
        fecha_inicio=body.fecha_inicio,
        dias_tratamiento=body.dias_tratamiento,
        dias_carencia=body.dias_carencia,
        aves_tratadas=body.aves_tratadas,
        estado="PENDIENTE",
        diagnostico="",
        validado_por=None,
    )
    db.add(tratamiento)
    db.commit()
    db.refresh(tratamiento)
    return _tratamiento(tratamiento)


@app.post("/api/tratamientos/{tratamiento_id}/validar")
def validar_tratamiento(
    tratamiento_id: int,
    body: ValidarIn,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(require("VETERINARIO")),
):
    if body.decision not in ("VALIDADA", "OBSERVADA"):
        raise HTTPException(status_code=400, detail="La decisión no es válida")
    tratamiento = db.get(Tratamiento, tratamiento_id)
    if tratamiento is None:
        raise HTTPException(status_code=404, detail="Tratamiento no encontrado")
    _cargar_lote(db, tratamiento.lote_id, usuario)
    tratamiento.estado = body.decision
    tratamiento.diagnostico = body.observacion.strip()
    tratamiento.validado_por = usuario.id
    db.commit()
    return _tratamiento(tratamiento)


@app.post("/api/vacunas/{vacuna_id}/validar")
def validar_vacuna(
    vacuna_id: int,
    body: ValidarIn,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(require("VETERINARIO")),
):
    if body.decision not in ("VALIDADA", "OBSERVADA"):
        raise HTTPException(status_code=400, detail="La decisión no es válida")
    vacuna = db.get(Vacunacion, vacuna_id)
    if vacuna is None:
        raise HTTPException(status_code=404, detail="Vacuna no encontrada")
    _cargar_lote(db, vacuna.lote_id, usuario)
    vacuna.estado = body.decision
    vacuna.observacion = body.observacion.strip()
    vacuna.validado_por = usuario.id
    if body.decision in ("VALIDADA", "OBSERVADA"):
        cerrar_recordatorios_vacuna(db, vacuna.lote_id, vacuna.nombre)
    db.commit()
    return _vacuna(vacuna)


@app.get("/api/alertas")
def listar_alertas(db: Session = Depends(get_db), usuario: Usuario = Depends(cliente)):
    org = organizacion_de(usuario)
    nuevas = evaluar_vacunas_vencidas(db, organizacion_id=org)
    if nuevas:
        db.commit()
        notificar_alertas(db, nuevas)
    alertas = (
        db.query(Alerta)
        .join(Lote, Alerta.lote_id == Lote.id)
        .join(Galpon, Lote.galpon_id == Galpon.id)
        .join(Granja, Galpon.granja_id == Granja.id)
        .options(joinedload(Alerta.lote).joinedload(Lote.galpon))
        .filter(Granja.organizacion_id == org)
        .order_by(Alerta.creada_en.desc())
        .all()
    )
    return [_alerta(a) for a in alertas]


@app.post("/api/alertas/{alerta_id}/atender")
def atender_alerta(
    alerta_id: int,
    body: ValidarIn,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(cliente),
):
    alerta = (
        db.query(Alerta)
        .options(joinedload(Alerta.lote).joinedload(Lote.galpon))
        .filter(Alerta.id == alerta_id)
        .first()
    )
    if alerta is None:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")
    _cargar_lote(db, alerta.lote_id, usuario)
    if alerta.requiere_veterinario and usuario.rol != "VETERINARIO":
        raise HTTPException(status_code=403, detail="Esta alerta la revisa el médico veterinario")
    if not alerta.requiere_veterinario and usuario.rol not in ("PRODUCTOR", "ADMIN"):
        raise HTTPException(status_code=403, detail="Esta alerta la atiende el productor")
    if body.decision not in ("ATENDIDA", "VISTA"):
        raise HTTPException(status_code=400, detail="La decisión no es válida")
    alerta.estado = body.decision
    alerta.observacion = body.observacion.strip()
    alerta.atendida_por = usuario.id
    db.commit()
    return _alerta(alerta)


def _usuarios_del_ambito(db: Session, actual: Usuario):
    """Un ADMIN ve las cuentas de su organización; PLATAFORMA ve solo las cuentas de plataforma.
    El PRODUCTOR no ve las cuentas de administración: solo productores, operativos y veterinarios."""
    consulta = db.query(Usuario)
    if actual.rol == "PLATAFORMA":
        return consulta.filter(Usuario.organizacion_id.is_(None), Usuario.rol == "PLATAFORMA")
    consulta = consulta.filter(Usuario.organizacion_id == organizacion_de(actual))
    if actual.rol == "PRODUCTOR":
        consulta = consulta.filter(Usuario.rol.in_(ROLES_PERSONAL))
    return consulta


def _usuario_del_ambito(db: Session, actual: Usuario, usuario_id: int) -> Usuario:
    usuario = _usuarios_del_ambito(db, actual).filter(Usuario.id == usuario_id).first()
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return usuario


def _validar_email(email: str) -> str:
    email = email.strip().lower()
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise HTTPException(status_code=400, detail="El correo no es válido")
    return email


def _nueva_cuenta(db: Session, nombre: str, email: str, rol: str, organizacion_id: int | None) -> tuple[Usuario, str]:
    email = _validar_email(email)
    if db.query(Usuario).filter(Usuario.email == email).first():
        raise HTTPException(status_code=400, detail="Ya existe una cuenta con ese correo")
    clave_temporal = secrets.token_urlsafe(10)
    usuario = Usuario(
        nombre=nombre.strip(),
        email=email,
        password_hash=hash_password(clave_temporal),
        rol=rol,
        activo=1,
        debe_cambiar_clave=1,
        organizacion_id=organizacion_id,
    )
    db.add(usuario)
    return usuario, clave_temporal


def _alta(db: Session, body: UsuarioCrearIn, organizacion_id: int | None, permitidos: tuple[str, ...]) -> dict:
    if body.rol not in permitidos:
        raise HTTPException(status_code=400, detail="No puede crear cuentas con ese rol")
    usuario, clave_temporal = _nueva_cuenta(db, body.nombre, body.email, body.rol, organizacion_id)
    db.commit()
    db.refresh(usuario)
    return {"usuario": _usuario(usuario), "clave_temporal": clave_temporal}


def _verificar_gestion(usuario: Usuario, permitidos: tuple[str, ...]) -> None:
    if usuario.rol not in permitidos:
        raise HTTPException(status_code=403, detail="No puede gestionar esa cuenta")


def _restablecer(db: Session, usuario: Usuario, permitidos: tuple[str, ...]) -> dict:
    _verificar_gestion(usuario, permitidos)
    clave_temporal = secrets.token_urlsafe(10)
    usuario.password_hash = hash_password(clave_temporal)
    usuario.debe_cambiar_clave = 1
    db.commit()
    return {"usuario": _usuario(usuario), "clave_temporal": clave_temporal}


def _cambiar_estado(db: Session, usuario: Usuario, activo: bool, actual: Usuario, ambito, permitidos: tuple[str, ...]) -> dict:
    _verificar_gestion(usuario, permitidos)
    if usuario.id == actual.id and not activo:
        raise HTTPException(status_code=400, detail="No puede desactivar su propia cuenta")
    if usuario.rol in ROLES_RESPONSABLES and usuario.activo and not activo:
        activos = ambito.filter(Usuario.rol == usuario.rol, Usuario.activo == 1).count()
        if activos <= 1:
            nombre = {"PLATAFORMA": "Propietario de la plataforma", "ADMIN": "Administrador", "PRODUCTOR": "Productor"}[usuario.rol]
            raise HTTPException(status_code=400, detail=f"Debe quedar al menos un {nombre} activo")
    usuario.activo = 1 if activo else 0
    db.commit()
    return _usuario(usuario)


gestor = require("ADMIN", "PRODUCTOR", "PLATAFORMA")


@app.get("/api/usuarios")
def usuarios(db: Session = Depends(get_db), actual: Usuario = Depends(gestor)):
    return [_usuario(u) for u in _usuarios_del_ambito(db, actual).order_by(Usuario.id).all()]


@app.post("/api/usuarios")
def crear_usuario(body: UsuarioCrearIn, db: Session = Depends(get_db), actual: Usuario = Depends(gestor)):
    organizacion_id = None if actual.rol == "PLATAFORMA" else organizacion_de(actual)
    return _alta(db, body, organizacion_id, CREA[actual.rol])


@app.post("/api/usuarios/{usuario_id}/restablecer-clave")
def restablecer_clave(usuario_id: int, db: Session = Depends(get_db), actual: Usuario = Depends(gestor)):
    return _restablecer(db, _usuario_del_ambito(db, actual, usuario_id), GESTIONA[actual.rol])


@app.patch("/api/usuarios/{usuario_id}/estado")
def cambiar_estado_usuario(
    usuario_id: int,
    body: UsuarioEstadoIn,
    db: Session = Depends(get_db),
    actual: Usuario = Depends(gestor),
):
    usuario = _usuario_del_ambito(db, actual, usuario_id)
    return _cambiar_estado(db, usuario, body.activo, actual, _usuarios_del_ambito(db, actual), GESTIONA[actual.rol])


@app.put("/api/umbral")
def guardar_umbral(
    body: UmbralIn,
    db: Session = Depends(get_db),
    actual: Usuario = Depends(require("VETERINARIO", "ADMIN")),
):
    clave = clave_umbral(organizacion_de(actual))
    row = db.get(Configuracion, clave)
    if row is None:
        row = Configuracion(clave=clave, valor=str(body.mortalidad_diaria))
        db.add(row)
    else:
        row.valor = str(body.mortalidad_diaria)
    db.commit()
    return {"mortalidad_diaria": body.mortalidad_diaria}


@app.get("/api/notificaciones/estado")
def estado_notificaciones(_: Usuario = Depends(require("ADMIN", "PLATAFORMA"))):
    return estado_telegram()


@app.post("/api/notificaciones/probar")
def probar_notificaciones(_: Usuario = Depends(require("ADMIN", "PLATAFORMA"))):
    if not estado_telegram()["configurado"]:
        raise HTTPException(status_code=400, detail="Configura TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID")
    ok, error = probar_telegram()
    if not ok:
        raise HTTPException(status_code=502, detail=f"Telegram no pudo enviar el mensaje: {error}")
    return {"ok": True, "mensaje": "Mensaje de prueba enviado"}


# ---------------------------------------------------------------------------
# Plataforma: solo el propietario de AviSmart (rol PLATAFORMA).
# ---------------------------------------------------------------------------

plataforma = require("PLATAFORMA")


@app.get("/api/plataforma/solicitudes")
def solicitudes_plataforma(db: Session = Depends(get_db), _: Usuario = Depends(plataforma)):
    solicitudes = db.query(SolicitudContacto).order_by(SolicitudContacto.creada_en.desc()).all()
    return [_solicitud(s) for s in solicitudes]


@app.patch("/api/plataforma/solicitudes/{solicitud_id}")
def actualizar_solicitud(
    solicitud_id: int,
    body: SolicitudEstadoIn,
    db: Session = Depends(get_db),
    _: Usuario = Depends(plataforma),
):
    if body.estado not in ("NUEVA", "CONTACTADA", "DESCARTADA"):
        raise HTTPException(status_code=400, detail="El estado no es válido")
    solicitud = db.get(SolicitudContacto, solicitud_id)
    if solicitud is None:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    solicitud.estado = body.estado
    solicitud.atendida_en = datetime.now() if body.estado != "NUEVA" else None
    db.commit()
    return _solicitud(solicitud)


def _cargar_organizacion(db: Session, organizacion_id: int) -> Organizacion:
    organizacion = db.get(Organizacion, organizacion_id)
    if organizacion is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return organizacion


@app.get("/api/plataforma/organizaciones")
def listar_organizaciones(db: Session = Depends(get_db), _: Usuario = Depends(plataforma)):
    return [_organizacion(db, o) for o in db.query(Organizacion).order_by(Organizacion.id.asc()).all()]


@app.post("/api/plataforma/organizaciones", status_code=201)
def crear_organizacion(body: OrganizacionIn, db: Session = Depends(get_db), _: Usuario = Depends(plataforma)):
    solicitud = None
    if body.solicitud_id is not None:
        solicitud = db.get(SolicitudContacto, body.solicitud_id)
        if solicitud is None:
            raise HTTPException(status_code=404, detail="Solicitud no encontrada")
        if solicitud.estado == "CLIENTE":
            raise HTTPException(status_code=400, detail="Esa solicitud ya se convirtió en cliente")
    organizacion = Organizacion(
        nombre=body.nombre.strip(),
        estado="ACTIVA",
        creada_en=datetime.now(),
        solicitud_id=solicitud.id if solicitud else None,
    )
    db.add(organizacion)
    db.flush()
    usuario, clave_temporal = _nueva_cuenta(db, body.productor_nombre, body.productor_email, "PRODUCTOR", organizacion.id)
    if solicitud is not None:
        solicitud.estado = "CLIENTE"
        solicitud.atendida_en = datetime.now()
    db.commit()
    db.refresh(organizacion)
    return {"organizacion": _organizacion(db, organizacion), "usuario": _usuario(usuario), "clave_temporal": clave_temporal}


@app.patch("/api/plataforma/organizaciones/{organizacion_id}")
def cambiar_estado_organizacion(
    organizacion_id: int,
    body: OrganizacionEstadoIn,
    db: Session = Depends(get_db),
    _: Usuario = Depends(plataforma),
):
    if body.estado not in ("ACTIVA", "SUSPENDIDA"):
        raise HTTPException(status_code=400, detail="El estado no es válido")
    organizacion = _cargar_organizacion(db, organizacion_id)
    organizacion.estado = body.estado
    db.commit()
    return _organizacion(db, organizacion)


def _personal_de(db: Session, organizacion_id: int):
    return db.query(Usuario).filter(Usuario.organizacion_id == organizacion_id)


def _persona_del_cliente(db: Session, organizacion_id: int, usuario_id: int) -> Usuario:
    usuario = _personal_de(db, organizacion_id).filter(Usuario.id == usuario_id).first()
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return usuario


@app.get("/api/plataforma/organizaciones/{organizacion_id}")
def ver_organizacion(organizacion_id: int, db: Session = Depends(get_db), _: Usuario = Depends(plataforma)):
    return _organizacion(db, _cargar_organizacion(db, organizacion_id))


@app.get("/api/plataforma/organizaciones/{organizacion_id}/usuarios")
def personal_cliente(organizacion_id: int, db: Session = Depends(get_db), _: Usuario = Depends(plataforma)):
    _cargar_organizacion(db, organizacion_id)
    return [_usuario(u) for u in _personal_de(db, organizacion_id).order_by(Usuario.id).all()]


@app.post("/api/plataforma/organizaciones/{organizacion_id}/usuarios")
def alta_personal_cliente(
    organizacion_id: int,
    body: UsuarioCrearIn,
    db: Session = Depends(get_db),
    _: Usuario = Depends(plataforma),
):
    _cargar_organizacion(db, organizacion_id)
    return _alta(db, body, organizacion_id, PLATAFORMA_CREA_EN_CLIENTE)


@app.post("/api/plataforma/organizaciones/{organizacion_id}/usuarios/{usuario_id}/restablecer-clave")
def restablecer_personal_cliente(
    organizacion_id: int,
    usuario_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(plataforma),
):
    return _restablecer(db, _persona_del_cliente(db, organizacion_id, usuario_id), PLATAFORMA_GESTIONA_EN_CLIENTE)


@app.patch("/api/plataforma/organizaciones/{organizacion_id}/usuarios/{usuario_id}/estado")
def estado_personal_cliente(
    organizacion_id: int,
    usuario_id: int,
    body: UsuarioEstadoIn,
    db: Session = Depends(get_db),
    actual: Usuario = Depends(plataforma),
):
    usuario = _persona_del_cliente(db, organizacion_id, usuario_id)
    return _cambiar_estado(db, usuario, body.activo, actual, _personal_de(db, organizacion_id), PLATAFORMA_GESTIONA_EN_CLIENTE)


@app.post("/api/lotes/{lote_id}/cerrar")
def cerrar_lote(
    lote_id: int,
    body: CierreIn,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(require("PRODUCTOR", "ADMIN")),
):
    lote = _cargar_lote(db, lote_id, usuario)
    if lote.estado != "ACTIVO" or lote.cierre is not None:
        raise HTTPException(status_code=400, detail="El lote ya está cerrado")
    if body.fecha_cierre < lote.fecha_ingreso or body.fecha_cierre > date.today():
        raise HTTPException(status_code=400, detail="La fecha de cierre queda fuera del lote")

    carencias = carencias_activas(db, lote.id)
    if carencias:
        fecha_libre = max(item["libre_faena"] for item in carencias)
        raise HTTPException(
            status_code=400,
            detail=f"No se puede cerrar el lote durante la carencia. Fecha libre: {fecha_libre}",
        )

    datos = indicadores(db, lote)
    if body.aves_vendidas > datos["aves_vivas"]:
        raise HTTPException(status_code=400, detail="Las aves vendidas superan las aves vivas")

    ingreso = round(body.peso_total_kg * body.precio_venta_kg, 2)
    costos = round(
        body.costo_pollitos + body.costo_alimento + body.costo_sanidad + body.otros_costos,
        2,
    )
    cierre = CierreLote(
        lote_id=lote.id,
        fecha_cierre=body.fecha_cierre,
        aves_vendidas=body.aves_vendidas,
        peso_total_kg=body.peso_total_kg,
        precio_venta_kg=body.precio_venta_kg,
        ingreso_total=ingreso,
        costo_pollitos=body.costo_pollitos,
        costo_alimento=body.costo_alimento,
        costo_sanidad=body.costo_sanidad,
        otros_costos=body.otros_costos,
        total_costos=costos,
        margen=round(ingreso - costos, 2),
        observaciones=body.observaciones.strip(),
        cerrado_por=usuario.id,
        created_at=datetime.now(),
    )
    lote.estado = "CERRADO"
    lote.fecha_cierre = body.fecha_cierre
    db.add(cierre)
    db.commit()
    db.refresh(cierre)
    return _cierre(cierre)


@app.get("/api/lotes/{lote_id}/cierre")
def consultar_cierre(
    lote_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(require("PRODUCTOR", "ADMIN")),
):
    _cargar_lote(db, lote_id, usuario)
    cierre = db.query(CierreLote).filter(CierreLote.lote_id == lote_id).first()
    if cierre is None:
        raise HTTPException(status_code=404, detail="El lote todavía no tiene cierre")
    return _cierre(cierre)


def _datos_reporte(db: Session, lote_id: int, usuario: Usuario):
    lote = _cargar_lote(db, lote_id, usuario)
    cierre = db.query(CierreLote).filter(CierreLote.lote_id == lote_id).first()
    if cierre is None:
        raise HTTPException(status_code=400, detail="Debe cerrar el lote antes de generar el reporte")
    registros = (
        db.query(RegistroDiario)
        .filter(RegistroDiario.lote_id == lote_id)
        .order_by(RegistroDiario.fecha.asc())
        .all()
    )
    vacunas = db.query(Vacunacion).filter(Vacunacion.lote_id == lote_id).all()
    tratamientos = db.query(Tratamiento).filter(Tratamiento.lote_id == lote_id).all()
    alertas = db.query(Alerta).filter(Alerta.lote_id == lote_id).all()
    return lote, cierre, indicadores(db, lote), registros, vacunas, tratamientos, alertas


@app.get("/api/lotes/{lote_id}/reporte.pdf")
def reporte_pdf(
    lote_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(require("PRODUCTOR", "ADMIN")),
):
    from .reports import generar_pdf

    contenido = generar_pdf(*_datos_reporte(db, lote_id, usuario))
    return StreamingResponse(
        contenido,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="avismart-lote-{lote_id}.pdf"'},
    )


@app.get("/api/lotes/{lote_id}/reporte.xlsx")
def reporte_excel(
    lote_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(require("PRODUCTOR", "ADMIN")),
):
    from .reports import generar_excel

    contenido = generar_excel(*_datos_reporte(db, lote_id, usuario))
    return StreamingResponse(
        contenido,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="avismart-lote-{lote_id}.xlsx"'},
    )
