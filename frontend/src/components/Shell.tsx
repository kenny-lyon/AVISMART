import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { api, type Alerta } from "../api";
import { useAuth } from "../auth";
import { useLote } from "../lote";
import Layout, { type NavGrupo } from "./Layout";
import { Icon, Panel, Vacio } from "./ui";

/** Pantallas que necesitan un lote elegido para mostrar algo. */
const NECESITAN_LOTE = ["/panel", "/registro", "/sanidad", "/bajas", "/alimentacion", "/camara"];

function SinLotes({ puedeConfigurar }: { puedeConfigurar: boolean }) {
  return (
    <Panel>
      <Vacio
        icono="lotes"
        titulo="Todavía no hay lotes"
        texto={
          puedeConfigurar ? (
            <ol className="pasos">
              <li><b>1</b> Registra tu granja avícola y sus galpones.</li>
              <li><b>2</b> Abre el primer lote en uno de los galpones.</li>
            </ol>
          ) : (
            "Cuando el productor abra un lote, aparecerá aquí."
          )
        }
        accion={
          puedeConfigurar && (
            <div className="page-actions">
              <Link className="btn" to="/instalaciones">Granjas y galpones</Link>
              <Link className="btn secondary" to="/lotes">Abrir lote</Link>
            </div>
          )
        }
      />
    </Panel>
  );
}

/** Franja visible mientras la plataforma trabaja dentro de un cliente. */
function FranjaSoporte({ cliente }: { cliente: { id: number; nombre: string } }) {
  const { salirSoporte } = useAuth();
  const navigate = useNavigate();
  return (
    <div className="aviso alerta franja-soporte">
      <Icon name="cuentas" />
      <span>
        <b>Modo soporte</b> en <b>{cliente.nombre}</b>. Trabajas con los permisos de su productor y lo que hagas queda registrado a tu nombre.
      </span>
      <button className="btn" type="button" onClick={() => salirSoporte().then(() => navigate(`/plataforma/clientes/${cliente.id}`, { replace: true }))}>
        Salir del modo soporte
      </button>
    </div>
  );
}

/** El recordatorio de datos de contacto se puede cerrar: vuelve a aparecer después de 24 horas. */
const HORAS_RECORDATORIO = 24;
const claveRecordatorio = (id: number) => `avismart_recordatorio_contacto_${id}`;

function recordatorioPospuesto(id: number) {
  try {
    const hasta = Number(localStorage.getItem(claveRecordatorio(id)) ?? 0);
    return Date.now() < hasta;
  } catch {
    return false;
  }
}

function posponerRecordatorio(id: number) {
  try {
    localStorage.setItem(claveRecordatorio(id), String(Date.now() + HORAS_RECORDATORIO * 3600 * 1000));
  } catch {
    /* sin almacenamiento local: se vuelve a mostrar en la próxima carga */
  }
}

export default function Shell({ children }: { children: React.ReactNode }) {
  const { usuario } = useAuth();
  const { resumen, loteId, elegir } = useLote();
  const { pathname } = useLocation();
  const [abiertas, setAbiertas] = useState(0);
  const [, setPospuesto] = useState(0);

  useEffect(() => {
    const contar = () =>
      api<Alerta[]>("/alertas")
        .then((lista) => setAbiertas(lista.filter((a) => a.estado !== "ATENDIDA").length))
        .catch(() => setAbiertas(0));
    contar();
    window.addEventListener("avismart:cambios", contar);
    return () => window.removeEventListener("avismart:cambios", contar);
  }, [pathname]);

  if (!usuario) return null;
  const rol = usuario.rol;
  const puede = (...roles: string[]) => roles.includes(rol);
  const variasGranjas = (resumen?.granjas.length ?? 0) > 1;
  const sinLotes = resumen !== null && resumen.lotes.length === 0 && NECESITAN_LOTE.includes(pathname);
  const lote = resumen?.lotes.find((l) => l.id === loteId);

  const grupos: NavGrupo[] = [
    {
      titulo: "Seguimiento",
      items: [
        { to: "/panel", label: "Panel del lote", icono: "panel" as const },
        ...(puede("PRODUCTOR", "OPERARIO") ? [{ to: "/registro", label: "Registro del día", icono: "registro" as const }] : []),
        { to: "/alertas", label: "Alertas", icono: "alertas" as const, contador: abiertas, urgente: true },
        { to: "/camara", label: "Cámara", icono: "camara" as const },
      ],
    },
    {
      titulo: "Sanidad y alimento",
      items: [
        { to: "/sanidad", label: "Vacunas y tratamientos", icono: "sanidad" },
        { to: "/bajas", label: "Revisión de bajas", icono: "ave" },
        { to: "/alimentacion", label: "Alimentación", icono: "alimento" },
      ],
    },
  ];
  if (puede("ADMIN", "PRODUCTOR")) {
    grupos.push({
      titulo: "Gestión",
      items: [
        { to: "/lotes", label: "Lotes", icono: "lotes" },
        { to: "/instalaciones", label: "Granjas y galpones", icono: "granjas" },
      ],
    });
  }
  grupos.push({
    titulo: "Ajustes",
    items: [{ to: "/config", label: puede("VETERINARIO") ? "Parámetros y cuenta" : puede("OPERARIO") ? "Mi cuenta" : "Personal y ajustes", icono: "config" }],
  });
  // El productor es la cuenta principal del cliente: se le pide completar su contacto de respaldo.
  const faltaContacto =
    rol === "PRODUCTOR" && !usuario.soporte && (!usuario.telefono || !usuario.correo_alterno) && pathname !== "/config" && !recordatorioPospuesto(usuario.id);

  return (
    <Layout
      subtitulo={resumen?.organizacion.nombre ?? "Engorde"}
      grupos={grupos}
      contexto={
        <>
          <small>{resumen?.organizacion.nombre}</small>
          <strong>{lote ? lote.granja : variasGranjas ? `${resumen?.granjas.length} granjas avícolas` : resumen?.granja?.nombre ?? "Sin granja avícola"}</strong>
        </>
      }
      derecha={
        <>
          {resumen && resumen.lotes.length > 0 && (
            <label className="selector-lote">
              <span>Lote</span>
              <select value={loteId ?? ""} onChange={(e) => elegir(Number(e.target.value))}>
                {resumen.lotes.map((l) => (
                  <option key={l.id} value={l.id}>
                    {variasGranjas ? `${l.granja} · ` : ""}{l.galpon} · {l.linea} · día {l.dia_vida}{l.estado === "CERRADO" ? " (cerrado)" : ""}
                  </option>
                ))}
              </select>
            </label>
          )}
          <Link className="icon-btn campana" to="/alertas" aria-label={`Alertas abiertas: ${abiertas}`} title="Alertas">
            <Icon name="alertas" />
            {abiertas > 0 && <span className="campana-num">{abiertas}</span>}
          </Link>
        </>
      }
    >
      {usuario.soporte && usuario.organizacion && <FranjaSoporte cliente={usuario.organizacion} />}
      {faltaContacto && (
        <div className="aviso info aviso-cerrable">
          <Icon name="cuentas" />
          <span>
            Completa tu <b>celular con WhatsApp</b> y un <b>correo de respaldo</b>. Los usamos solo para verificar que eres tú si alguna vez pierdes el acceso.{" "}
            <Link to="/config?pestana=cuenta">Completar ahora</Link>
          </span>
          <button
            type="button"
            className="aviso-cerrar"
            aria-label="Recordármelo más tarde"
            title="Recordármelo más tarde"
            onClick={() => { posponerRecordatorio(usuario.id); setPospuesto((n) => n + 1); }}
          >
            ×
          </button>
        </div>
      )}
      {sinLotes ? <SinLotes puedeConfigurar={puede("ADMIN", "PRODUCTOR")} /> : children}
    </Layout>
  );
}
