import os
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from .logic import peso_esperado
from .models import (
    Alerta,
    Configuracion,
    Galpon,
    Granja,
    LecturaAmbiental,
    Lote,
    Organizacion,
    RegistroDiario,
    Tratamiento,
    Usuario,
    Vacunacion,
)
from .security import hash_password

def seed(db: Session) -> None:
    if db.query(Usuario).count() > 0:
        return
    clave_demo = os.getenv("AVISMART_DEMO_PASSWORD", "").strip()
    if len(clave_demo) < 10:
        raise RuntimeError("AVISMART_DEMO_PASSWORD debe tener al menos 10 caracteres para cargar la demostración")

    organizacion = Organizacion(nombre="Demostración", estado="ACTIVA", creada_en=datetime.now())
    db.add(organizacion)
    db.flush()

    cuentas = [
        ("Administrador del sistema", "admin@avismart.local", "ADMIN"),
        ("Responsable de la granja", "productor@avismart.local", "PRODUCTOR"),
        ("Personal de galpón", "operativo@avismart.local", "OPERATIVO"),
        ("Servicio veterinario", "veterinario@avismart.local", "VETERINARIO"),
    ]
    usuarios = {}
    for nombre, email, rol in cuentas:
        usuario = Usuario(
            nombre=nombre,
            email=email,
            password_hash=hash_password(clave_demo),
            rol=rol,
            activo=1,
            debe_cambiar_clave=0,
            organizacion_id=organizacion.id,
        )
        db.add(usuario)
        db.flush()
        usuarios[rol] = usuario

    granja = Granja(nombre="Granja de engorde Puno", ubicacion="Puno", organizacion_id=organizacion.id)
    db.add(granja)
    db.flush()
    galpon = Galpon(
        granja_id=granja.id,
        nombre="Galpón 1",
        capacidad=6000,
        camara_nombre="Cámara principal",
        camara_modo="SIMULADA",
        camara_activa=1,
    )
    db.add(galpon)
    db.flush()

    ingreso = date.today() - timedelta(days=18)
    lote = Lote(
        galpon_id=galpon.id,
        linea="Ross",
        fecha_ingreso=ingreso,
        poblacion_inicial=5000,
        peso_objetivo_g=2800,
        estado="ACTIVO",
    )
    db.add(lote)
    db.flush()

    db.add(Configuracion(clave="mortalidad_diaria", valor="20"))

    mortalidades = [6, 8, 7, 10, 5, 9, 8, 12, 7, 6, 40, 8, 7, 9, 6, 8, 7]
    for i, muertos in enumerate(mortalidades, start=1):
        dia = ingreso + timedelta(days=i)
        db.add(
            RegistroDiario(
                lote_id=lote.id,
                usuario_id=usuarios["OPERATIVO"].id,
                fecha=dia,
                mortalidad=muertos,
                alimento_kg=round(70 + i * 16, 1),
                agua_l=round(140 + i * 28, 1),
                peso_muestra_g=round(peso_esperado(i, lote.linea) * 0.98, 1),
            )
        )

    db.add(
        Alerta(
            lote_id=lote.id,
            tipo="SALUD",
            mensaje="Mortalidad del día: 40 aves. El umbral configurado es 20.",
            estado="NUEVA",
            requiere_veterinario=1,
            observacion="",
            creada_en=datetime.combine(ingreso + timedelta(days=11), datetime.min.time()).replace(hour=8),
        )
    )
    db.add(
        Vacunacion(
            lote_id=lote.id,
            nombre="Newcastle",
            fecha_programada=ingreso + timedelta(days=7),
            estado="VALIDADA",
            observacion="Aplicación conforme.",
            validado_por=usuarios["VETERINARIO"].id,
        )
    )
    db.add(
        Vacunacion(
            lote_id=lote.id,
            nombre="Gumboro",
            fecha_programada=ingreso + timedelta(days=14),
            estado="PENDIENTE",
            observacion="",
            validado_por=None,
        )
    )
    db.add(
        LecturaAmbiental(
            galpon_id=galpon.id,
            fecha_hora=datetime.now().replace(second=0, microsecond=0),
            temperatura=26.4,
            humedad=62,
            origen="SIMULADO",
        )
    )
    db.commit()


def asegurar_tratamiento_demo(db: Session) -> None:
    if db.query(Tratamiento).count() > 0:
        return
    lote = db.query(Lote).order_by(Lote.id.asc()).first()
    if lote is None:
        return
    db.add(
        Tratamiento(
            lote_id=lote.id,
            medicamento="Enrofloxacina",
            dosis="10 mg/kg",
            via="Agua de bebida",
            fecha_inicio=date.today() - timedelta(days=1),
            dias_tratamiento=3,
            dias_carencia=5,
            aves_tratadas=None,
            estado="PENDIENTE",
            diagnostico="",
            validado_por=None,
        )
    )
    db.commit()
