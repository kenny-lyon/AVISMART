import { useEffect, useState } from "react";
import { api, ROL, type Rol, type Usuario } from "../api";
import { useAuth } from "../auth";
import { Avatar, Campo, Drawer, DrawerForm, Estado, Icon, Panel, Seccion, mensajeError, useToast } from "./ui";

export type Credencial = { email: string; clave: string };

/** Muestra una clave temporal una sola vez, con opción de copiarla. */
export function CredencialTemporal({ credencial }: { credencial: Credencial }) {
  const avisar = useToast();
  async function copiar() {
    try {
      await navigator.clipboard.writeText(`Usuario: ${credencial.email}\nClave temporal: ${credencial.clave}`);
      avisar("Credencial copiada. Entrégala por un canal privado.");
    } catch {
      avisar("No se pudo copiar; selecciona el texto manualmente.", "riesgo");
    }
  }
  return (
    <div className="temporary-credential">
      <div>
        <strong>Se muestra solo esta vez</strong>
        <p>Usuario: <code>{credencial.email}</code></p>
        <p>Clave temporal: <code>{credencial.clave}</code></p>
        <small>La persona deberá reemplazarla al entrar por primera vez.</small>
      </div>
      <button className="btn secondary" type="button" onClick={copiar}>Copiar</button>
    </div>
  );
}

/** Drawer que entrega una credencial recién generada. */
export function DrawerCredencial({ credencial, titulo, onCerrar }: { credencial: Credencial | null; titulo: string; onCerrar: () => void }) {
  return (
    <Drawer
      abierto={credencial !== null}
      titulo={titulo}
      descripcion="Entrega estos datos por un canal privado, idealmente el correo y la clave por medios distintos."
      onCerrar={onCerrar}
      pie={<button className="btn" type="button" onClick={onCerrar}>Listo</button>}
    >
      {credencial && <CredencialTemporal credencial={credencial} />}
    </Drawer>
  );
}

function estadoCuenta(u: Usuario) {
  if (!u.activo) return <Estado valor="INACTIVO" texto="Inactiva" />;
  if (u.debe_cambiar_clave) return <Estado valor="PENDIENTE" texto="Clave temporal" />;
  return <Estado valor="ACTIVO" texto="Activa" />;
}

/** Alta, restablecimiento y baja de cuentas del ámbito de quien está conectado. */
export default function Cuentas({ roles, gestiona = roles, base = "/usuarios", titulo, descripcion, onCambio }: {
  roles: Rol[];
  gestiona?: Rol[];
  base?: string;
  titulo: string;
  descripcion: string;
  onCambio?: () => void;
}) {
  const { usuario: actual } = useAuth();
  const avisar = useToast();
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [nueva, setNueva] = useState(false);
  const [nombre, setNombre] = useState("");
  const [email, setEmail] = useState("");
  const [rol, setRol] = useState<Rol>(roles.includes("OPERARIO") ? "OPERARIO" : roles[0]);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState("");
  const [credencial, setCredencial] = useState<{ titulo: string; datos: Credencial } | null>(null);

  async function cargar() {
    setUsuarios(await api<Usuario[]>(base));
  }

  async function recargar() {
    await cargar();
    onCambio?.();
  }

  useEffect(() => {
    cargar().catch((err) => avisar(mensajeError(err), "riesgo"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [base]);

  async function crear() {
    setError("");
    setGuardando(true);
    try {
      const data = await api<{ usuario: Usuario; clave_temporal: string }>(base, {
        method: "POST",
        body: JSON.stringify({ nombre, email, rol }),
      });
      setNueva(false);
      setNombre("");
      setEmail("");
      setCredencial({ titulo: `Cuenta creada para ${data.usuario.nombre}`, datos: { email: data.usuario.email, clave: data.clave_temporal } });
      await recargar();
    } catch (err) {
      setError(mensajeError(err, "No se pudo crear la cuenta"));
    } finally {
      setGuardando(false);
    }
  }

  async function restablecer(usuario: Usuario) {
    if (!window.confirm(`Se invalidará la clave actual de ${usuario.nombre}. ¿Continuar?`)) return;
    try {
      const data = await api<{ usuario: Usuario; clave_temporal: string }>(`${base}/${usuario.id}/restablecer-clave`, { method: "POST" });
      setCredencial({ titulo: `Nueva clave para ${usuario.nombre}`, datos: { email: data.usuario.email, clave: data.clave_temporal } });
      await recargar();
    } catch (err) {
      avisar(mensajeError(err, "No se pudo restablecer la clave"), "riesgo");
    }
  }

  async function cambiarEstado(usuario: Usuario) {
    if (usuario.activo && !window.confirm(`${usuario.nombre} ya no podrá entrar. ¿Desactivar la cuenta?`)) return;
    try {
      await api(`${base}/${usuario.id}/estado`, { method: "PATCH", body: JSON.stringify({ activo: !usuario.activo }) });
      await recargar();
      avisar(`Cuenta ${usuario.activo ? "desactivada" : "activada"}.`);
    } catch (err) {
      avisar(mensajeError(err, "No se pudo cambiar el estado"), "riesgo");
    }
  }

  return (
    <>
      <Panel
        titulo={titulo}
        descripcion={descripcion}
        sinPadding
        acciones={
          <button className="btn small" type="button" onClick={() => { setError(""); setNueva(true); }}>
            <Icon name="mas" size={15} /> Nueva cuenta
          </button>
        }
      >
        <div className="tabla-wrap">
          <table>
            <thead>
              <tr><th>Persona</th><th>Rol</th><th>Estado</th><th /></tr>
            </thead>
            <tbody>
              {usuarios.map((u) => (
                <tr key={u.id}>
                  <td>
                    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                      <Avatar nombre={u.nombre} />
                      <div className="celda-principal">
                        <strong>{u.nombre}{u.id === actual?.id ? " (tú)" : ""}</strong>
                        <small>{u.email}</small>
                      </div>
                    </div>
                  </td>
                  <td>{ROL[u.rol]}</td>
                  <td>{estadoCuenta(u)}</td>
                  <td className="acciones">
                    {gestiona.includes(u.rol) && (
                      <button className="link-button" type="button" onClick={() => restablecer(u)}>Restablecer clave</button>
                    )}
                    {u.id !== actual?.id && gestiona.includes(u.rol) && (
                      <button className={u.activo ? "link-button riesgo" : "link-button"} type="button" onClick={() => cambiarEstado(u)}>
                        {u.activo ? "Desactivar" : "Activar"}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <DrawerForm
        abierto={nueva}
        titulo="Nueva cuenta"
        descripcion="Se generará una clave temporal que la persona cambiará al entrar."
        onCerrar={() => setNueva(false)}
        onGuardar={crear}
        guardando={guardando}
        textoGuardar="Crear cuenta"
        error={error}
      >
        <Seccion titulo="Persona">
          <Campo label="Nombre completo" ancho>
            <input value={nombre} onChange={(e) => setNombre(e.target.value)} required minLength={3} />
          </Campo>
          <Campo label="Correo" ancho>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </Campo>
          {roles.length > 1 && (
            <Campo label="Rol" ancho>
              <select value={rol} onChange={(e) => setRol(e.target.value as Rol)}>
                {roles.map((item) => <option value={item} key={item}>{ROL[item]}</option>)}
              </select>
            </Campo>
          )}
        </Seccion>
      </DrawerForm>

      <DrawerCredencial credencial={credencial?.datos ?? null} titulo={credencial?.titulo ?? ""} onCerrar={() => setCredencial(null)} />
    </>
  );
}
