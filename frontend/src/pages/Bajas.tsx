import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, fecha, hoyLocal, num } from "../api";
import { useAuth } from "../auth";
import { Campo, DrawerForm, PageHeader, Panel, Seccion, Tabs, Vacio, mensajeError, useToast } from "../components/ui";
import { ListaEvidencia, ZonaEvidencia, type Adjunto } from "../components/Evidencias";
import { useLote } from "../lote";

type Revision = {
  dictamen: "NORMAL" | "VISITA" | "BROTE";
  dictamen_nombre: string;
  causa: string;
  observaciones: string;
  fecha_visita: string | null;
  veterinario: string | null;
  creada_en: string;
  evidencias: Adjunto[];
};
type DiaBajas = {
  registro_id: number;
  fecha: string;
  dia: number;
  mortalidad: number;
  porcentaje: number;
  prioridad: boolean;
  fotos: Adjunto[];
  revision: Revision | null;
};
type Bajas = { umbral: number; activo: boolean; pendientes: number; dias: DiaBajas[] };
type Catalogo = { dictamenes: Record<string, string>; causas: string[]; dias_visita: number };

const AYUDA_DICTAMEN: Record<string, string> = {
  NORMAL: "Bajas esperables para la edad. Se registra la causa y no se avisa a nadie.",
  VISITA: "Hace falta ver el galpón. Al productor le llega la fecha de tu visita.",
  BROTE: "Riesgo sanitario. Llega una alerta urgente al productor y al personal, y puedes indicar el tratamiento enseguida.",
};
const VACIO = { dictamen: "NORMAL", causa: "", observaciones: "", fechaVisita: "" };

function sumarDias(dias: number) {
  const f = new Date();
  f.setDate(f.getDate() + dias);
  return `${f.getFullYear()}-${String(f.getMonth() + 1).padStart(2, "0")}-${String(f.getDate()).padStart(2, "0")}`;
}

export default function Bajas() {
  const { usuario } = useAuth();
  const { loteId } = useLote();
  const avisar = useToast();
  const navigate = useNavigate();
  const [datos, setDatos] = useState<Bajas | null>(null);
  const [catalogo, setCatalogo] = useState<Catalogo | null>(null);
  const [filtro, setFiltro] = useState("PENDIENTES");
  const [evaluando, setEvaluando] = useState<DiaBajas | null>(null);
  const [form, setForm] = useState(VACIO);
  const [evidencias, setEvidencias] = useState<Adjunto[]>([]);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState("");
  const esVet = usuario?.rol === "VETERINARIO";

  async function cargar() {
    if (!loteId) return;
    setDatos(await api<Bajas>(`/lotes/${loteId}/bajas`));
  }

  useEffect(() => {
    cargar().catch((err) => avisar(mensajeError(err), "riesgo"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loteId]);

  useEffect(() => {
    api<Catalogo>("/catalogo/causas-bajas").then(setCatalogo).catch(() => undefined);
  }, []);

  function abrir(dia: DiaBajas) {
    setError("");
    setForm(VACIO);
    setEvidencias([]);
    setEvaluando(dia);
  }

  async function guardar() {
    if (!evaluando) return;
    setError("");
    setGuardando(true);
    try {
      await api(`/registros/${evaluando.registro_id}/revision`, {
        method: "POST",
        body: JSON.stringify({
          dictamen: form.dictamen,
          causa: form.causa,
          observaciones: form.observaciones,
          fecha_visita: form.dictamen === "VISITA" ? form.fechaVisita : null,
          adjuntos: evidencias.map((a) => a.id),
        }),
      });
      const dia = evaluando;
      setEvaluando(null);
      await cargar();
      if (form.dictamen === "BROTE") {
        avisar("Dictamen guardado. Se avisó al productor y al personal. Indica ahora el tratamiento.", "riesgo");
        const diagnostico = `Bajas del ${fecha(dia.fecha)} (${dia.mortalidad} aves): ${form.causa}. ${form.observaciones}`.slice(0, 300);
        navigate(`/sanidad?indicar=1&diagnostico=${encodeURIComponent(diagnostico)}`);
      } else {
        avisar(form.dictamen === "VISITA" ? "Dictamen guardado. Se avisó al productor de tu visita." : "Dictamen guardado.");
      }
    } catch (err) {
      setError(mensajeError(err, "No se guardó el dictamen"));
    } finally {
      setGuardando(false);
    }
  }

  if (!datos) return <p className="muted">Cargando…</p>;
  const visibles = datos.dias.filter((d) => (filtro === "PENDIENTES" ? !d.revision : filtro === "REVISADOS" ? !!d.revision : true));
  const puedeEvaluar = esVet && datos.activo;

  return (
    <>
      <PageHeader
        titulo="Revisión de bajas"
        descripcion={
          esVet
            ? "Cada día con bajas queda por revisar. Mira las fotos del personal y deja tu dictamen: mortalidad normal, visita al galpón o posible brote."
            : "Días con bajas del lote y el dictamen del médico veterinario sobre su causa."
        }
      />
      <Panel sinPadding>
        <div className="panel-body" style={{ paddingBottom: 0 }}>
          <Tabs
            valor={filtro}
            onCambio={setFiltro}
            items={[
              { id: "PENDIENTES", label: "Por revisar", cantidad: datos.pendientes },
              { id: "REVISADOS", label: "Revisados", cantidad: datos.dias.length - datos.pendientes },
              { id: "TODOS", label: "Todos", cantidad: datos.dias.length },
            ]}
          />
        </div>
        <div className="panel-body bajas-lista">
          {visibles.length === 0 ? (
            <Vacio
              icono="ave"
              titulo={filtro === "PENDIENTES" ? "No hay bajas por revisar" : "No hay días en esta lista"}
              texto={filtro === "PENDIENTES" ? "Cuando el personal registre un día con bajas, aparecerá aquí con sus fotos." : undefined}
            />
          ) : (
            visibles.map((d) => (
              <article key={d.registro_id} className={`baja-dia${d.prioridad && !d.revision ? " prioridad" : ""}`}>
                <header>
                  <div>
                    <h3>{fecha(d.fecha)} · día {d.dia}</h3>
                    <p>
                      <b>{num(d.mortalidad)} {d.mortalidad === 1 ? "baja" : "bajas"}</b> · {num(d.porcentaje, 2)} % de las aves
                      {d.prioridad && <span className="chip-riesgo">Supera el umbral de {datos.umbral}</span>}
                    </p>
                  </div>
                  {d.revision ? (
                    <span className={`dictamen ${d.revision.dictamen.toLowerCase()}`}>{d.revision.dictamen_nombre}</span>
                  ) : puedeEvaluar ? (
                    <button className="btn primario small" type="button" onClick={() => abrir(d)}>Evaluar</button>
                  ) : (
                    <span className="dictamen pendiente">Por revisar</span>
                  )}
                </header>
                {d.fotos.length > 0 ? (
                  <ListaEvidencia seccion="BAJAS" archivos={d.fotos} />
                ) : (
                  <p className="muted baja-sin-fotos">El personal no adjuntó fotos de las bajas de este día.</p>
                )}
                {d.revision && (
                  <div className="baja-revision">
                    <p><b>Causa probable:</b> {d.revision.causa}</p>
                    {d.revision.fecha_visita && <p><b>Visita al galpón:</b> {fecha(d.revision.fecha_visita)}</p>}
                    {d.revision.observaciones && <p><b>Indicaciones:</b> {d.revision.observaciones}</p>}
                    {d.revision.evidencias.length > 0 && <ListaEvidencia seccion="REVISION" archivos={d.revision.evidencias} />}
                    <small className="muted">
                      {d.revision.veterinario ?? "Médico veterinario"} · {fecha(d.revision.creada_en)} {d.revision.creada_en.slice(11, 16)}
                      {d.revision.dictamen === "BROTE" && <> · <Link to="/sanidad">Ver tratamientos</Link></>}
                    </small>
                  </div>
                )}
              </article>
            ))
          )}
        </div>
      </Panel>

      <DrawerForm
        abierto={evaluando !== null}
        titulo={evaluando ? `Evaluar bajas del ${fecha(evaluando.fecha)}` : "Evaluar bajas"}
        descripcion={evaluando ? `Día ${evaluando.dia} · ${num(evaluando.mortalidad)} bajas (${num(evaluando.porcentaje, 2)} % de las aves).` : undefined}
        onCerrar={() => setEvaluando(null)}
        onGuardar={guardar}
        guardando={guardando}
        textoGuardar="Guardar dictamen"
        error={error}
        ancho="amplio"
      >
        {evaluando && evaluando.fotos.length > 0 && (
          <Seccion titulo="Fotos del personal">
            <ListaEvidencia seccion="BAJAS" archivos={evaluando.fotos} />
          </Seccion>
        )}
        <Seccion titulo="Dictamen">
          <div className="dictamen-opciones" role="radiogroup">
            {Object.entries(catalogo?.dictamenes ?? {}).map(([id, nombre]) => (
              <label key={id} className={`dictamen-opcion ${id.toLowerCase()}${form.dictamen === id ? " elegida" : ""}`}>
                <input type="radio" name="dictamen" value={id} checked={form.dictamen === id} onChange={() => setForm({ ...form, dictamen: id })} />
                <b>{nombre}</b>
                <small>{AYUDA_DICTAMEN[id]}</small>
              </label>
            ))}
          </div>
          <Campo label="Causa probable">
            <select value={form.causa} onChange={(e) => setForm({ ...form, causa: e.target.value })} required>
              <option value="" disabled>Elige la causa…</option>
              {catalogo?.causas.map((c) => <option key={c}>{c}</option>)}
            </select>
          </Campo>
          {form.dictamen === "VISITA" && (
            <Campo label="Fecha de la visita" ayuda={`Desde hoy y hasta ${catalogo?.dias_visita ?? 14} días.`}>
              <input type="date" value={form.fechaVisita} min={hoyLocal()} max={sumarDias(catalogo?.dias_visita ?? 14)} onChange={(e) => setForm({ ...form, fechaVisita: e.target.value })} required />
            </Campo>
          )}
          <Campo
            label={form.dictamen === "BROTE" ? "Qué observaste y qué debe hacer el personal" : "Observaciones"}
            ancho
            ayuda={form.dictamen === "BROTE" ? "Por ejemplo: aislar el galpón, no mover aves, retirar las muertas dos veces al día." : undefined}
          >
            <textarea rows={3} maxLength={1000} value={form.observaciones} onChange={(e) => setForm({ ...form, observaciones: e.target.value })} required={form.dictamen === "BROTE"} minLength={form.dictamen === "BROTE" ? 10 : undefined} />
          </Campo>
        </Seccion>
        <Seccion titulo="Tus evidencias">
          <ZonaEvidencia
            seccion="REVISION"
            ayuda="Fotos de la necropsia, de lesiones o el resultado del laboratorio. Son opcionales."
            archivos={evidencias}
            ruta="/adjuntos/temporales"
            onCambio={setEvidencias}
          />
        </Seccion>
      </DrawerForm>
    </>
  );
}
