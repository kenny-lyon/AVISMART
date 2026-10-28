import { useEffect, useState } from "react";
import { api, type Usuario } from "../api";
import { useAuth } from "../auth";
import { Campo, Panel, Vacio, mensajeError, useToast } from "./ui";

export type Acceso = { fecha: string; evento: string; ip: string | null; navegador: string; usuario?: string };

export function cuandoAcceso(iso: string) {
  return new Date(iso).toLocaleString("es-PE", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

/** Tabla de ingresos y cambios de clave. */
export function TablaAccesos({ accesos, conPersona = false }: { accesos: Acceso[]; conPersona?: boolean }) {
  if (accesos.length === 0) return <Vacio icono="cuentas" titulo="Sin accesos registrados" texto="Aquí aparecerán los inicios de sesión y los cambios de clave." />;
  return (
    <div className="tabla-wrap">
      <table>
        <thead>
          <tr>{conPersona && <th>Persona</th>}<th>Fecha</th><th>Evento</th><th>Navegador</th><th>Conexión (IP)</th></tr>
        </thead>
        <tbody>
          {accesos.map((a, i) => (
            <tr key={a.fecha + i}>
              {conPersona && <td>{a.usuario}</td>}
              <td>{cuandoAcceso(a.fecha)}</td>
              <td>{a.evento}</td>
              <td>{a.navegador || "—"}</td>
              <td className="mono">{a.ip ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Datos de contacto de la propia cuenta y sus últimos accesos. */
export default function MiCuenta() {
  const { usuario, actualizarUsuario } = useAuth();
  const avisar = useToast();
  const [telefono, setTelefono] = useState(usuario?.telefono ?? "");
  const [respaldo, setRespaldo] = useState(usuario?.correo_alterno ?? "");
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState("");
  const [accesos, setAccesos] = useState<Acceso[]>([]);

  useEffect(() => {
    api<Acceso[]>("/me/accesos").then(setAccesos).catch(() => undefined);
  }, []);

  async function guardar(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setGuardando(true);
    try {
      const actualizado = await api<Usuario>("/me/contacto", { method: "PUT", body: JSON.stringify({ telefono, correo_alterno: respaldo }) });
      actualizarUsuario(actualizado);
      setTelefono(actualizado.telefono ?? "");
      setRespaldo(actualizado.correo_alterno ?? "");
      avisar("Datos de contacto guardados.");
    } catch (err) {
      setError(mensajeError(err, "No se guardaron los datos"));
    } finally {
      setGuardando(false);
    }
  }

  return (
    <>
      <Panel
        titulo="Datos de contacto"
        descripcion={`Entras con ${usuario?.email}. Estos datos los usa AviSmart solo para verificar que eres tú si alguna vez pierdes el acceso a tu cuenta.`}
      >
        <form onSubmit={guardar} className="form-grid" style={{ maxWidth: 640 }}>
          {error && <div className="aviso riesgo campo ancho">{error}</div>}
          <Campo label="Celular con WhatsApp" ayuda="9 dígitos, empieza con 9.">
            <input type="tel" inputMode="tel" maxLength={20} value={telefono} onChange={(e) => setTelefono(e.target.value)} placeholder="987 654 321" />
          </Campo>
          <Campo label="Correo de respaldo" ayuda="Distinto al correo con el que entras.">
            <input type="email" maxLength={160} value={respaldo} onChange={(e) => setRespaldo(e.target.value)} placeholder="nombre@gmail.com" />
          </Campo>
          <div className="campo ancho">
            <button className="btn" type="submit" disabled={guardando} style={{ justifySelf: "start" }}>{guardando ? "Guardando…" : "Guardar datos"}</button>
          </div>
        </form>
      </Panel>
      <Panel titulo="Últimos accesos" descripcion="Si ves un ingreso que no reconoces, cambia tu clave y avísanos desde Contacto o por WhatsApp al 931 113 015." sinPadding>
        <TablaAccesos accesos={accesos} />
      </Panel>
    </>
  );
}
