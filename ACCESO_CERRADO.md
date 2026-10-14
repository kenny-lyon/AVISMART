# Acceso cerrado de AviSmart

AviSmart no ofrece registro público. Una instalación atiende a varios clientes; cada cliente es una **organización** y solo ve sus propios datos.

## Niveles de acceso

1. **Visitante:** no tiene credenciales. Conoce el producto y envía una solicitud desde `/contacto`.
2. **Propietario de la plataforma (`PLATAFORMA`):** el equipo AviSmart. Revisa las solicitudes, crea clientes, suspende o reactiva organizaciones y recupera el acceso de sus administradores. **No ve datos productivos** (panel, sanidad, lotes).
3. **Cuentas de una organización cliente** (siempre dentro de su organización):
   - **Productor:** el responsable del cliente. Gestiona granjas avícolas, galpones y lotes, y da de alta, desactiva o restablece a sus **Operativos y Médicos veterinarios**.
   - **Operativo:** registro diario del galpón.
   - **Médico veterinario:** valida sanidad y ajusta el **umbral de mortalidad**.
   - El rol `ADMIN` ya no se crea para clientes; solo existe en la organización **Demostración**.

## Primera cuenta de la instalación

La cuenta de plataforma se crea una vez desde el servidor:

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.bootstrap_admin --nombre "Nombre del propietario" --email "propietario@dominio.com"
```

El comando muestra una clave temporal una sola vez y obliga a cambiarla al ingresar. Para sumar más personas del equipo AviSmart se usa **Cuentas de plataforma** dentro del sistema.

## Alta de un cliente

1. El interesado envía el formulario de **Contacto**; la solicitud aparece en **Solicitudes**.
2. El propietario de la plataforma pulsa **Convertir en cliente** (o crea el cliente directamente en **Clientes**).
3. AviSmart crea la organización y la cuenta de su **Productor** con una clave temporal que se muestra una sola vez.
4. La clave se entrega por un canal privado, idealmente separado del correo.
5. En **Clientes → (cliente) → Personal del cliente**, la plataforma puede crear de inmediato sus Operativos y Veterinarios. El productor también puede hacerlo desde **Personal y ajustes**.
6. El productor entra, crea su clave personal y registra su **granja avícola y galpones**.

## Bajas y recuperación

- El Productor desactiva o restablece las cuentas de sus operativos y veterinarios.
- La plataforma gestiona a todo el personal del cliente, incluido el Productor (restablecer clave, desactivar, agregar otro productor). Siempre debe quedar al menos un Productor activo.
- **Suspender** un cliente impide entrar a todas sus cuentas de inmediato, sin borrar sus datos.

Las claves no se guardan como texto legible: la base conserva solamente un hash con sal.

## Separación de datos

Cada consulta del sistema filtra por la organización de quien la hace. Pedir un lote, vacuna, tratamiento, alerta, galpón o cuenta de otro cliente responde "no encontrado". El umbral de mortalidad también es propio de cada organización.

Las notificaciones por Telegram todavía usan un único canal para toda la instalación.

## Datos de demostración

Los datos creados antes de separar clientes quedaron en la organización **Demostración** (cuentas `@avismart.local`). La carga automática de demostración está desactivada por defecto: solo se habilita con `AVISMART_DEMO=true` y `AVISMART_DEMO_PASSWORD`, y no se usa en una instalación entregada a un cliente.
