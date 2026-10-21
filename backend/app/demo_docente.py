"""Prepara la organización «Demostración» con una campaña completa para presentar AviSmart.

Todas las fechas se calculan desde HOY, así que conviene ejecutarlo el día de la presentación:

    cd backend
    .\\.venv\\Scripts\\python.exe -m app.demo_docente

Deja:
  - Granja avícola con ubigeo y punto en el mapa (Juliaca, San Román, Puno).
  - Galpón 01: lote Cobb 500 ACTIVO en el día 40 (saca prevista a los 42 días), con registros diarios,
    clima, alertas atendidas y una abierta, vacunas con su ciclo completo (una por revisar) y un tratamiento
    con la carencia ya cumplida.
  - Galpón 02: campaña anterior Ross 308 CERRADA, con su resultado económico y reportes.
  - Galpón 03: libre, para abrir un lote en vivo.
Solo toca los datos productivos de «Demostración»; las cuentas y los demás clientes no se modifican.
Antes de cambiar nada guarda una copia de la base en backend/respaldos/.
"""
import random
import shutil
from datetime import date, datetime, time, timedelta
from pathlib import Path

from .baja_cliente import _consultas
from .db import DB_PATH, SessionLocal
from .logic import evaluar_clima, evaluar_registro, fase_del_dia, peso_esperado, plan_alimento, rango_temperatura
from .models import (
    Alerta,
    CambioAlimento,
    CierreLote,
    FaseAlimento,
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
from .security import establecer_clave, verify_password

CLAVE_DEMO = "avismart123"
CUENTAS_DEMO = ("productor@avismart.local", "operario@avismart.local", "veterinario@avismart.local", "admin@avismart.local")
# Consumo diario de alimento por ave (g): referencia de las guías + 12 % por la altura (sierra).
CONSUMO = [(1, 13), (7, 35), (14, 67), (21, 106), (28, 146), (35, 181), (42, 206), (49, 222)]

rnd = random.Random(2026)


def _interpolar(puntos, dia):
    if dia <= puntos[0][0]:
        return puntos[0][1]
    for (d0, v0), (d1, v1) in zip(puntos, puntos[1:]):
        if dia <= d1:
            return v0 + (v1 - v0) * (dia - d0) / (d1 - d0)
    return puntos[-1][1]


def _momento(dia: date, hora: int, minuto: int = 0) -> datetime:
    return datetime.combine(dia, time(hora, minuto))


def _respaldar() -> Path:
    destino = Path(DB_PATH).parent / "respaldos" / f"avismart_antes_demo_docente_{datetime.now():%Y%m%d_%H%M%S}.db"
    destino.parent.mkdir(exist_ok=True)
    shutil.copy2(DB_PATH, destino)
    return destino


def _campana(db, lote: Lote, dias: int, operario: Usuario, productor: Usuario, eventos: dict) -> tuple[float, float, int]:
    """Registros diarios y clima del día 1 al `dias`. Devuelve (alimento total kg, peso final g, aves vivas)."""
    vivas = lote.poblacion_inicial
    fases = plan_alimento(db, lote)
    alimento_total = 0.0
    peso = lote.peso_llegada_g or 42
    for dia in range(1, dias + 1):
        fecha = lote.fecha_ingreso + timedelta(days=dia)
        evento = eventos.get(dia, {})
        tasa = 0.0024 if dia <= 3 else 0.0012 if dia <= 7 else 0.0006
        muertes = evento.get("muertes", max(0, round(vivas * tasa * rnd.uniform(0.6, 1.4))))
        vivas -= muertes
        alimento = round(vivas * _interpolar(CONSUMO, dia) * 1.12 * rnd.uniform(0.97, 1.03) / 1000, 1)
        agua = round(alimento * rnd.uniform(1.75, 1.9) * evento.get("agua", 1), 1)
        peso = round(peso_esperado(dia, lote.linea) * evento.get("peso", rnd.uniform(0.965, 1.0)))
        alimento_total += alimento
        registro = RegistroDiario(
            lote_id=lote.id,
            usuario_id=(productor if dia % 7 == 0 else operario).id,
            fecha=fecha,
            mortalidad=muertes,
            alimento_kg=alimento,
            agua_l=agua,
            peso_muestra_g=peso,
            fase_alimento=(fase_del_dia(fases, dia).nombre if fase_del_dia(fases, dia) else None),
        )
        db.add(registro)
        db.flush()
        for alerta in evaluar_registro(db, lote, registro):
            alerta.creada_en = _momento(fecha, 18, 30)
        db.flush()

        # Clima: una lectura en la mañana y otra en la tarde, dentro del rango salvo los días con evento.
        tmin, tmax = rango_temperatura(dia)
        for hora, ajuste in ((7, -0.6), (15, 0.6)):
            temperatura = evento.get("temperatura") if hora == 15 and "temperatura" in evento else round((tmin + tmax) / 2 + ajuste + rnd.uniform(-0.4, 0.4), 1)
            lectura = LecturaAmbiental(
                galpon_id=lote.galpon_id,
                fecha_hora=_momento(fecha, hora, rnd.randint(0, 50)),
                temperatura=temperatura,
                humedad=round(rnd.uniform(56, 66), 1),
                origen="SIMULADO",
            )
            db.add(lectura)
            db.flush()
            for alerta in evaluar_clima(db, lote, lectura):
                alerta.creada_en = lectura.fecha_hora
            db.flush()
    return alimento_total, peso, vivas


def _vacuna(db, lote, nombre, dia, estado, operario, veterinario, incubadora=False, nota=""):
    fecha = lote.fecha_ingreso + timedelta(days=dia)
    db.add(
        Vacunacion(
            lote_id=lote.id,
            nombre=nombre,
            fecha_programada=fecha,
            estado=estado,
            observacion="Aplicación conforme." if estado == "VALIDADA" else "",
            aprobada_por=None if incubadora else veterinario.id,
            fecha_aplicacion=fecha,
            aplicada_por=operario.id,
            nota_aplicacion=nota or (f"Aplicada en la incubadora ({lote.proveedor})." if incubadora else "Aplicada en el galpón."),
            validado_por=veterinario.id if estado == "VALIDADA" else None,
        )
    )


def _atender_alertas(db, lote: Lote, hasta: date, productor: Usuario, veterinario: Usuario):
    notas = {
        "SALUD": "Necropsia de 5 aves: lesiones compatibles con colibacilosis. Se indicó Enrofloxacina por 5 días.",
        "CRECIMIENTO": "Se revisó la muestra y el comedero; se ajustó la altura de comederos y la ventilación.",
        "AMBIENTE": "Se regularon las cortinas y la criadora; la temperatura volvió al rango.",
    }
    for alerta in db.query(Alerta).filter(Alerta.lote_id == lote.id):
        if alerta.creada_en.date() <= hasta:
            alerta.estado = "ATENDIDA"
            alerta.observacion = notas.get(alerta.tipo, "Revisado.")
            alerta.atendida_por = (veterinario if alerta.requiere_veterinario else productor).id


def preparar() -> None:
    hoy = date.today()
    respaldo = _respaldar()
    db = SessionLocal()
    try:
        productor = db.query(Usuario).filter_by(email="productor@avismart.local").one()
        organizacion = db.get(Organizacion, productor.organizacion_id)
        operario = db.query(Usuario).filter_by(email="operario@avismart.local").one()
        veterinario = db.query(Usuario).filter_by(email="veterinario@avismart.local").one()

        # Cuentas de demostración activas y con la clave conocida.
        for usuario in db.query(Usuario).filter(Usuario.email.in_(CUENTAS_DEMO)):
            usuario.activo = 1
            if not verify_password(CLAVE_DEMO, usuario.password_hash) or usuario.debe_cambiar_clave:
                establecer_clave(usuario, CLAVE_DEMO, temporal=False)
        organizacion.estado = "ACTIVA"

        # Borra solo lo productivo de la organización (granjas, galpones, lotes y todo lo que cuelga de ellos).
        for nombre, consulta in _consultas(db, organizacion).items():
            if nombre not in ("usuarios", "configuracion", "intentos_login", "intentos_recuperacion"):
                consulta.delete(synchronize_session=False)
        db.flush()

        granja = Granja(
            nombre="Granja avícola Santa Rosa",
            ubicacion="Juliaca, San Román, Puno",
            departamento="Puno",
            provincia="San Román",
            distrito="Juliaca",
            latitud=-15.5136,
            longitud=-70.1592,
            organizacion_id=organizacion.id,
        )
        db.add(granja)
        db.flush()
        galpones = []
        for numero, capacidad in ((1, 6000), (2, 5000), (3, 5000)):
            galpon = Galpon(granja_id=granja.id, nombre=f"Galpón {numero:02d}", capacidad=capacidad,
                            camara_nombre="Cámara principal", camara_modo="SIMULADA", camara_activa=1)
            db.add(galpon)
            galpones.append(galpon)
        db.flush()

        # ---------------------------------------------------------------- campaña anterior (cerrada)
        ingreso_anterior = hoy - timedelta(days=100)
        anterior = Lote(
            galpon_id=galpones[1].id, linea="Ross 308", fecha_ingreso=ingreso_anterior, poblacion_inicial=4475,
            peso_objetivo_g=2900, proveedor="Redondos", guia="T002-001874", sexo="MIXTO", cantidad_recibida=4500,
            descarte_llegada=25, peso_llegada_g=41.5, precio_pollito=2.20, edad_saca_dias=42,
            observaciones="Pollitos activos y uniformes. Transporte a 30 °C.", estado="ACTIVO",
        )
        db.add(anterior)
        db.flush()
        alimento_ant, peso_ant, vivas_ant = _campana(db, anterior, 42, operario, productor, {20: {"peso": 0.88}})
        for nombre, dia, incubadora in (("Marek (HVT)", 0, True), ("Newcastle + Bronquitis (B1 + H120)", 0, True),
                                        ("Gumboro (cepa intermedia)", 14, False), ("Newcastle La Sota (refuerzo)", 18, False)):
            _vacuna(db, anterior, nombre, dia, "VALIDADA", operario, veterinario, incubadora)
        db.add(Tratamiento(lote_id=anterior.id, medicamento="Amoxicilina", dosis="15 mg/kg", via="Agua de bebida",
                           fecha_inicio=ingreso_anterior + timedelta(days=21), dias_tratamiento=5, dias_carencia=3,
                           estado="VALIDADA", diagnostico="Enteritis leve; heces húmedas en un sector del galpón.",
                           validado_por=veterinario.id))
        fecha_faena = ingreso_anterior + timedelta(days=42)
        peso_total = round(vivas_ant * peso_ant / 1000 * 0.98)
        costos = {
            "costo_pollitos": round(anterior.cantidad_recibida * anterior.precio_pollito, 2),
            "costo_alimento": round(alimento_ant * 2.15, 2),
            "costo_sanidad": 980.0,
            "otros_costos": 4500.0,
        }
        ingreso_venta = round(peso_total * 6.20, 2)
        total = round(sum(costos.values()), 2)
        db.add(CierreLote(lote_id=anterior.id, fecha_cierre=fecha_faena, aves_vendidas=vivas_ant, peso_total_kg=peso_total,
                          precio_venta_kg=6.20, ingreso_total=ingreso_venta, total_costos=total, margen=round(ingreso_venta - total, 2),
                          observaciones="Venta a camal de Juliaca. Otros costos: gas de criadoras, cama de viruta, luz y mano de obra.", cerrado_por=productor.id,
                          created_at=_momento(fecha_faena, 17), **costos))
        anterior.estado = "CERRADO"
        anterior.fecha_cierre = fecha_faena
        _atender_alertas(db, anterior, fecha_faena, productor, veterinario)

        # ---------------------------------------------------------------- campaña actual (día 40)
        ingreso = hoy - timedelta(days=40)
        actual = Lote(
            galpon_id=galpones[0].id, linea="Cobb 500", fecha_ingreso=ingreso, poblacion_inicial=4960,
            peso_objetivo_g=3200, proveedor="San Fernando", guia="T001-004512", sexo="MIXTO", cantidad_recibida=5000,
            descarte_llegada=40, peso_llegada_g=42, precio_pollito=2.30, edad_saca_dias=42,
            observaciones="Llegaron activos; 40 descartados por ombligo mal cicatrizado.", estado="ACTIVO",
        )
        db.add(actual)
        db.flush()
        # Plan de alimentación con dos variaciones del veterinario (Inicio más largo y alimento de retiro).
        for nombre, desde, hasta, presentacion, producto in (
            ("Preinicio", 0, 10, "Migaja", "Preinicio pollo BB"),
            ("Inicio", 11, 23, "Migaja o pellet pequeño", "Inicio pollo de carne"),
            ("Crecimiento", 24, 35, "Pellet", "Crecimiento pollo de carne"),
            ("Acabado", 36, 40, "Pellet", "Acabado pollo de carne"),
            ("Retiro", 41, 70, "Pellet", "Acabado sin medicamentos"),
        ):
            db.add(FaseAlimento(lote_id=actual.id, nombre=nombre, dia_desde=desde, dia_hasta=hasta, presentacion=presentacion, producto=producto))
        for dia, motivo, detalle in (
            (17, "Peso bajo el día 16: se prolonga el alimento de Inicio hasta el día 23.",
             "Antes: Preinicio 0-10; Inicio 11-21; Crecimiento 22-35; Acabado 36-70. Ahora: Preinicio 0-10; Inicio 11-23; Crecimiento 24-35; Acabado 36-70."),
            (33, "Tratamiento con Enrofloxacina: alimento de retiro sin medicamentos desde el día 41 hasta la faena.",
             "Antes: Acabado 36-70. Ahora: Acabado 36-40; Retiro 41-70 (Acabado sin medicamentos)."),
        ):
            db.add(CambioAlimento(lote_id=actual.id, usuario_id=veterinario.id, fecha=_momento(ingreso + timedelta(days=dia), 10, 15),
                                  motivo=motivo, detalle=detalle))
        db.flush()
        eventos = {
            9: {"temperatura": 25.8},          # noche fría: alerta de ambiente (atendida)
            16: {"peso": 0.87},                # pesaje bajo: alerta de crecimiento (atendida)
            24: {"muertes": 28, "agua": 0.7},  # brote: alerta de salud (atendida) y tratamiento
            39: {"temperatura": 26.4},         # ayer, tarde calurosa: alerta de ambiente ABIERTA
        }
        _campana(db, actual, 39, operario, productor, eventos)
        for nombre, dia, estado, incubadora in (
            ("Marek (HVT)", 0, "VALIDADA", True),
            ("Newcastle + Bronquitis (B1 + H120)", 0, "VALIDADA", True),
            ("Gumboro (cepa intermedia)", 14, "VALIDADA", False),
            ("Bronquitis infecciosa (H120 refuerzo)", 14, "VALIDADA", False),
            ("Newcastle La Sota (refuerzo)", 18, "VALIDADA", False),
            ("Gumboro (intermedia plus)", 21, "APLICADA", False),  # espera la conformidad del veterinario
        ):
            _vacuna(db, actual, nombre, dia, estado, operario, veterinario, incubadora)
        db.add(Tratamiento(lote_id=actual.id, medicamento="Enrofloxacina 10 %", dosis="10 mg/kg", via="Agua de bebida",
                           fecha_inicio=ingreso + timedelta(days=24), dias_tratamiento=5, dias_carencia=7, aves_tratadas=None,
                           estado="VALIDADA", diagnostico="Colibacilosis: mortalidad alta el día 24 y lesiones en la necropsia.",
                           validado_por=veterinario.id))
        _atender_alertas(db, actual, hoy - timedelta(days=2), productor, veterinario)

        db.commit()
        print(f"Respaldo previo: {respaldo}")
        print(f"Granja: {granja.nombre} · {granja.ubicacion}")
        print(f"Galpón 01: lote Cobb 500 activo, ingreso {ingreso:%d/%m/%Y} (día 40, saca prevista el {(ingreso + timedelta(days=42)):%d/%m/%Y})")
        print(f"Galpón 02: lote Ross 308 cerrado el {fecha_faena:%d/%m/%Y} · margen S/ {ingreso_venta - total:,.2f}")
        print("Galpón 03: libre")
        abiertas = db.query(Alerta).filter(Alerta.lote_id == actual.id, Alerta.estado != "ATENDIDA").count()
        print(f"Alertas abiertas del lote actual: {abiertas}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    preparar()
