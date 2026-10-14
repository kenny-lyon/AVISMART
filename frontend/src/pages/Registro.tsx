import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, fecha, hoyLocal, num, type Panel as PanelLote } from "../api";
import { Campo, Icon, PageHeader, Panel, Seccion, Vacio, mensajeError, useToast } from "../components/ui";
import { useLote } from "../lote";

const VACIO = { mortalidad: "", alimento: "", agua: "", peso: "" };

export default function Registro() {
  const { loteId, recargar } = useLote();
  const avisar = useToast();
  const [panel, setPanel] = useState<PanelLote | null>(null);
  const [dia, setDia] = useState(hoyLocal);
  const [datos, setDatos] = useState(VACIO);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState("");
  const [resultado, setResultado] = useState<{ fecha: string; alertas: { mensaje: string; tipo: string }[] } | null>(null);

  async function cargar() {
    if (!loteId) return;
    setPanel(await api<PanelLote>(`/lotes/${loteId}/panel`));
  }

  useEffect(() => {
    setResultado(null);
    cargar().catch((err) => setError(mensajeError(err)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loteId]);

  async function guardar(e: React.FormEvent) {
    e.preventDefault();
    if (!loteId) return;
    setError("");
    setGuardando(true);
    try {
      const data = await api<{ alertas: { mensaje: string; tipo: string }[] }>(`/lotes/${loteId}/registros`, {
        method: "POST",
        body: JSON.stringify({
          fecha: dia,
          mortalidad: Number(datos.mortalidad),
          alimento_kg: Number(datos.alimento),
          agua_l: Number(datos.agua),
          peso_muestra_g: Number(datos.peso),
        }),
      });
      setResultado({ fecha: dia, alertas: data.alertas });
      setDatos(VACIO);
      avisar(data.alertas.length ? `Registro guardado con ${data.alertas.length} alerta(s).` : "Registro guardado.");
      await Promise.all([recargar(), cargar()]);
    } catch (err) {
      setError(mensajeError(err, "No se guardó el registro"));
    } finally {
      setGuardando(false);
    }
  }

  if (!panel) return <p className="muted">{error || "Cargando el lote…"}</p>;
  const anterior = panel.registros[0];
  const cerrado = panel.lote.estado !== "ACTIVO";
  const set = (k: keyof typeof VACIO) => (e: React.ChangeEvent<HTMLInputElement>) => setDatos({ ...datos, [k]: e.target.value });
  const yaRegistrado = panel.registros.some((r) => r.fecha === dia);

  return (
    <>
      <PageHeader
        titulo="Registro del día"
        descripcion={`${panel.lote.galpon} · ${panel.lote.linea} · día ${panel.dia_vida} de vida. Anota lo observado en el galpón; el panel y las alertas se actualizan al guardar.`}
      />

      {cerrado ? (
        <Panel><Vacio icono="lotes" titulo="Este lote ya está cerrado" texto="Elige un lote activo en la barra superior para registrar el día." /></Panel>
      ) : (
        <div className="registro-layout">
          <Panel sinPadding>
            <form onSubmit={guardar}>
              <div className="panel-body">
                {error && <div className="aviso riesgo"><Icon name="aviso" />{error}</div>}
                {resultado && (
                  <div className={resultado.alertas.length ? "aviso alerta" : "aviso ok"}>
                    <Icon name={resultado.alertas.length ? "aviso" : "check"} />
                    <div>
                      <b>Registro del {fecha(resultado.fecha)} guardado.</b>{" "}
                      {resultado.alertas.length
                        ? resultado.alertas.map((a) => a.mensaje).join(" ")
                        : "Todo dentro de rango."}{" "}
                      <Link to="/panel">Ver panel</Link>
                    </div>
                  </div>
                )}
                <Seccion titulo="1. Fecha">
                  <Campo label="Día que se registra" ayuda={yaRegistrado ? "Ya hay un registro para esta fecha." : undefined}>
                    <input type="date" value={dia} min={panel.lote.fecha_ingreso} max={hoyLocal()} onChange={(e) => setDia(e.target.value)} required />
                  </Campo>
                </Seccion>
                <Seccion titulo="2. Bajas">
                  <Campo label="Aves muertas" ayuda={`Alerta si supera ${panel.umbral_mortalidad} aves.`}>
                    <input type="number" min="0" inputMode="numeric" value={datos.mortalidad} onChange={set("mortalidad")} placeholder={anterior ? `Anterior: ${anterior.mortalidad}` : "0"} required />
                  </Campo>
                </Seccion>
                <Seccion titulo="3. Consumo">
                  <Campo label="Alimento (kg)">
                    <input type="number" min="0" step="0.1" inputMode="decimal" value={datos.alimento} onChange={set("alimento")} placeholder={anterior ? `Anterior: ${num(anterior.alimento_kg, 1)}` : ""} required />
                  </Campo>
                  <Campo label="Agua (L)">
                    <input type="number" min="0" step="0.1" inputMode="decimal" value={datos.agua} onChange={set("agua")} placeholder={anterior ? `Anterior: ${num(anterior.agua_l, 1)}` : ""} required />
                  </Campo>
                </Seccion>
                <Seccion titulo="4. Pesaje">
                  <Campo label="Peso promedio por ave (g)" ayuda={`Pesa un grupo de pollos (por ejemplo 50), suma los gramos y divide entre la cantidad. Para hoy la curva ${panel.lote.linea} espera cerca de ${num(panel.peso_esperado_g)} g.`}>
                    <input type="number" min="1" step="1" inputMode="numeric" value={datos.peso} onChange={set("peso")} placeholder={`≈ ${Math.round(panel.peso_esperado_g)}`} required />
                  </Campo>
                </Seccion>
              </div>
              <div className="form-pie">
                <button className="btn secondary" type="button" onClick={() => { setDatos(VACIO); setError(""); }}>Limpiar</button>
                <button className="btn primario" type="submit" disabled={guardando || yaRegistrado}>
                  {guardando ? "Guardando…" : "Guardar registro"}
                </button>
              </div>
            </form>
          </Panel>

          <Panel titulo="Referencia del lote">
            <div className="referencia">
              <div><span>Día de vida</span><strong>{panel.dia_vida}</strong></div>
              <div><span>Aves vivas</span><strong>{num(panel.aves_vivas)}</strong></div>
              <div><span>Peso esperado hoy</span><strong>{num(panel.peso_esperado_g)} g</strong></div>
              <div><span>Umbral de mortalidad</span><strong>{panel.umbral_mortalidad} aves/día</strong></div>
              <div><span>Último registro</span><strong>{anterior ? fecha(anterior.fecha) : "—"}</strong></div>
              {anterior && (
                <>
                  <div><span>Bajas</span><strong>{anterior.mortalidad}</strong></div>
                  <div><span>Alimento / agua</span><strong>{num(anterior.alimento_kg, 1)} kg · {num(anterior.agua_l, 1)} L</strong></div>
                  <div><span>Peso</span><strong>{num(anterior.peso_muestra_g)} g</strong></div>
                </>
              )}
            </div>
          </Panel>
        </div>
      )}
    </>
  );
}
