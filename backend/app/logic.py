from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from .models import Alerta, Configuracion, Galpon, Granja, LecturaAmbiental, Lote, RegistroDiario, Tratamiento, Vacunacion

CURVAS = {
    # Objetivos de rendimiento 2022, aves mixtas (as-hatched).
    "Ross": [
        (0, 44),
        (7, 213),
        (14, 533),
        (21, 1012),
        (28, 1616),
        (35, 2296),
        (42, 2998),
        (49, 3681),
    ],
    "Cobb": [
        (0, 42),
        (7, 202),
        (14, 570),
        (21, 1116),
        (28, 1783),
        (35, 2521),
        (42, 3278),
        (49, 4001),
    ],
}


def peso_esperado(dia: int, linea: str = "Ross") -> float:
    curva = CURVAS.get(linea, CURVAS["Ross"])
    dia = max(0, dia)
    if dia >= curva[-1][0]:
        return float(curva[-1][1])
    for (d0, p0), (d1, p1) in zip(curva, curva[1:]):
        if d0 <= dia <= d1:
            t = (dia - d0) / (d1 - d0)
            return p0 + (p1 - p0) * t
    return 42.0


def dia_vida(lote: Lote, hoy: date | None = None) -> int:
    hoy = hoy or lote.fecha_cierre or date.today()
    return max(0, (hoy - lote.fecha_ingreso).days)


def rango_temperatura(dia: int) -> tuple[float, float]:
    if dia <= 7:
        return (31.0, 34.0)
    if dia <= 14:
        return (28.0, 31.0)
    if dia <= 21:
        return (25.0, 29.0)
    if dia <= 28:
        return (23.0, 27.0)
    return (20.0, 25.0)


def clave_umbral(organizacion_id: int | None) -> str:
    return f"mortalidad_diaria:{organizacion_id}" if organizacion_id else "mortalidad_diaria"


def umbral_mortalidad(db: Session, organizacion_id: int | None = None) -> int:
    """Umbral de la organización; si no lo configuró, usa el valor general."""
    row = db.get(Configuracion, clave_umbral(organizacion_id)) if organizacion_id else None
    if row is None:
        row = db.get(Configuracion, "mortalidad_diaria")
    if row is None:
        return 20
    try:
        return int(row.valor)
    except ValueError:
        return 20


def organizacion_del_lote(lote: Lote) -> int | None:
    if lote.galpon is None or lote.galpon.granja is None:
        return None
    return lote.galpon.granja.organizacion_id


def _existe_alerta(db: Session, lote_id: int, tipo: str, hoy: date, motivo: str = "") -> bool:
    inicio = datetime.combine(hoy, datetime.min.time())
    fin = datetime.combine(hoy, datetime.max.time())
    consulta = db.query(Alerta).filter(
        Alerta.lote_id == lote_id,
        Alerta.tipo == tipo,
        Alerta.creada_en >= inicio,
        Alerta.creada_en <= fin,
    )
    if motivo:
        consulta = consulta.filter(Alerta.mensaje.startswith(motivo))
    encontrada = consulta.first()
    return encontrada is not None


def _crear(db: Session, lote_id: int, tipo: str, mensaje: str, veterinario: bool, vacuna_id: int | None = None) -> Alerta:
    alerta = Alerta(
        lote_id=lote_id,
        tipo=tipo,
        mensaje=mensaje,
        estado="NUEVA",
        requiere_veterinario=1 if veterinario else 0,
        observacion="",
        creada_en=datetime.now(),
        vacuna_id=vacuna_id,
    )
    db.add(alerta)
    return alerta


def evaluar_registro(db: Session, lote: Lote, registro: RegistroDiario) -> list[Alerta]:
    nuevas: list[Alerta] = []
    hoy = registro.fecha
    umbral = umbral_mortalidad(db, organizacion_del_lote(lote))

    if registro.mortalidad > umbral and not _existe_alerta(db, lote.id, "SALUD", hoy, "Mortalidad"):
        nuevas.append(
            _crear(
                db,
                lote.id,
                "SALUD",
                f"Mortalidad del día: {registro.mortalidad} aves. El umbral configurado es {umbral}.",
                True,
            )
        )

    anteriores = (
        db.query(RegistroDiario)
        .filter(RegistroDiario.lote_id == lote.id, RegistroDiario.fecha < hoy)
        .order_by(RegistroDiario.fecha.desc())
        .limit(3)
        .all()
    )
    if len(anteriores) == 3:
        consumos = (
            ("alimento", registro.alimento_kg, [r.alimento_kg for r in anteriores]),
            ("agua", registro.agua_l, [r.agua_l for r in anteriores]),
        )
        for nombre, actual, historial in consumos:
            promedio = sum(historial) / 3
            motivo = f"El {nombre}"
            if promedio > 0 and actual < promedio * 0.85 and not _existe_alerta(
                db, lote.id, "SALUD", hoy, motivo
            ):
                caida = round((1 - actual / promedio) * 100)
                nuevas.append(
                    _crear(
                        db,
                        lote.id,
                        "SALUD",
                        f"{motivo} cayó {caida}% frente al promedio de los últimos 3 días.",
                        True,
                    )
                )

    dia = (hoy - lote.fecha_ingreso).days
    esperado = peso_esperado(dia, lote.linea)
    if esperado > 0 and registro.peso_muestra_g > 0:
        desvio = abs(registro.peso_muestra_g - esperado) / esperado
        if desvio > 0.10 and not _existe_alerta(db, lote.id, "CRECIMIENTO", hoy, "Peso"):
            sentido = "por debajo" if registro.peso_muestra_g < esperado else "por encima"
            nuevas.append(
                _crear(
                    db,
                    lote.id,
                    "CRECIMIENTO",
                    f"Peso de muestra {registro.peso_muestra_g:.0f} g, {sentido} de la curva ({esperado:.0f} g).",
                    False,
                )
            )
    return nuevas


def evaluar_clima(db: Session, lote: Lote, lectura: LecturaAmbiental) -> list[Alerta]:
    nuevas: list[Alerta] = []
    dia = dia_vida(lote, lectura.fecha_hora.date())
    tmin, tmax = rango_temperatura(dia)
    hoy = lectura.fecha_hora.date()
    if (lectura.temperatura < tmin or lectura.temperatura > tmax) and not _existe_alerta(
        db, lote.id, "AMBIENTE", hoy, "Temperatura"
    ):
        nuevas.append(
            _crear(
                db,
                lote.id,
                "AMBIENTE",
                f"Temperatura {lectura.temperatura:.1f} °C fuera del rango {tmin:.0f}–{tmax:.0f} °C del día {dia}.",
                False,
            )
        )
    if (lectura.humedad < 50 or lectura.humedad > 70) and not _existe_alerta(
        db, lote.id, "AMBIENTE", hoy, "Humedad"
    ):
        nuevas.append(
            _crear(
                db,
                lote.id,
                "AMBIENTE",
                f"Humedad {lectura.humedad:.0f}% fuera del rango 50–70% recomendado.",
                False,
            )
        )
    return nuevas


def indicadores(db: Session, lote: Lote) -> dict:
    registros = (
        db.query(RegistroDiario)
        .filter(RegistroDiario.lote_id == lote.id)
        .order_by(RegistroDiario.fecha.asc())
        .all()
    )
    muertes = sum(r.mortalidad for r in registros)
    aves = max(lote.poblacion_inicial - muertes, 0)
    mortalidad_pct = (muertes / lote.poblacion_inicial * 100) if lote.poblacion_inicial else 0
    alimento = sum(r.alimento_kg for r in registros)
    ultimo = registros[-1] if registros else None
    peso_inicial = lote.peso_llegada_g or peso_esperado(0, lote.linea)
    peso_actual = ultimo.peso_muestra_g if ultimo else peso_inicial
    dia = dia_vida(lote)
    esperado = peso_esperado(dia, lote.linea)
    ganancia_g = peso_actual - peso_inicial
    biomasa_kg = aves * max(ganancia_g, 0) / 1000
    fcr = (alimento / biomasa_kg) if biomasa_kg > 0 else None
    ganancia_diaria = (ganancia_g / dia) if dia else 0
    epef = None
    if fcr and dia and fcr > 0:
        viabilidad = (aves / lote.poblacion_inicial * 100) if lote.poblacion_inicial else 0
        epef = (viabilidad * (peso_actual / 1000)) / (dia * fcr) * 100

    serie = []
    por_dia = {(r.fecha - lote.fecha_ingreso).days: r for r in registros}
    for d in range(0, dia + 1):
        reg = por_dia.get(d)
        serie.append(
            {
                "dia": d,
                "esperado": round(peso_esperado(d, lote.linea), 1),
                "peso": round(reg.peso_muestra_g, 1) if reg else None,
                "mortalidad": reg.mortalidad if reg else None,
            }
        )

    tmin, tmax = rango_temperatura(dia)
    lectura = None
    if lote.galpon is not None:
        lectura = (
            db.query(LecturaAmbiental)
            .filter(LecturaAmbiental.galpon_id == lote.galpon_id)
            .order_by(LecturaAmbiental.fecha_hora.desc())
            .first()
        )

    abiertas = (
        db.query(Alerta)
        .filter(Alerta.lote_id == lote.id, Alerta.estado != "ATENDIDA")
        .count()
    )

    return {
        "dia_vida": dia,
        "aves_vivas": aves,
        "muertes": muertes,
        "mortalidad_acumulada": round(mortalidad_pct, 2),
        "alimento_kg": round(alimento, 1),
        "peso_actual_g": round(peso_actual, 1),
        "peso_esperado_g": round(esperado, 1),
        "ganancia_diaria_g": round(ganancia_diaria, 1),
        "fcr": round(fcr, 2) if fcr else None,
        "epef": round(epef, 1) if epef else None,
        "temp_min": tmin,
        "temp_max": tmax,
        "alertas_abiertas": abiertas,
        "lectura": (
            {
                "temperatura": lectura.temperatura,
                "humedad": lectura.humedad,
                "origen": lectura.origen,
                "fecha_hora": lectura.fecha_hora.isoformat(timespec="minutes"),
            }
            if lectura
            else None
        ),
        "serie": serie,
        "registros": [
            {
                "id": r.id,
                "fecha": r.fecha.isoformat(),
                "mortalidad": r.mortalidad,
                "alimento_kg": r.alimento_kg,
                "agua_l": r.agua_l,
                "peso_muestra_g": r.peso_muestra_g,
            }
            for r in reversed(registros[-8:])
        ],
    }


def fechas_tratamiento(inicio: date, dias_tratamiento: int, dias_carencia: int) -> tuple[date, date]:
    ultima = inicio + timedelta(days=max(dias_tratamiento, 1) - 1)
    libre = ultima + timedelta(days=max(dias_carencia, 0))
    return ultima, libre


# Etapas de una vacuna que todavía esperan una acción y quién la debe hacer.
ESPERA_VETERINARIO = "PENDIENTE"  # falta aprobar la fecha
ESPERA_APLICACION = "PROGRAMADA"  # falta aplicarla en el galpón


def _cuando(dias: int) -> str:
    return "hoy" if dias == 0 else f"hace {dias} día{'s' if dias != 1 else ''}"


def evaluar_vacunas_vencidas(
    db: Session, lote: Lote | None = None, organizacion_id: int | None = None
) -> list[Alerta]:
    """Crea un recordatorio por vacuna y por etapa cuando la fecha llegó y nadie actuó.

    Solo lotes activos. Si alguien atendió el recordatorio a mano, no se vuelve a crear
    para esa misma etapa; si la vacuna avanza de etapa y sigue atrasada, se crea el siguiente.
    """
    hoy = date.today()
    consulta = (
        db.query(Vacunacion)
        .join(Lote, Vacunacion.lote_id == Lote.id)
        .filter(
            Lote.estado == "ACTIVO",
            Vacunacion.estado.in_((ESPERA_VETERINARIO, ESPERA_APLICACION)),
            Vacunacion.fecha_programada <= hoy,
        )
    )
    if lote is not None:
        consulta = consulta.filter(Vacunacion.lote_id == lote.id)
    if organizacion_id is not None:
        consulta = (
            consulta.join(Galpon, Lote.galpon_id == Galpon.id)
            .join(Granja, Galpon.granja_id == Granja.id)
            .filter(Granja.organizacion_id == organizacion_id)
        )
    nuevas: list[Alerta] = []
    for vacuna in consulta.all():
        veterinario = vacuna.estado == ESPERA_VETERINARIO
        ya_existe = (
            db.query(Alerta)
            .filter(
                Alerta.tipo == "RECORDATORIO",
                Alerta.vacuna_id == vacuna.id,
                Alerta.requiere_veterinario == (1 if veterinario else 0),
            )
            .first()
        )
        if ya_existe:
            continue
        cuando = _cuando((hoy - vacuna.fecha_programada).days)
        fecha = vacuna.fecha_programada.strftime("%d/%m/%Y")
        if veterinario:
            mensaje = f"La vacuna {vacuna.nombre} estaba prevista para {cuando} ({fecha}) y su fecha aún no fue aprobada por el veterinario."
        else:
            mensaje = f"La vacuna {vacuna.nombre} debía aplicarse {cuando} ({fecha}) y no tiene registro de aplicación."
        nuevas.append(_crear(db, vacuna.lote_id, "RECORDATORIO", mensaje, veterinario, vacuna.id))
    return nuevas


def cerrar_recordatorios_vacuna(db: Session, vacuna: Vacunacion, motivo: str) -> None:
    """Cierra solo los recordatorios de esta vacuna (no los de otra con nombre parecido)."""
    for alerta in (
        db.query(Alerta)
        .filter(Alerta.tipo == "RECORDATORIO", Alerta.vacuna_id == vacuna.id, Alerta.estado != "ATENDIDA")
        .all()
    ):
        alerta.estado = "ATENDIDA"
        alerta.observacion = motivo


def cerrar_recordatorios_lote(db: Session, lote_id: int) -> None:
    for alerta in (
        db.query(Alerta)
        .filter(Alerta.tipo == "RECORDATORIO", Alerta.lote_id == lote_id, Alerta.estado != "ATENDIDA")
        .all()
    ):
        alerta.estado = "ATENDIDA"
        alerta.observacion = "Cerrado automáticamente al cerrar el lote."


def carencias_activas(db: Session, lote_id: int, referencia: date | None = None) -> list[dict]:
    """Tratamientos cuya carencia sigue vigente en la fecha de referencia (por defecto hoy).

    Para cerrar el lote, la referencia es la fecha de faena. Los tratamientos observados por el
    veterinario también cuentan: el medicamento ya se aplicó y deja residuos igual.
    """
    dia = referencia or date.today()
    filas = (
        db.query(Tratamiento)
        .filter(Tratamiento.lote_id == lote_id)
        .order_by(Tratamiento.fecha_inicio.desc())
        .all()
    )
    activas = []
    for tratamiento in filas:
        ultima, libre = fechas_tratamiento(
            tratamiento.fecha_inicio,
            tratamiento.dias_tratamiento,
            tratamiento.dias_carencia,
        )
        if dia < libre:
            activas.append(
                {
                    "id": tratamiento.id,
                    "medicamento": tratamiento.medicamento,
                    "libre_faena": libre.isoformat(),
                    "dias_restantes": (libre - dia).days,
                    "estado": tratamiento.estado,
                }
            )
    return activas
