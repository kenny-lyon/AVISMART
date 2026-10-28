export type Rol = "PLATAFORMA" | "ADMIN" | "PRODUCTOR" | "OPERARIO" | "VETERINARIO";

export const ROLES_CLIENTE: Rol[] = ["ADMIN", "PRODUCTOR", "OPERARIO", "VETERINARIO"];
export const ROLES_PERSONAL: Rol[] = ["PRODUCTOR", "OPERARIO", "VETERINARIO"];

/** Avisa a la barra lateral que vuelva a contar alertas o solicitudes. */
export function avisarCambios() {
  window.dispatchEvent(new Event("avismart:cambios"));
}

export type Usuario = {
  id: number;
  nombre: string;
  email: string;
  rol: Rol;
  activo: boolean;
  debe_cambiar_clave: boolean;
  organizacion: { id: number; nombre: string } | null;
  /** Cuenta de plataforma trabajando dentro de un cliente (modo soporte). */
  soporte?: boolean;
  telefono?: string | null;
  correo_alterno?: string | null;
};

export type Galpon = { id: number; nombre: string; capacidad: number; granja_id: number; granja: string };

export type Granja = {
  id: number;
  nombre: string;
  ubicacion: string;
  departamento: string | null;
  provincia: string | null;
  distrito: string | null;
  latitud: number | null;
  longitud: number | null;
  galpones: Galpon[];
};

export type Organizacion = {
  id: number;
  nombre: string;
  estado: "ACTIVA" | "SUSPENDIDA";
  creada_en: string | null;
  solicitud_id: number | null;
  /** Quién escribió la solicitud, cuando no es el productor del cliente. */
  origen: { nombre: string; email: string; fecha: string } | null;
  usuarios_activos: number;
  granjas: number;
  lotes_activos: number;
  responsables: Usuario[];
  personal: Record<"PRODUCTOR" | "OPERARIO" | "VETERINARIO", number>;
  telegram_vinculado: boolean;
};

export type Lote = {
  id: number;
  linea: string;
  fecha_ingreso: string;
  poblacion_inicial: number;
  peso_objetivo_g: number;
  proveedor: string | null;
  guia: string | null;
  sexo: string | null;
  cantidad_recibida: number | null;
  descarte_llegada: number | null;
  peso_llegada_g: number | null;
  precio_pollito: number | null;
  costo_pollitos: number | null;
  edad_saca_dias: number | null;
  observaciones: string | null;
  estado: string;
  fecha_cierre: string | null;
  dia_vida: number;
  galpon_id: number;
  galpon: string;
  granja_id: number;
  granja: string;
  ubicacion: string;
};

export type CierreLote = {
  id: number;
  lote_id: number;
  fecha_cierre: string;
  aves_vendidas: number;
  peso_total_kg: number;
  precio_venta_kg: number;
  ingreso_total: number;
  costo_pollitos: number;
  costo_alimento: number;
  costo_sanidad: number;
  otros_costos: number;
  total_costos: number;
  margen: number;
  observaciones: string;
};

export type Resumen = {
  organizacion: { id: number; nombre: string };
  granja: { id: number; nombre: string; ubicacion: string } | null;
  granjas: Granja[];
  galpones: Galpon[];
  lotes: Lote[];
  umbral_mortalidad: number;
};

export type Alerta = {
  id: number;
  lote_id: number;
  lote: string;
  tipo: string;
  mensaje: string;
  estado: string;
  requiere_veterinario: boolean;
  observacion: string;
  creada_en: string;
  notificacion_estado: string;
  notificacion_error: string;
  notificada_en: string | null;
};

export type TelegramEstado = {
  canal: string;
  configurado: boolean;
  chat_configurado: boolean;
};

export type SolicitudContacto = {
  id: number;
  nombre: string;
  email: string;
  empresa: string;
  pais: string;
  aves: string;
  motivo: "DEMO" | "COMERCIAL" | "SOPORTE" | "ALIANZA";
  plan: string;
  mensaje: string;
  estado: "NUEVA" | "CONTACTADA" | "DESCARTADA" | "CLIENTE" | "SOSPECHOSA" | "BAJA";
  telefono: string | null;
  /** El correo ya tiene cuenta en AviSmart: no se debe crear otro cliente con él. */
  cuenta_existente: {
    rol: string;
    activo: boolean;
    organizacion: { id: number; nombre: string; estado: string } | null;
  } | null;
  creada_en: string;
  atendida_en: string | null;
  verificada_en: string | null;
  motivo_sospecha: string | null;
};

export type Panel = {
  lote: Lote;
  dia_vida: number;
  aves_vivas: number;
  muertes: number;
  mortalidad_acumulada: number;
  alimento_kg: number;
  peso_actual_g: number;
  peso_esperado_g: number;
  ganancia_diaria_g: number;
  fcr: number | null;
  epef: number | null;
  temp_min: number;
  temp_max: number;
  alertas_abiertas: number;
  umbral_mortalidad: number;
  alimento_hoy: FaseAlimento | null;
  tratamientos_indicados: number;
  lectura: {
    temperatura: number;
    humedad: number;
    origen: string;
    fecha_hora: string;
    temp_exterior: number | null;
    humedad_exterior: number | null;
  } | null;
  serie:{ dia: number; esperado: number; peso: number | null; mortalidad: number | null }[];
  registros: {
    id: number;
    fecha: string;
    mortalidad: number;
    alimento_kg: number;
    agua_l: number;
    peso_muestra_g: number;
    // Dictamen del veterinario sobre las bajas del día: NORMAL, VISITA o BROTE.
    revision: string | null;
  }[];
  carencias: {
    id: number;
    medicamento: string;
    libre_faena: string;
    dias_restantes: number;
    estado: string;
  }[];
  vacunas_vencidas: {
    id: number;
    nombre: string;
    fecha_programada: string;
    dias_atraso: number;
    estado: string;
  }[];
};

export type Camara = {
  galpon_id: number;
  galpon: string;
  nombre: string;
  modo: string;
  activa: boolean;
  lote_id: number | null;
  lote: string | null;
  granja: string | null;
  ubicacion: string | null;
  lectura: { temperatura: number; humedad: number; fecha_hora: string } | null;
};

/** Clima de la zona de la granja (Open-Meteo) para comparar con el galpón. */
export type ClimaExterior =
  | { disponible: false; motivo: string }
  | {
      disponible: true;
      ubicacion: string | null;
      latitud: number;
      longitud: number;
      temperatura: number;
      humedad: number;
      viento_kmh: number;
      viento_direccion: number;
      minima: number;
      hora_minima: string;
      maxima: number;
      hora_maxima: string;
    };

export type Tratamiento = {
  id: number;
  lote_id: number;
  medicamento: string;
  dosis: string;
  via: string;
  fecha_inicio: string;
  dias_tratamiento: number;
  dias_carencia: number;
  aves_tratadas: number | null;
  ultima_dosis: string;
  libre_faena: string;
  en_carencia: boolean;
  dias_restantes: number;
  estado: string;
  diagnostico: string;
  /** Lo indicó el veterinario (receta); en estado INDICADO espera que el personal lo inicie. */
  indicado: boolean;
};

export type Vacuna = {
  id: number;
  lote_id: number;
  nombre: string;
  fecha_programada: string;
  estado: string;
  observacion: string;
  fecha_aplicacion: string | null;
  nota_aplicacion: string;
};

const TOKEN = "avismart_token";

export function guardarSesion(token: string) {
  localStorage.setItem(TOKEN, token);
}

export function leerToken() {
  return localStorage.getItem(TOKEN);
}

// Durante el modo soporte se guarda aparte la sesión de plataforma, para volver a ella al salir.
const TOKEN_PLATAFORMA = "avismart_token_plataforma";

export function iniciarSoporte(tokenSoporte: string) {
  const actual = leerToken();
  if (actual && !localStorage.getItem(TOKEN_PLATAFORMA)) localStorage.setItem(TOKEN_PLATAFORMA, actual);
  localStorage.setItem(TOKEN, tokenSoporte);
}

/** Vuelve a la sesión de plataforma. Devuelve false si ya no existe. */
export function terminarSoporte() {
  const plataforma = localStorage.getItem(TOKEN_PLATAFORMA);
  localStorage.removeItem(TOKEN_PLATAFORMA);
  if (!plataforma) {
    localStorage.removeItem(TOKEN);
    return false;
  }
  localStorage.setItem(TOKEN, plataforma);
  return true;
}

export function cerrarSesionLocal() {
  localStorage.removeItem(TOKEN);
  localStorage.removeItem(TOKEN_PLATAFORMA);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (!headers.has("Content-Type") && options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  const token = leerToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  let res: Response;
  try {
    res = await fetch(`/api${path}`, { ...options, headers });
  } catch {
    throw new ApiError(0, "No se pudo conectar con el servidor. Revisa tu conexión e intenta de nuevo.");
  }
  if (res.status === 401 && !path.startsWith("/auth/")) {
    cerrarSesionLocal();
    if (!window.location.pathname.startsWith("/login")) {
      window.location.href = "/login";
    }
  }
  const text = await res.text();
  let data: unknown = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    // Respuesta que no es JSON (por ejemplo, un error del servidor o del proxy).
    data = null;
  }
  if (!res.ok) {
    throw new ApiError(res.status, mensajeDeError(res.status, (data as { detail?: unknown } | null)?.detail));
  }
  return data as T;
}

/** Convierte cualquier respuesta de error en un mensaje claro para la persona. */
function mensajeDeError(status: number, detail: unknown) {
  if (typeof detail === "string" && detail) return detail;
  if (Array.isArray(detail) && detail.length) return "Revisa los datos del formulario: hay un valor fuera de rango o incompleto.";
  if (status === 429) return "Hiciste varios intentos seguidos. Espera unos minutos e intenta de nuevo.";
  if (status >= 500) return "Ocurrió un error inesperado en el servidor. Intenta de nuevo; si continúa, avisa al soporte.";
  return "No se pudo completar la acción.";
}

export async function descargar(path: string, nombre: string) {
  const headers = new Headers();
  const token = leerToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(`/api${path}`, { headers });
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new ApiError(res.status, data?.detail ?? "No se pudo descargar el reporte");
  }
  const url = URL.createObjectURL(await res.blob());
  const enlace = document.createElement("a");
  enlace.href = url;
  enlace.download = nombre;
  document.body.appendChild(enlace);
  enlace.click();
  enlace.remove();
  URL.revokeObjectURL(url);
}

export const ROL: Record<Rol, string> = {
  PLATAFORMA: "Propietario de la plataforma",
  ADMIN: "Administrador",
  PRODUCTOR: "Productor",
  OPERARIO: "Operario",
  VETERINARIO: "Médico veterinario",
};

/** Fecha de hoy (YYYY-MM-DD) en la hora local, no en UTC: evita que de noche el navegador mande "mañana". */
export function hoyLocal() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** Primera pantalla de cada cuenta después de entrar. */
export function inicio(usuario: Usuario) {
  return usuario.rol === "PLATAFORMA" ? "/plataforma/clientes" : "/panel";
}

export function fecha(iso: string) {
  const [y, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}/${y}`;
}

export function num(value: number, digits = 0) {
  return value.toLocaleString("es-PE", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export type FaseAlimento = { nombre: string; dia_desde: number; dia_hasta: number; presentacion: string; producto: string };
export type Alimentacion = {
  dia_vida: number;
  fases: FaseAlimento[];
  fase_actual: string | null;
  cambios: { fecha: string; usuario: string; motivo: string; detalle: string }[];
  catalogo: { fases: (FaseAlimento & { nota: string })[]; nombres: string[]; presentaciones: string[] };
};
