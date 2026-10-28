import { useEffect, useState } from "react";
import { api, type Alimentacion as DatosAlimentacion, type FaseAlimento } from "../api";
import { useAuth } from "../auth";
import { Campo, DrawerForm, Estado, Icon, PageHeader, Panel, Seccion, Vacio, mensajeError, useToast } from "../components/ui";
import { useLote } from "../lote";
import { valorCampo } from "../textos";

type Fila = { nombre: string; dia_hasta: string; presentacion: string; producto: string };

/** Fecha y hora legible del historial. */
function cuando(iso: string) {
  return new Date(iso).toLocaleString("es-PE", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

export default function Alimentacion() {
  const { usuario } = useAuth();
  const { loteId, resumen } = useLote();
  const avisar = useToast();
  const [datos, setDatos] = useState<DatosAlimentacion | null>(null);
  const [error, setError] = useState("");
  const [editando, setEditando] = useState(false);
  const [filas, setFilas] = useState<Fila[]>([]);
  const [motivo, setMotivo] = useState("");
  const [guardando, setGuardando] = useState(false);
  const [errorPlan, setErrorPlan] = useState("");

  const lote = resumen?.lotes.find((l) => l.id === loteId);
  const puedeVariar = usuario?.rol === "VETERINARIO" && lote?.estado === "ACTIVO";

  async function cargar() {
    if (!loteId) return;
    setDatos(await api<DatosAlimentacion>(`/lotes/${loteId}/alimentacion`));
  }

  useEffect(() => {
    cargar().catch((err) => setError(mensajeError(err)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loteId]);

  // El «desde» de cada fase es el día siguiente al «hasta» de la anterior: así nunca quedan huecos.
  const desde = (i: number) => (i === 0 ? 0 : Number(filas[i - 1].dia_hasta || 0) + 1);

  function abrir() {
    if (!datos) return;
    setFilas(datos.fases.map((f) => ({ nombre: f.nombre, dia_hasta: String(f.dia_hasta), presentacion: f.presentacion, producto: f.producto })));
    setMotivo("");
    setErrorPlan("");
    setEditando(true);
  }

  const cambiarFila = (i: number, cambio: Partial<Fila>) => setFilas(filas.map((f, j) => (j === i ? { ...f, ...cambio } : f)));

  async function guardar() {
    if (!loteId) return;
    setErrorPlan("");
    setGuardando(true);
    try {
      const fases: FaseAlimento[] = filas.map((f, i) => ({
        nombre: f.nombre,
        dia_desde: desde(i),
        dia_hasta: Number(f.dia_hasta),
        presentacion: f.presentacion,
        producto: f.producto,
      }));
      setDatos(await api<DatosAlimentacion>(`/lotes/${loteId}/alimentacion`, { method: "PUT", body: JSON.stringify({ fases, motivo }) }));
      setEditando(false);
      avisar("Plan de alimentación actualizado. El cambio quedó en el historial.");
    } catch (err) {
      setErrorPlan(mensajeError(err, "No se guardó el plan"));
    } finally {
      setGuardando(false);
    }
  }

  if (!datos) return <p className="muted">{error || "Cargando el plan de alimentación…"}</p>;
  const actual = datos.fases.find((f) => f.nombre === datos.fase_actual);
  const nota = (nombre: string) => datos.catalogo.fases.find((f) => f.nombre === nombre)?.nota;

  return (
    <>
      <PageHeader
        titulo="Alimentación"
        descripcion="Plan de alimento por fases del lote. Lo define el médico veterinario; el registro del día anota el alimento que se dio."
        acciones={
          puedeVariar && (
            <button className="btn primario" type="button" onClick={abrir}>
              <Icon name="editar" /> Variar plan
            </button>
          )
        }
      />

      {actual && (
        <div className="aviso info">
          <Icon name="alimento" />
          <span>
            Hoy (día {datos.dia_vida}) corresponde <b>{actual.nombre}</b>
            {actual.presentacion ? ` en ${actual.presentacion.toLowerCase()}` : ""}
            {actual.producto ? ` · ${actual.producto}` : ""}. {nota(actual.nombre)}
          </span>
        </div>
      )}

      <Panel titulo="Plan del lote" descripcion="Cada fase cubre un rango de días de vida." sinPadding>
        <div className="tabla-wrap">
          <table>
            <thead>
              <tr><th>Fase</th><th>Días</th><th>Presentación</th><th>Producto</th><th /></tr>
            </thead>
            <tbody>
              {datos.fases.map((f) => (
                <tr key={f.nombre + f.dia_desde} className={f.nombre === datos.fase_actual ? "fila-actual" : undefined}>
                  <td className="celda-principal"><strong>{f.nombre}</strong><small>{nota(f.nombre) ?? "Sin medicamentos en el alimento antes de la faena."}</small></td>
                  <td>{f.dia_desde} – {f.dia_hasta}</td>
                  <td>{f.presentacion || <span className="muted">—</span>}</td>
                  <td>{f.producto || <span className="muted">—</span>}</td>
                  <td>{f.nombre === datos.fase_actual && <Estado valor="ACTIVO" texto="Actual" />}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel titulo="Variaciones del plan" descripcion="Cada cambio del veterinario queda registrado con su motivo." sinPadding>
        {datos.cambios.length === 0 ? (
          <Vacio icono="alimento" titulo="Sin variaciones" texto="El lote sigue el plan base de alimentación." />
        ) : (
          <ul className="historial">
            {datos.cambios.map((c) => (
              <li key={c.fecha + c.motivo}>
                <strong>{c.motivo}</strong>
                <small>{cuando(c.fecha)} · {c.usuario}</small>
                <span className="muted">{c.detalle}</span>
              </li>
            ))}
          </ul>
        )}
      </Panel>

      <DrawerForm
        abierto={editando}
        titulo="Variar plan de alimentación"
        descripcion="Ajusta las fases o el producto. Cada fase empieza el día siguiente a la anterior."
        onCerrar={() => setEditando(false)}
        onGuardar={guardar}
        guardando={guardando}
        textoGuardar="Guardar variación"
        error={errorPlan}
        ancho="amplio"
      >
        {filas.map((f, i) => (
          <Seccion key={i} titulo={`Fase ${i + 1} · desde el día ${desde(i)}`}>
            <Campo label="Fase">
              <select value={f.nombre} onChange={(e) => cambiarFila(i, { nombre: e.target.value })}>
                {datos.catalogo.nombres.map((n) => <option key={n}>{n}</option>)}
              </select>
            </Campo>
            <Campo label="Hasta el día">
              <input type="number" min={desde(i)} max={70} value={f.dia_hasta} onChange={(e) => cambiarFila(i, { dia_hasta: valorCampo(e) })} required />
            </Campo>
            <Campo label="Presentación">
              <select value={f.presentacion} onChange={(e) => cambiarFila(i, { presentacion: e.target.value })}>
                <option value="">—</option>
                {datos.catalogo.presentaciones.map((p) => <option key={p}>{p}</option>)}
              </select>
            </Campo>
            <Campo label="Producto o marca (opcional)">
              <input value={f.producto} maxLength={120} onChange={(e) => cambiarFila(i, { producto: e.target.value })} placeholder="Ej. Inicio medicado" />
            </Campo>
          </Seccion>
        ))}
        <div className="actions" style={{ marginBottom: 16 }}>
          {filas.length < 6 && (
            <button className="btn small secondary" type="button" onClick={() => setFilas([...filas, { nombre: "Retiro", dia_hasta: String(Math.min(desde(filas.length) + 4, 70)), presentacion: "Pellet", producto: "" }])}>
              <Icon name="mas" size={15} /> Agregar fase
            </button>
          )}
          {filas.length > 1 && (
            <button className="btn small secondary" type="button" onClick={() => setFilas(filas.slice(0, -1))}>Quitar la última</button>
          )}
        </div>
        <Campo label="Motivo de la variación" ancho ayuda="Queda en el historial con tu nombre.">
          <textarea rows={3} minLength={5} maxLength={500} required value={motivo} onChange={(e) => setMotivo(e.target.value)}
            placeholder="Ej. Se prolonga el Inicio por el brote respiratorio" />
        </Campo>
      </DrawerForm>
    </>
  );
}
