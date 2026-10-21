import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";

/* ---------------------------------------------------------------- Íconos */

const PATHS = {
  panel: "M3 13h8V3H3zM13 21h8V11h-8zM3 21h8v-6H3zM13 3v6h8V3z",
  registro: "M9 3h6l1 2h3v16H5V5h3zM9 3v3h6V3M8 11h8M8 15h5",
  sanidad: "M12 21s-7.5-4.4-7.5-10.3A4.2 4.2 0 0 1 12 8.2a4.2 4.2 0 0 1 7.5 2.5C19.5 16.6 12 21 12 21zM12 10.5v5M9.5 13h5",
  camara: "M3 7h12v10H3zM15 10.5l6-3.5v10l-6-3.5",
  alertas: "M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4",
  lotes: "M4 7h16M4 12h16M4 17h10",
  granjas: "M3 21V10l9-6 9 6v11M9 21v-6h6v6",
  config: "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z",
  clientes: "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM22 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8",
  solicitudes: "M4 4h16v12H5.2L4 17.2zM8 9h8M8 12h5",
  cuentas: "M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 21v-1a6 6 0 0 1 6-6h4a6 6 0 0 1 6 6v1",
  salir: "M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9",
  menu: "M4 6h16M4 12h16M4 18h16",
  cerrar: "M6 6l12 12M18 6L6 18",
  mas: "M12 5v14M5 12h14",
  check: "M5 12.5l4.5 4.5L19 7.5",
  aviso: "M12 9v4M12 17h.01M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z",
  termometro: "M14 14.8V5a2 2 0 0 0-4 0v9.8a4 4 0 1 0 4 0zM12 9v7",
  ave: "M7 18c-2-1-3-3.5-3-6 0-4 3-7 7-7 2.5 0 4 1 5 2.5L20 7l-2 3c.5 3.5-1 7-5 8H7zM14 9.5h.01M9 21l1-3M13 21l-.5-3",
  peso: "M6 8h12l2 12H4zM9 8a3 3 0 1 1 6 0",
  grafico: "M4 19V9M10 19V5M16 19v-7M22 19H2",
  descarga: "M12 4v11M7 10l5 5 5-5M5 20h14",
  ojo: "M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12zM12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z",
  editar: "M4 20h4L19 9l-4-4L4 16zM14 6l4 4",
  llave: "M15 7a4 4 0 1 1-3.9 5H8v3H5v-3H3v-3h8.1A4 4 0 0 1 15 7zM16 11h.01",
  pausa: "M8 5v14M16 5v14",
  alimento: "M5 9h14l-1.5 11h-11zM8 9V6a4 4 0 0 1 8 0v3M9 14h6",
  ubicacion: "M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21zM12 12a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z",
  papelera: "M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6M10 11v6M14 11v6",
  flecha: "M5 12h14M13 6l6 6-6 6",
} as const;

export type IconName = keyof typeof PATHS;

export function Icon({ name, size = 18 }: { name: IconName; size?: number }) {
  return (
    <svg className="icon" width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <path d={PATHS[name]} />
    </svg>
  );
}

/* ---------------------------------------------------------- Encabezado */

export function PageHeader({ titulo, descripcion, acciones, eyebrow }: {
  titulo: string;
  descripcion?: ReactNode;
  acciones?: ReactNode;
  eyebrow?: string;
}) {
  return (
    <header className="page-header">
      <div>
        {eyebrow && <p className="page-eyebrow">{eyebrow}</p>}
        <h1>{titulo}</h1>
        {descripcion && <p className="page-desc">{descripcion}</p>}
      </div>
      {acciones && <div className="page-actions">{acciones}</div>}
    </header>
  );
}

/* --------------------------------------------------------------- Panel */

export function Panel({ titulo, descripcion, acciones, children, className = "", sinPadding = false }: {
  titulo?: ReactNode;
  descripcion?: ReactNode;
  acciones?: ReactNode;
  children: ReactNode;
  className?: string;
  sinPadding?: boolean;
}) {
  return (
    <section className={`panel ${className}`}>
      {(titulo || acciones) && (
        <div className="panel-head">
          <div>
            {titulo && <h2>{titulo}</h2>}
            {descripcion && <p>{descripcion}</p>}
          </div>
          {acciones && <div className="panel-actions">{acciones}</div>}
        </div>
      )}
      <div className={sinPadding ? "panel-body flush" : "panel-body"}>{children}</div>
    </section>
  );
}

/* ---------------------------------------------------------- Pestañas */

export type Pestana = { id: string; label: string; cantidad?: number };

export function Tabs({ items, valor, onCambio }: { items: Pestana[]; valor: string; onCambio: (id: string) => void }) {
  return (
    <div className="tabs" role="tablist">
      {items.map((item) => (
        <button
          key={item.id}
          type="button"
          role="tab"
          aria-selected={valor === item.id}
          className={valor === item.id ? "tab activo" : "tab"}
          onClick={() => onCambio(item.id)}
        >
          {item.label}
          {item.cantidad !== undefined && <span className="tab-count">{item.cantidad}</span>}
        </button>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------- Estado */

const TONOS: Record<string, string> = {
  ACTIVO: "ok", ACTIVA: "ok", VALIDADA: "ok", ATENDIDA: "ok", CONTACTADA: "ok", CLIENTE: "acento", ENVIADA: "ok",
  PENDIENTE: "alerta", INDICADO: "alerta", NUEVA: "alerta", VISTA: "info", OBSERVADA: "riesgo", VENCIDA: "riesgo", SOSPECHOSA: "riesgo", PROGRAMADA: "info", APLICADA: "acento", SUSPENDIDA: "riesgo",
  CERRADO: "neutro", DESCARTADA: "neutro", BAJA: "neutro", INACTIVO: "neutro", FALLIDA: "riesgo",
  SALUD: "riesgo", RECORDATORIO: "alerta", AMBIENTE: "info", CRECIMIENTO: "acento",
};

export function Estado({ valor, texto }: { valor: string; texto?: string }) {
  return <span className={`estado ${TONOS[valor] ?? "neutro"}`}>{texto ?? valor.charAt(0) + valor.slice(1).toLowerCase()}</span>;
}

/* -------------------------------------------------------- Vacío */

export function Vacio({ icono = "registro", titulo, texto, accion }: {
  icono?: IconName;
  titulo: string;
  texto?: ReactNode;
  accion?: ReactNode;
}) {
  return (
    <div className="vacio">
      <span className="vacio-icono"><Icon name={icono} size={22} /></span>
      <strong>{titulo}</strong>
      {texto && <p>{texto}</p>}
      {accion}
    </div>
  );
}

/* ----------------------------------------------------- Formularios */

export function Campo({ label, ayuda, children, ancho = false }: {
  label: string;
  ayuda?: ReactNode;
  children: ReactNode;
  ancho?: boolean;
}) {
  return (
    <label className={ancho ? "campo ancho" : "campo"}>
      <span className="campo-label">{label}</span>
      {children}
      {ayuda && <small className="campo-ayuda">{ayuda}</small>}
    </label>
  );
}

export function Seccion({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <fieldset className="form-seccion">
      <legend>{titulo}</legend>
      <div className="form-grid">{children}</div>
    </fieldset>
  );
}

/* ---------------------------------------------- Panel lateral (drawer) */

export function Drawer({ abierto, titulo, descripcion, onCerrar, children, pie, ancho = "normal" }: {
  abierto: boolean;
  titulo: string;
  descripcion?: ReactNode;
  onCerrar: () => void;
  children: ReactNode;
  pie?: ReactNode;
  ancho?: "normal" | "amplio";
}) {
  useEffect(() => {
    if (!abierto) return;
    const alPulsar = (e: KeyboardEvent) => e.key === "Escape" && onCerrar();
    document.addEventListener("keydown", alPulsar);
    document.body.classList.add("sin-scroll");
    return () => {
      document.removeEventListener("keydown", alPulsar);
      document.body.classList.remove("sin-scroll");
    };
  }, [abierto, onCerrar]);

  if (!abierto) return null;
  return (
    <div className="drawer-capa" onMouseDown={(e) => e.target === e.currentTarget && onCerrar()}>
      <aside className={`drawer ${ancho}`} role="dialog" aria-modal="true" aria-label={titulo}>
        <header className="drawer-head">
          <div>
            <h2>{titulo}</h2>
            {descripcion && <p>{descripcion}</p>}
          </div>
          <button className="icon-btn" type="button" onClick={onCerrar} aria-label="Cerrar">
            <Icon name="cerrar" />
          </button>
        </header>
        <div className="drawer-body">{children}</div>
        {pie && <footer className="drawer-foot">{pie}</footer>}
      </aside>
    </div>
  );
}

/** Formulario dentro de un drawer: el pie con Cancelar / Guardar queda siempre visible. */
export function DrawerForm({ abierto, titulo, descripcion, onCerrar, onGuardar, guardando, textoGuardar = "Guardar", error, children, ancho, peligro = false }: {
  abierto: boolean;
  titulo: string;
  descripcion?: ReactNode;
  onCerrar: () => void;
  onGuardar: () => void;
  guardando?: boolean;
  textoGuardar?: string;
  error?: string;
  children: ReactNode;
  ancho?: "normal" | "amplio";
  peligro?: boolean;
}) {
  const id = `form-${titulo.replace(/\W+/g, "-").toLowerCase()}`;
  return (
    <Drawer
      abierto={abierto}
      titulo={titulo}
      descripcion={descripcion}
      onCerrar={onCerrar}
      ancho={ancho}
      pie={
        <>
          <button className="btn secondary" type="button" onClick={onCerrar}>Cancelar</button>
          <button className={peligro ? "btn danger" : "btn"} type="submit" form={id} disabled={guardando}>
            {guardando ? "Guardando…" : textoGuardar}
          </button>
        </>
      }
    >
      {error && <div className="aviso riesgo">{error}</div>}
      <form
        id={id}
        className="form-drawer"
        onSubmit={(e) => {
          e.preventDefault();
          onGuardar();
        }}
      >
        {children}
      </form>
    </Drawer>
  );
}

/* --------------------------------------------------------- Avisos */

type Toast = { id: number; texto: string; tono: "ok" | "riesgo" };
const ToastContext = createContext<(texto: string, tono?: Toast["tono"]) => void>(() => undefined);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const avisar = useCallback((texto: string, tono: Toast["tono"] = "ok") => {
    const id = Date.now() + Math.random();
    setToasts((lista) => [...lista, { id, texto, tono }]);
    window.setTimeout(() => setToasts((lista) => lista.filter((t) => t.id !== id)), 4500);
  }, []);
  return (
    <ToastContext.Provider value={avisar}>
      {children}
      <div className="toasts" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={`toast ${t.tono}`}>
            <Icon name={t.tono === "ok" ? "check" : "aviso"} />
            <span>{t.texto}</span>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  return useContext(ToastContext);
}

export function mensajeError(err: unknown, porDefecto = "No se pudo completar la acción") {
  return err instanceof Error ? err.message : porDefecto;
}

/* ---------------------------------------------------------- Ayuda */

/** Ícono "?" que explica un término en lenguaje sencillo. Funciona con mouse, teclado y toque. */
export function Ayuda({ titulo, children }: { titulo: string; children: ReactNode }) {
  const [abierta, setAbierta] = useState(false);
  const [pos, setPos] = useState({ left: 0, top: 0, ancho: 280 });
  const ref = useRef<HTMLSpanElement>(null);

  function mostrar() {
    const caja = ref.current?.getBoundingClientRect();
    if (caja) {
      // Se fija a la ventana y se recorta a sus bordes para que nunca quede fuera de la pantalla.
      const ancho = Math.min(280, window.innerWidth - 16);
      const left = Math.min(Math.max(caja.left - 12, 8), window.innerWidth - ancho - 8);
      setPos({ left, top: caja.bottom + 8, ancho });
    }
    setAbierta(true);
  }

  useEffect(() => {
    if (!abierta) return;
    const fuera = (e: Event) => ref.current && !ref.current.contains(e.target as Node) && setAbierta(false);
    const cerrar = () => setAbierta(false);
    document.addEventListener("pointerdown", fuera);
    window.addEventListener("scroll", cerrar, true);
    return () => {
      document.removeEventListener("pointerdown", fuera);
      window.removeEventListener("scroll", cerrar, true);
    };
  }, [abierta]);

  return (
    <span className="ayuda" ref={ref} onMouseEnter={mostrar} onMouseLeave={() => setAbierta(false)}>
      <button
        type="button"
        className="ayuda-btn"
        aria-label={`¿Qué es ${titulo}?`}
        aria-expanded={abierta}
        onClick={() => (abierta ? setAbierta(false) : mostrar())}
        onFocus={mostrar}
        onBlur={() => setAbierta(false)}
      >
        ?
      </button>
      {abierta && (
        <span className="ayuda-pop" role="tooltip" style={{ left: pos.left, top: pos.top, width: pos.ancho }}>
          <strong>{titulo}</strong>
          {children}
        </span>
      )}
    </span>
  );
}

/* -------------------------------------------------------- Iniciales */

export function Avatar({ nombre }: { nombre: string }) {
  const iniciales = nombre
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join("");
  return <span className="avatar" aria-hidden="true">{iniciales || "?"}</span>;
}
