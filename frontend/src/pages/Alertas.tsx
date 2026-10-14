import { useEffect, useState } from "react";
import { api, avisarCambios, fecha, type Alerta } from "../api";
import { useAuth } from "../auth";
import { Campo, Drawer, Estado, PageHeader, Panel, Tabs, Vacio, mensajeError, useToast } from "../components/ui";

const TIPOS: Record<string, string> = { SALUD: "Salud", RECORDATORIO: "Vacuna", AMBIENTE: "Ambiente", CRECIMIENTO: "Crecimiento" };

export default function Alertas() {
  const { usuario } = useAuth();
  const avisar = useToast();
  const [alertas, setAlertas] = useState<Alerta[]>([]);
  const [vista, setVista] = useState("ABIERTAS");
  const [tipo, setTipo] = useState("TODOS");
  const [detalle, setDetalle] = useState<Alerta | null>(null);
  const [nota, setNota] = useState("");
  const [error, setError] = useState("");
  const [guardando, setGuardando] = useState(false);

  async function cargar() {
    setAlertas(await api<Alerta[]>("/alertas"));
  }

  useEffect(() => {
    cargar().catch((err) => avisar(mensajeError(err), "riesgo"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function puede(alerta: Alerta) {
    if (alerta.estado === "ATENDIDA") return false;
    if (alerta.requiere_veterinario) return usuario?.rol === "VETERINARIO";
    return usuario?.rol === "PRODUCTOR" || usuario?.rol === "ADMIN";
  }

  async function atender() {
    if (!detalle) return;
    setError("");
    setGuardando(true);
    try {
      await api(`/alertas/${detalle.id}/atender`, { method: "POST", body: JSON.stringify({ decision: "ATENDIDA", observacion: nota }) });
      setDetalle(null);
      avisarCambios();
      avisar("Alerta atendida.");
      await cargar();
    } catch (err) {
      setError(mensajeError(err, "No se pudo atender"));
    } finally {
      setGuardando(false);
    }
  }

  const abiertas = alertas.filter((a) => a.estado !== "ATENDIDA");
  const porVista = vista === "ABIERTAS" ? abiertas : vista === "ATENDIDAS" ? alertas.filter((a) => a.estado === "ATENDIDA") : alertas;
  const visibles = tipo === "TODOS" ? porVista : porVista.filter((a) => a.tipo === tipo);
  const mias = abiertas.filter(puede).length;

  return (
    <>
      <PageHeader
        titulo="Alertas"
        descripcion="Salud y recordatorios de vacuna los cierra el veterinario. Ambiente y crecimiento, el productor."
      />
      {mias > 0 && <div className="aviso info">Tienes {mias} alerta(s) abiertas que te corresponde atender.</div>}

      <Panel sinPadding>
        <div className="barra-lista">
          <Tabs
            valor={vista}
            onCambio={setVista}
            items={[
              { id: "ABIERTAS", label: "Abiertas", cantidad: abiertas.length },
              { id: "ATENDIDAS", label: "Atendidas", cantidad: alertas.length - abiertas.length },
              { id: "TODAS", label: "Todas", cantidad: alertas.length },
            ]}
          />
          <select value={tipo} onChange={(e) => setTipo(e.target.value)} style={{ width: "auto" }} aria-label="Filtrar por tipo">
            <option value="TODOS">Todos los tipos</option>
            {Object.entries(TIPOS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </div>
        {visibles.length === 0 ? (
          <Vacio icono="alertas" titulo={vista === "ABIERTAS" ? "No hay alertas abiertas" : "No hay alertas en esta vista"} texto={vista === "ABIERTAS" ? "El lote está dentro de los rangos configurados." : undefined} />
        ) : (
          <div className="tabla-wrap">
            <table>
              <thead>
                <tr><th>Tipo</th><th>Detalle</th><th>Fecha</th><th>Atiende</th><th>Estado</th><th /></tr>
              </thead>
              <tbody>
                {visibles.map((a) => (
                  <tr key={a.id} className={`clicable ${a.estado === "ATENDIDA" ? "" : a.tipo === "SALUD" ? "fila-riesgo" : a.tipo === "RECORDATORIO" ? "fila-alerta" : "fila-info"}`} onClick={() => { setError(""); setNota(""); setDetalle(a); }}>
                    <td><Estado valor={a.tipo} texto={TIPOS[a.tipo] ?? a.tipo} /></td>
                    <td className="celda-principal">
                      <strong>{a.mensaje}</strong>
                      <small>{a.lote}</small>
                    </td>
                    <td>{fecha(a.creada_en)}</td>
                    <td>{a.requiere_veterinario ? "Veterinario" : "Productor"}</td>
                    <td><Estado valor={a.estado} /></td>
                    <td className="acciones">
                      <button className="link-button" type="button">{puede(a) ? "Atender" : "Ver"}</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <Drawer
        abierto={detalle !== null}
        titulo={detalle ? `Alerta de ${(TIPOS[detalle.tipo] ?? detalle.tipo).toLowerCase()}` : ""}
        descripcion={detalle?.lote}
        onCerrar={() => setDetalle(null)}
        pie={
          detalle && puede(detalle) ? (
            <>
              <button className="btn secondary" type="button" onClick={() => setDetalle(null)}>Cancelar</button>
              <button className="btn" type="button" disabled={guardando} onClick={atender}>{guardando ? "Guardando…" : "Marcar atendida"}</button>
            </>
          ) : (
            <button className="btn secondary" type="button" onClick={() => setDetalle(null)}>Cerrar</button>
          )
        }
      >
        {detalle && (
          <>
            {error && <div className="aviso riesgo">{error}</div>}
            <p className="cita">{detalle.mensaje}</p>
            <dl className="ficha" style={{ marginTop: 18 }}>
              <dt>Estado</dt><dd><Estado valor={detalle.estado} /></dd>
              <dt>Creada</dt><dd>{fecha(detalle.creada_en)} {detalle.creada_en.slice(11, 16)}</dd>
              <dt>La atiende</dt><dd>{detalle.requiere_veterinario ? "Médico veterinario" : "Productor o administrador"}</dd>
              <dt>Telegram</dt><dd>{detalle.notificacion_estado.toLowerCase().replace("_", " ")}</dd>
              {detalle.observacion && (<><dt>Qué se hizo</dt><dd>{detalle.observacion}</dd></>)}
            </dl>
            {puede(detalle) && (
              <Campo label="Qué se hizo" ayuda="Queda registrado junto a la alerta.">
                <textarea rows={4} value={nota} onChange={(e) => setNota(e.target.value)} placeholder="Ej. Revisión de campo, se ajustó la ventilación" />
              </Campo>
            )}
            {!puede(detalle) && detalle.estado !== "ATENDIDA" && (
              <p className="muted">Esta alerta la atiende {detalle.requiere_veterinario ? "el médico veterinario" : "el productor o el administrador"}.</p>
            )}
          </>
        )}
      </Drawer>
    </>
  );
}
