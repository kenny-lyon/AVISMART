# Flujo de prueba de AviSmart por rol

Guía paso a paso para probar el sistema completo, en orden, con datos de prueba y lo que se debe ver en cada paso.

- **Levantar el sistema:** doble clic en `AviSmart/iniciar_avismart.bat`. Corre en segundo plano y abre el login; para apagarlo, `detener_avismart.bat`.
- **Dirección:** `http://127.0.0.1:5173/login`
- **Organización de prueba:** *Demostración*. Clave de todas sus cuentas: `avismart123`
- **Cambiar de rol:** cerrar sesión con el botón ⇥ (abajo a la izquierda) y entrar con la otra cuenta.
- **Datos de demostración:** la organización *Demostración* trae una campaña completa lista para mostrar. Se prepara con un comando que calcula las fechas desde **el día en que se ejecuta**: correrlo el mismo día de la presentación (ver la sección 0).

| Rol | Cuenta |
|---|---|
| Propietario de la plataforma | `superperrito15@gmail.com` (clave propia) |
| Productor | `productor@avismart.local` |
| Operario | `operario@avismart.local` |
| Médico veterinario | `veterinario@avismart.local` |
| Administrador heredado (solo Demostración) | `admin@avismart.local` |

---

## 0. Preparar la demostración (el día de la presentación)

Con el sistema levantado, en PowerShell:

```powershell
cd D:\UNIVERSIDAD\8vo\TallerSoftwareII\AviSmart\backend
.\.venv\Scripts\python.exe -m app.demo_docente
```

Guarda un respaldo de la base en `backend/respaldos/` y rehace **solo los datos productivos de Demostración**. Las cuentas y los demás clientes no se tocan, y las claves de las cuentas de demostración quedan en `avismart123`. El resultado es este:

| Dónde | Qué queda |
|---|---|
| Granja | **Granja avícola Santa Rosa**: Juliaca, San Román, Puno, con su punto en el mapa |
| Galpón 01 (6.000) | Lote **Cobb 500 activo en el día 40** (saca prevista el día 42), de San Fernando: 5.000 recibidos y 40 descartados. Tiene 39 días de registros, clima dos veces al día, 5 alertas atendidas y 1 abierta, 6 vacunas (1 por revisar) y un tratamiento con la carencia cumplida |
| Galpón 02 (5.000) | Campaña anterior **Ross 308 cerrada** hace 58 días, de Redondos, con su resultado económico y reportes |
| Galpón 03 (5.000) | Libre, para abrir un lote en vivo |

Los números de las secciones 2 a 5 son los que deja este comando. Se puede volver a correr las veces que haga falta.

---

## 1. Plataforma: de la solicitud al cliente

La plataforma gestiona clientes. No ve datos productivos, salvo cuando entra en **modo soporte** (sección 11).

1. Sin iniciar sesión, abrir la **web pública → Contacto** y enviar una solicitud de prueba:
   - empresa *Avícola Prueba*, nombre propio y un **correo real** (por ejemplo, de Gmail);
   - **Celular (opcional):** `987 654 321`. Un número que no empiece con 9 o no tenga 9 dígitos se rechaza.
2. Aparece **"Revisa tu correo"**. Pulsar **"¿Prefieres hacerlo ahora? Confirmar mi correo"** → **"¡Correo confirmado!"**. Sin confirmar, la solicitud no le llega a la plataforma.
3. Entrar con la cuenta de plataforma. En **Solicitudes**, el número rojo sube en 1 y la solicitud aparece en *Nuevas*. Al abrirla se ven el celular con los enlaces **llamar** y **WhatsApp**.
4. Pulsar **Marcar contactada** → pasa a *Contactadas*.
5. Abrirla y pulsar **Convertir en cliente**: el formulario sale relleno.
   - Para probar el caso "escribió un empleado": cambiar el correo del productor por otro, por ejemplo `dueno.prueba@gmail.com`.
   - Pulsar **Crear cliente** y anotar la **clave temporal del productor** (se muestra una sola vez).
6. Se abre la ficha del cliente.
   - **Debe verse:** si se cambió el productor, el aviso *"Origen: solicitud de … El contacto inicial lo hizo otra persona, no el productor."*
   - La solicitud pasó a la pestaña *Clientes*.
7. **Personal del cliente → + Nueva cuenta**: el rol solo ofrece **Operario** y **Médico veterinario**, porque el productor principal es único. Crear uno de cada uno.
   - Un correo con **ñ** o tildes (por ejemplo, `perezMuñ@gmail.com`) → *"El correo no es válido. Revisa que no tenga espacios, tildes ni ñ"*.
8. Probar **Suspender** y **Reactivar cliente**: mientras está suspendido, sus cuentas no pueden entrar (*"El acceso de tu empresa está suspendido. Comunícate con AviSmart"*).

**Debe verse:**
- Botones de la ficha: **Entrar como soporte** (amarillo) y **Suspender** (rojo).
- Si el cliente está suspendido: **Entrar como soporte**, **Reactivar cliente** y **Eliminar**.

---

## 2. Productor: recorrido por la campaña

Cuenta: `productor@avismart.local`. Se abre el **Panel del lote** de *Galpón 01 · Cobb 500 · día 40*.

1. **Panel del lote.**
   - **Debe verse:** 4.779 aves vivas (181 bajas), mortalidad acumulada **3,65 %**, peso promedio **2.890 g**, conversión **1,58** y EPEF **439**.
   - El gráfico muestra la curva real siguiendo a la esperada de Cobb 500, con un bache en el día 16.
   - **Clima del galpón:** 26,4 °C, fuera del rango de hoy (20–25 °C).
   - Pasar el mouse por los **?** de cada indicador para explicar qué significa.
2. **Alertas** (campana con **1**):
   - Hay **una abierta**: *Ambiente* del día 39 (26,4 °C). Abrirla, escribir "Se abrieron cortinas" y **Marcar atendida**.
   - Pestaña **Atendidas**: el historial de la campaña, cada una con quién la atendió y qué se hizo.
     - *Ambiente* del día 9: noche fría.
     - *Crecimiento* del día 16: pesaje bajo.
     - *Salud* del día 24: 28 bajas y caída del agua del 23 %. Las atendió el veterinario con la necropsia.
3. **Lotes:**
   - *Activos*: el Galpón 01, con su origen (San Fernando) y su recepción.
   - *Cerrados*: la campaña anterior del **Galpón 02 · Ross 308**. Descargar el **PDF** y el **Excel**.
     - Resultado: 4.332 aves vendidas, 12.456 kg a S/ 6,20.
     - Ingreso **S/ 77.227,20**, costos **S/ 63.513,34**, margen **S/ 13.713,86**.
     - El Excel trae las hojas Cierre, Recepción, Registros diarios (con gráfico), Sanidad y Alertas.
4. **Granjas y galpones:**
   - *Granja avícola Santa Rosa*, en **Juliaca, San Román, Puno**, con el enlace **Cómo llegar**. Al pulsar **Editar** se ve el pin en el mapa.
   - Galpón 01 ocupado, Galpón 02 y Galpón 03 libres.
5. **Alimentación:** el plan del lote con la fase de hoy (**Acabado**) y las variaciones que hizo el veterinario. El productor lo consulta; solo el veterinario lo cambia.
6. **Personal y ajustes:** el operario y el veterinario de la granja. Solo se pueden crear operarios y veterinarios.

---

## 3. Médico veterinario: sanidad y alimento

Cuenta: `veterinario@avismart.local`

1. **Vacunas y tratamientos → Vacunas:** la **Gumboro (intermedia plus)** espera su revisión. Pulsar **Revisar**, escribir "Aplicación conforme" y **Dar conformidad** → pasa a **Conforme**.
2. **Programar vacuna** (lo programa el propio veterinario): *Newcastle La Sota (refuerzo)* con fecha de hoy.
   - **Debe verse:** queda directamente como **Por aplicar**, sin pasar por "Fecha por aprobar".
   - Cuando la propone el productor o el operario, en cambio, sí espera la aprobación.
3. **Indicar tratamiento** (receta del veterinario), con estos datos:
   - *Amoxicilina*, *15 mg/kg*, *Agua de bebida*;
   - desde hoy, 3 días, carencia 3;
   - 200 aves;
   - diagnóstico "Enteritis en un sector del galpón".

   **Debe verse:**
   - Aparece como **Indicado · por iniciar**, con la carencia en *"Corre al iniciar"*.
   - Al productor y al operario les llega el aviso *"El veterinario indicó Amoxicilina…"*.
4. **Tratamientos:** la Enrofloxacina del día 24 con su diagnóstico.
   - Es un tratamiento que registró el personal y que el veterinario validó después. Ese camino sigue disponible.
5. **Alimentación:**
   - El plan del lote: Preinicio 0–10, Inicio 11–23, Crecimiento 24–35, **Acabado 36–40 (actual)** y Retiro 41–70.
   - Las **dos variaciones** que hizo el veterinario, con su motivo:
     - Inicio prolongado por el peso bajo del día 16;
     - alimento de retiro por el tratamiento.
   - Pulsar **Variar plan**, cambiar por ejemplo el producto de Retiro, escribir el motivo y guardar → aparece en el historial.
6. **Alertas:** las de *Salud* del día 24 aparecen atendidas por él. Las de *Ambiente* y *Crecimiento* las ve como "Ver", porque las atiende el productor.
7. **Parámetros de alerta:** el umbral de mortalidad diaria está en **20**. Solo el veterinario puede cambiarlo.

---

## 4. Operario: la receta y el registro de hoy

Cuenta: `operario@avismart.local`

1. **Vacunas y tratamientos:**
   - El aviso azul *"El veterinario indicó Amoxicilina (15 mg/kg)…"*.
   - En la tabla, pulsar **Iniciar** → fecha de hoy → **Iniciar tratamiento**.
   - **Debe verse:** pasa a **Conforme**, su carencia empieza a correr y el aviso de Alertas se cierra solo.
   - *Vacunas*:
     - 5 **Conformes**: Marek y Newcastle + Bronquitis vinieron de la incubadora; Gumboro, Bronquitis H120 y Newcastle La Sota se aplicaron en el galpón.
     - La que programó el veterinario, lista para **Registrar aplicación**.
2. **Registro del día** (hoy es el día 40):
   - El campo **Tipo de alimento** ya viene con **Acabado**, el que indica el plan. Solo se cambia si se dio otro.
   - Guardar:

   | Aves muertas | Alimento (kg) | Agua (L) | Peso por ave (g) |
   |---|---|---|---|
   | 2 | 1035 | 1900 | 2960 |

   **Debe verse:** se guarda sin alertas y el Panel se actualiza.
3. **Alimentación:** el plan del lote en modo consulta. Solo el veterinario lo puede variar.
4. **Cámara:** el Galpón 01 sin señal (cámara simulada) y la última lectura de clima.
5. **Debe verse:** el operario no tiene Lotes, Granjas ni Personal, y no puede atender alertas.

---

## 5. Productor: cerrar la campaña

Cuenta: `productor@avismart.local`. Con el lote en el día 40 y la saca prevista el día 42, se puede mostrar el cierre.

> **Ojo con la carencia:** si en las secciones 3 y 4 se indicó e inició la Amoxicilina, el cierre de hoy se **bloquea** con *"La fecha de faena (…) cae dentro de la carencia de Amoxicilina…"*. Es la regla funcionando y sirve para mostrarla. Para hacer además el cierre completo, vuelve a correr `python -m app.demo_docente` antes de esta sección, o muestra el cierre antes de la receta.


1. **Lotes → Cerrar lote** en el **Galpón 01**.
   - La fecha de faena viene con la de hoy.
   - Aves vendidas y costo de pollitos se llenan solos: 5.000 × S/ 2,30 = **S/ 11.500**.
   - Completar:

   | Campo | Valor |
   |---|---|
   | Peso total vendido | 13860 kg (≈ 2.900 g por ave) |
   | Precio por kg | S/ 6.20 |
   | Alimento / sanidad / otros | 46365 / 1050 / 4500 |

   **Debe verse:** ingreso **S/ 85.932** y costos **S/ 63.415**, con un margen cercano a **S/ 22.517**. El alimento sale de 21.565 kg × S/ 2,15. Pulsar **Confirmar cierre**.
2. Pestaña **Cerrados**: ahora están las dos campañas, cada una con su PDF y su Excel.
3. **Abrir un lote nuevo en vivo** en el **Galpón 03**:
   - Línea **Hubbard**: la ayuda de "Peso objetivo" sugiere el peso de la curva para la edad de saca, con el botón **Usar este peso**.
   - Incubadora: elegir de la lista (por ejemplo, **Avinka**) o escribir otra.
   - **Vacunas de la incubadora:** marcar *Marek (HVT)*. Al abrir el lote aparece en Sanidad como **Aplicada · por revisar**.
   - Recibidos 5.000, descartados 30, peso al llegar 42 g, precio S/ 2.30.

> Si no se quiere cerrar el lote durante la presentación, basta con mostrar el formulario y pulsar **Cancelar**.

---

## 6. Administrador heredado (solo Demostración)

Cuenta: `admin@avismart.local`. Existe solo para comparar; los clientes nuevos ya no tienen este rol.

- Ve todo lo de su organización: Personal, Parámetros, Lotes y Granjas. Puede crear **Operario** o **Veterinario**, pero no productores.
- **Debe verse:** no tiene Solicitudes ni Clientes, que son exclusivos de la plataforma.

---

## 7. Formulario de contacto protegido

Detalle completo en `SEGURIDAD_CONTACTO.md`. Prueba rápida en `http://127.0.0.1:5173/contacto`:

1. Correo `ademir@gmial.con` → **"El dominio del correo no existe o no recibe mensajes"**.
2. Correo `bot@mailinator.com` → **"No se aceptan correos temporales o desechables"**.
3. Celular `12345` → **"El celular debe tener 9 dígitos y empezar con 9…"**. Dejarlo vacío también es válido.
4. Correo válido de Gmail → **"Revisa tu correo"**. Mientras no se confirme, la solicitud **no aparece** en Plataforma → Solicitudes.
5. Pulsar **"Confirmar mi correo"** → **"¡Correo confirmado!"** y la solicitud aparece en *Nuevas*.
6. Abrir el mismo enlace otra vez → **"El enlace no es válido o ya fue usado"**.

---

## 8. Claves y recuperación de acceso

Usar una cuenta de prueba (por ejemplo, un operario creado por el productor) para no cambiar la clave de las cuentas de demostración.

1. **Primer ingreso con clave temporal:** entrar con la clave temporal → lleva a **Cambiar clave**.
2. **Espacios:** poner una clave nueva que termine en espacio → **"La clave no puede empezar ni terminar con espacios"**.
3. **Ver la clave y Bloq Mayús:** el ojo 👁 muestra la clave; con Bloq Mayús activado aparece el aviso **"Bloq Mayús está activado"**.
4. **Cambiar clave cierra otras sesiones:** con la cuenta abierta en dos navegadores, cambiar la clave en uno → el otro vuelve al login al recargar.
5. **¿Olvidaste tu clave?:** en el login pulsar **"¿Olvidaste tu clave?"** y escribir el correo → **"Si el correo está registrado, te enviamos un enlace…"**. Con un correo que no existe aparece **el mismo mensaje**.
6. Pulsar **"¿Prefieres hacerlo ahora? Crear mi clave nueva"** y crear la clave → **"Clave actualizada"**. Entrar con la clave nueva funciona; con la anterior, no.
7. Abrir el mismo enlace otra vez → **"El enlace no es válido o ya fue usado"**.
8. **Emergencia (sin correo):** desde el servidor:

   ```powershell
   cd backend
   .\.venv\Scripts\python.exe -m app.restablecer_clave --email correo@dominio.com
   ```

   Muestra una clave temporal nueva para esa cuenta.

---

## 9. Validaciones de datos

Se pueden probar sin guardar nada, porque todos estos datos se rechazan:

| Dónde | Dato | Debe verse |
|---|---|---|
| Registro del día | Peso por ave 500 g en el lote del día 40 | *"Un peso promedio de 500 g no es posible para un pollo de 40 días…"* |
| Registro del día | Alimento muy por encima de lo posible | El navegador no deja enviarlo; el servidor responde *"…son más de 350 g por ave al día"* |
| Clima | 500 °C | *"«temperatura (°C)» debe ser menor o igual a 50."* |
| Tratamiento | Fecha de inicio futura | *"…la fecha de inicio no puede ser futura"* |
| Vacuna | Fecha fuera de la campaña | *"La fecha programada debe caer dentro de la campaña…"* |
| Cerrar lote | Lote sin registros diarios | *"El lote no tiene registros diarios…"* |
| Cerrar lote | Fecha de faena anterior al último registro | *"Hay registros diarios hasta el …: la fecha de faena no puede ser anterior"* |
| Cerrar lote | Peso total que da un promedio absurdo | *"…el peso promedio sería … g por ave. Revisa…"* |
| Nueva cuenta | Correo con ñ o tildes | *"El correo no es válido. Revisa que no tenga espacios, tildes ni ñ"* |

---

## 10. Login, reportes y Telegram

1. **Bloqueo del login** (usar un correo que no exista, para no bloquear una cuenta real):
   - con 4 claves erróneas → *"Te queda 1 intento antes de un bloqueo temporal"*;
   - al 6.º intento → *"Demasiados intentos fallidos. Espera 15 minutos o usa «¿Olvidaste tu clave?»"*.
2. **Recepción en los reportes:** en un lote cerrado, el PDF tiene la sección **"Recepción de pollitos"** y el Excel una hoja **"Recepción"**. Incluyen proveedor, guía, sexo, recibidos, descartados, alojados, peso al llegar, precio y costo de pollitos, y meta.
3. **Aviso de solicitud nueva:** al confirmar una solicitud de contacto llega un aviso al canal de Telegram de la plataforma y un correo a las cuentas de plataforma, si están conectados.
4. **Telegram por cliente:** como productor, *Personal y ajustes → Notificaciones → Vincular Telegram*. Si no está activo, la pantalla dice *"Las alertas por Telegram aún no están activas para tu cuenta. Escríbenos desde Soporte y las activamos."*

---

## 11. Plataforma: solicitudes, soporte y baja de clientes

Cuenta de plataforma.

### 11.1 Pestañas de Solicitudes

| Pestaña | Qué muestra | Botones al abrir |
|---|---|---|
| Nuevas | Sin atender | Descartar · Marcar contactada · Convertir en cliente |
| Contactadas | Ya se habló con la persona | Descartar · Convertir en cliente |
| Clientes | Clientes **vigentes** | — |
| Descartadas | Descartadas y **clientes dados de baja** | Volver a Nuevas (solo las descartadas) |
| Todas | Historial completo, sin las sospechosas | — |
| Sospechosas | Separadas por el antispam | Es legítima · Descartar |

**Debe verse:** una solicitud descartada **no** tiene "Convertir en cliente".

### 11.2 Un correo, una cuenta

1. Enviar desde Contacto una solicitud con el **correo del productor de un cliente existente** (por ejemplo, `productor@avismart.local` no sirve porque `.local` no recibe correos; usar el Gmail de un cliente creado en la sección 1).
2. **Debe verse:**
   - En la lista, debajo del nombre: *"· ya es cliente: …"*.
   - Al abrirla, el aviso *"Este correo ya tiene una cuenta en el cliente …"*. Si está suspendido, el aviso indica cómo reactivarlo.
   - En lugar de **Convertir en cliente** aparece **Ver cliente**.
3. Si aun así se intenta crear el cliente, el sistema lo rechaza: *"Ese correo ya tiene una cuenta en el cliente «…»…"*.

### 11.3 Modo soporte

1. Ficha de un cliente → **Entrar como soporte**.
2. **Debe verse:**
   - El sistema del cliente con permisos de productor.
   - La franja amarilla *"Modo soporte en … Trabajas con los permisos de su productor y lo que hagas queda registrado a tu nombre"*.
   - Abajo a la izquierda, **"Soporte AviSmart"**.
3. Registrar una granja y un galpón, y abrir el primer lote: quedan en ese cliente.
4. **Salir del modo soporte** → vuelve a la ficha del cliente con la sesión de plataforma.
5. **Debe verse:** el modo soporte no da acceso a las pantallas de plataforma ni permite cambiar la clave, y dura como máximo 4 horas.

### 11.4 Eliminar un cliente

1. Ficha del cliente de prueba → **Suspender**. Aparece el botón **Eliminar**.
2. **Eliminar** → el panel pide **escribir el nombre del cliente**. Con un nombre distinto no se borra nada.
3. Escribir el nombre y pulsar **Eliminar para siempre**.
4. **Debe verse:**
   - Se descarga un archivo `cliente_<nombre>_<fecha>.json` con toda su información, sin claves.
   - Se vuelve a la lista con el aviso *"… fue eliminado. Se descargó el archivo con su información."*
   - Su solicitud pasa a *Descartadas* como **"Cliente dado de baja"**.
   - Su correo queda libre para volver a usarse.
5. En el servidor quedan la copia de respaldo `backend/respaldos/avismart_antes_eliminar_<nombre>_<fecha>.db` y la exportación en `backend/respaldos/clientes/`.

---

## Notas

- **Antes de la presentación:** correr `python -m app.demo_docente` (sección 0). Si algo se desordena durante la prueba, se vuelve a correr y todo queda igual que al inicio.
- **Respaldo manual.** Con el sistema apagado (`detener_avismart.bat`), en PowerShell:

  ```powershell
  cd backend
  Copy-Item avismart.db "respaldos\avismart_antes_prueba_$(Get-Date -Format yyyyMMdd_HHmm).db"
  ```

  Para volver a ese estado: apagar el sistema, copiar el respaldo encima de `avismart.db` y volver a levantarlo.
- **Otros datos que ya existen:** el cliente **Avicola Ruelas**, con productor, operario y veterinario. En Solicitudes, *Avicola Ruelas* está en **Clientes** y *produjhonel* en **Descartadas**.
- Devolver el umbral de mortalidad a **20** al terminar, si se cambió.
- Si un lote tiene un tratamiento, no se puede cerrar con una fecha de faena anterior al fin de la carencia. Se compara con la fecha de faena, no con la de hoy.
- Ciclo de una vacuna: **Fecha por aprobar** → (veterinario aprueba) → **Programada / Por aplicar** → (personal registra la aplicación) → **Aplicada · por revisar** → (veterinario da conformidad) → **Conforme**. En cualquiera de las dos revisiones el veterinario puede **observar**. Las vacunas de la incubadora entran directo como **Aplicada · por revisar**, y las que programa el veterinario, como **Por aplicar**.
- Tratamientos: el personal puede registrar lo que ya aplicó (el veterinario lo valida después) o el veterinario lo **indica** y el personal lo **inicia**. La carencia de un tratamiento indicado corre desde que se inicia.
- Alimentación: cada lote nuevo empieza con el plan base (Preinicio, Inicio, Crecimiento, Acabado). Solo el veterinario lo varía y cada cambio queda con su motivo.
- Cada recordatorio de vacuna pertenece a una sola vacuna. Atender uno a mano no lo hace reaparecer, y al cerrar el lote se cierran los que queden abiertos.
- Mientras el envío de correos no esté conectado, los enlaces de confirmación y de recuperación aparecen en pantalla como **"¿Prefieres hacerlo ahora?"**. Con el correo conectado, solo llegan por email.
- El formulario de contacto permite 3 solicitudes cada 15 minutos desde la misma computadora.
