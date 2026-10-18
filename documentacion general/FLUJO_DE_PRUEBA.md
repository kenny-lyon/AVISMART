# Flujo de prueba de AviSmart por rol

Guía paso a paso para probar el sistema completo con los cuatro roles, en orden, con datos de prueba y lo que se debe ver en cada paso.

- **Dirección:** `http://127.0.0.1:5173/login`
- **Organización de prueba:** *Demostración* (Granja de engorde Puno). Clave de todas sus cuentas: `avismart123`
- **Cambiar de rol:** cerrar sesión con el botón ⇥ (abajo a la izquierda) y entrar con la otra cuenta.
- **Fechas:** pensadas para el **14/10/2026**. Si se prueba otro día, desplazarlas igual.

| Rol | Cuenta |
|---|---|
| Propietario de la plataforma | `superperrito15@gmail.com` (clave propia) |
| Productor | `productor@avismart.local` |
| Operario | `operario@avismart.local` |
| Médico veterinario | `veterinario@avismart.local` |
| Administrador heredado (solo Demostración) | `admin@avismart.local` |

---

## 1. Plataforma (administrador general)

Gestiona clientes; no opera granjas avícolas.

1. Sin iniciar sesión, abrir la **web pública → Contacto** y enviar una solicitud de prueba: empresa *Avícola Prueba*, nombre propio y un correo inventado (por ejemplo `prueba@avicola.pe`).
2. Entrar con la cuenta de plataforma. En **Solicitudes** aparece un **1** rojo y la solicitud en la pestaña *Nuevas*.
3. Abrir la solicitud y pulsar **Convertir en cliente**: el formulario sale relleno. Pulsar **Crear cliente** y anotar la **clave temporal del productor** (se muestra una sola vez).
4. Se abre la ficha del cliente. En **Personal del cliente → + Nueva cuenta**, crear un **Operario** y un **Médico veterinario**.
5. Probar **Suspender cliente / Reactivar cliente**: mientras está suspendido, sus cuentas no pueden entrar.

**Debe verse:** la plataforma no tiene Panel, Lotes ni Sanidad; no accede a datos productivos.

---

## 2. Productor: preparar el lote

Cuenta: `productor@avismart.local`

1. **Granjas y galpones → Agregar galpón**: `Galpón 2`, capacidad `3000` (el Galpón 1 está ocupado por el lote de la demo).
2. **Lotes → + Abrir lote**. En el selector, el **Galpón 1 aparece "OCUPADO"** y deshabilitado. Elegir **Galpón 2** y completar:

   | Campo | Valor |
   |---|---|
   | Línea / sexo | Cobb / Mixto |
   | Incubadora o proveedor | Incubadora San Fernando |
   | Fecha de llegada | 08/10/2026 |
   | N.º de guía | T001-000123 |
   | Pollitos recibidos / descartados | 2050 / 30 → se calcula **2.020** en el galpón |
   | Peso al llegar / precio por pollito | 42 g / S/ 2.10 → costo **S/ 4.305** |
   | Peso objetivo / edad de saca | 2800 g / 42 días |

3. **Personal y ajustes → Nueva cuenta**: solo se puede elegir **Operario** o **Médico veterinario**, y las cuentas de administración no aparecen.

---

## 3. Operario: trabajo diario

Cuenta: `operario@avismart.local`. En la barra superior, cambiar el **Lote** a **Galpón 2 · Cobb**.

1. **Registro del día**: guardar tres días.

   | Fecha | Aves muertas | Alimento (kg) | Agua (L) | Peso por ave (g) |
   |---|---|---|---|---|
   | 09/10/2026 | 6 | 45 | 90 | 62 |
   | 11/10/2026 | **25** | 60 | 120 | **80** |
   | 13/10/2026 | 5 | 78 | 150 | 150 |

   **Debe verse:** el 11/10 genera dos alertas, *Salud* (25 muertas, sobre el umbral de 20) y *Crecimiento* (80 g, muy por debajo de la curva).

2. **Panel → Clima del galpón → + Lectura**: 26 °C y 60 %. **Debe verse:** alerta de *Ambiente*, porque a esa edad el rango es 31–34 °C.
3. **Vacunas y tratamientos → Programar vacuna**: *Newcastle + Bronquitis (B1 + H120)*, fecha 09/10/2026. **Debe verse:** en la pestaña *Vacunas* queda como **"Fecha sin aprobar"** y la acción es solo "Ver detalle": no se puede aplicar hasta que el veterinario apruebe la fecha.
4. Cambiar el lote a **Galpón 1 · Ross** y pulsar **Registrar tratamiento**: *Enrofloxacina 10 %*, dosis *10 mg/kg*. Los días de carencia (7) se llenan solos. **Debe verse:** el aviso ámbar **"Lote en carencia"**.

**Debe verse:** el Operario no tiene Lotes, Granjas ni Personal, y no puede atender alertas.

---

## 4. Médico veterinario: sanidad

Cuenta: `veterinario@avismart.local`

1. **Alertas**: la de **Salud** (25 muertas) aparece con franja roja. Abrirla, escribir "Revisión de campo" y pulsar **Marcar atendida**.
2. **Vacunas y tratamientos**:
   - En **Alertas** aparece el recordatorio *"…su fecha aún no fue aprobada por el veterinario"*.
   - Lote **Galpón 2**, pestaña *Vacunas*: **Aprobar fecha**. **Debe verse:** pasa a **"Por aplicar"** y el recordatorio del veterinario se cierra solo.
   - Lote **Galpón 1**, pestaña *Tratamientos*: **Revisar** la Enrofloxacina, escribir un diagnóstico y **Validar**.
3. **Parámetros de alerta**: cambiar el umbral de mortalidad a **15** y guardar (solo el veterinario puede hacerlo).

**Debe verse:** las alertas de *Ambiente* y *Crecimiento* le aparecen como "Ver", porque las atiende el productor.

---

## 5. Productor: atender y cerrar

Cuenta: `productor@avismart.local`

1. **Alertas**: atender las de **Crecimiento** y **Ambiente**. También aparece el recordatorio *"…no tiene registro de aplicación"* de la vacuna.
1b. **Vacunas y tratamientos** (Galpón 2, pestaña *Vacunas*): **Registrar aplicación**, con fecha 09/10/2026 y una nota (por ejemplo, el lote del frasco). **Debe verse:** **"Aplicada · por revisar"** y el recordatorio se cierra. Después, el veterinario entra y pulsa **Dar conformidad** → **"Conforme"**.
2. **Panel** (Galpón 2): pasar el mouse sobre los íconos **?** y sobre el gráfico de peso para ver las explicaciones y el detalle de cada día.
3. **Lotes → Cerrar lote** en **Galpón 2**. La **fecha de faena** viene con la fecha de hoy y se puede cambiar (no puede ser anterior al último registro diario). Aves vendidas y costo de pollitos se llenan solos; completar:

   | Campo | Valor |
   |---|---|
   | Peso total vendido | 800 kg |
   | Precio por kg | S/ 7.50 |
   | Alimento / sanidad / otros | 400 / 50 / 0 |

   **Debe verse:** Ingreso **S/ 6.000** · Costos **S/ 4.755** · Margen **S/ 1.245**. Pulsar **Confirmar cierre**.

4. Pestaña **Cerrados** → descargar **PDF** y **Excel**. El PDF incluye producción (población, mortalidad, FCR, EPEF), gráfico de peso, resultado económico, registros diarios y sanidad.
5. Intentar **cerrar el Galpón 1**. **Debe verse:** el sistema lo bloquea con *"La fecha de faena (…) cae dentro de la carencia de Enrofloxacina 10 %. El lote queda libre para faena desde el …"*. Aunque el veterinario haya **observado** el tratamiento, la carencia sigue contando: el medicamento ya se aplicó.

---

## 6. Administrador heredado (solo Demostración)

Cuenta: `admin@avismart.local`. Existe solo para comparar; los clientes nuevos ya no tienen este rol.

- Ve todo lo de su organización (Personal, Parámetros, Lotes, Granjas) y puede crear Productor, Operario o Veterinario.
- **Debe verse:** no tiene Solicitudes ni Clientes, que son exclusivos de la plataforma.

---

## 7. Formulario de contacto protegido

Detalle completo en `SEGURIDAD_CONTACTO.md`. Prueba rápida en `http://127.0.0.1:5173/contacto`:

1. Correo `ademir@gmial.con` → **"El dominio del correo no existe o no recibe mensajes"**.
2. Correo `bot@mailinator.com` → **"No se aceptan correos temporales o desechables"**.
3. Correo válido de Gmail → **"Revisa tu correo"**. Mientras no confirme, la solicitud **no aparece** en Plataforma → Solicitudes.
4. Abrir el enlace de confirmación (en modo desarrollo, en el recuadro amarillo) → **"¡Correo confirmado!"** y la solicitud aparece en *Nuevas*.
5. Abrir el mismo enlace otra vez → **"El enlace no es válido o ya fue usado"**.

---

## 8. Claves y recuperación de acceso

Usar una cuenta de prueba (por ejemplo, un operario creado por el productor) para no cambiar la clave de las cuentas de demostración.

1. **Primer ingreso con clave temporal:** entrar con la clave temporal → lleva a **Cambiar clave**.
2. **Espacios:** poner una clave nueva que termine en espacio → **"La clave no puede empezar ni terminar con espacios"**.
3. **Ver la clave y Bloq Mayús:** el ojo 👁 muestra la clave; con Bloq Mayús activado aparece el aviso **"Bloq Mayús está activado"**.
4. **Cambiar clave cierra otras sesiones:** con la cuenta abierta en dos navegadores, cambiar la clave en uno → el otro vuelve al login al recargar.
5. **¿Olvidaste tu clave?:** en el login pulsar **"¿Olvidaste tu clave?"**, escribir el correo → **"Si el correo está registrado, te enviamos un enlace…"**. Con un correo que no existe aparece **el mismo mensaje**.
6. Abrir el enlace (en modo desarrollo, en el recuadro amarillo), crear la clave nueva → **"Clave actualizada"**. Entrar con la clave nueva funciona; con la anterior, no.
7. Abrir el mismo enlace otra vez → **"El enlace no es válido o ya fue usado"**.
8. **Emergencia (sin correo):** desde el servidor

   ```powershell
   cd backend
   .\.venv\Scripts\python.exe -m app.restablecer_clave --email correo@dominio.com
   ```

   muestra una clave temporal nueva para esa cuenta.

## 9. Validaciones de datos

Se pueden probar sin guardar nada, porque todos estos datos se rechazan:

| Dónde | Dato | Debe verse |
|---|---|---|
| Registro del día | Peso por ave 5000 g en un lote de 28 días | *"Un peso promedio de 5000 g no es posible para un pollo de 28 días…"* |
| Registro del día | Alimento muy por encima de lo posible | El navegador no deja enviarlo; el servidor responde *"…son más de 350 g por ave al día"* |
| Clima | 500 °C | *"«temperatura (°C)» debe ser menor o igual a 50."* |
| Tratamiento | Fecha de inicio futura | *"…la fecha de inicio no puede ser futura"* |
| Vacuna | Fecha fuera de la campaña | *"La fecha programada debe caer dentro de la campaña…"* |
| Cerrar lote | Lote sin registros diarios | *"El lote no tiene registros diarios…"* |
| Cerrar lote | Fecha de faena anterior al último registro | *"Hay registros diarios hasta el …: la fecha de faena no puede ser anterior"* |
| Cerrar lote | Peso total que da un promedio absurdo | *"…el peso promedio sería … g por ave. Revisa…"* |

## 10. Login, reportes y Telegram

1. **Bloqueo del login** (con un correo que no exista, para no bloquear una cuenta real): 4 claves erróneas → *"Te queda 1 intento antes de un bloqueo temporal"*; al 6.º intento → *"Demasiados intentos fallidos. Espera 15 minutos o usa «¿Olvidaste tu clave?»"*.
2. **Recepción en los reportes:** en un lote cerrado, el PDF tiene la sección **"Recepción de pollitos"** y el Excel una hoja **"Recepción"** (proveedor, guía, sexo, recibidos, descartados, alojados, peso al llegar, precio y costo de pollitos, meta).
3. **Aviso de solicitud nueva:** al confirmar una solicitud de contacto llega un aviso al canal de Telegram de la plataforma y un correo a las cuentas de plataforma (si están configurados).
4. **Telegram por cliente:** como productor, *Personal y ajustes → Notificaciones → Vincular Telegram*. Sin el bot configurado, la pantalla lo explica.

## Notas

- La prueba **deja datos reales** en la base: Galpón 2 con un lote cerrado, un tratamiento en Galpón 1, alertas y el cliente "Avícola Prueba". Para repetirla desde cero se puede restaurar un respaldo de `backend/respaldos/`.
- Devolver el umbral de mortalidad a **20** al terminar, si se cambió a 15.
- Si se registra un tratamiento en un lote, ese lote no se puede cerrar con una fecha de faena anterior al fin de la carencia (se compara con la fecha de faena, no con la de hoy).
- Ciclo de una vacuna: **Fecha por aprobar** → (veterinario aprueba) → **Programada / Por aplicar** → (personal registra la aplicación) → **Aplicada · por revisar** → (veterinario da conformidad) → **Conforme**. En cualquiera de las dos revisiones el veterinario puede **observar**.
- Cada recordatorio de vacuna pertenece a una sola vacuna: atender uno a mano no lo hace reaparecer y al cerrar el lote se cierran los que queden abiertos.
- Mientras no se configure Gmail en `backend/.env`, los enlaces de confirmación y de recuperación se muestran en pantalla (modo desarrollo).
- El formulario de contacto permite 3 solicitudes cada 15 minutos desde la misma computadora.
