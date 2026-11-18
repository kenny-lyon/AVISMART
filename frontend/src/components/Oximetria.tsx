import { useEffect, useState } from "react";
import { api, fecha, hoyLocal, num } from "../api";
import { Campo, DrawerForm, Icon, Seccion, Vacio, mensajeError, useToast } from "./ui";
import { valorCampo } from "../textos";

type Medicion = { id: number; fecha: string; aves_medidas: number; spo2_promedio: number; spo2_minimo: number | null; nota: string; veterinario: string | null };
type Datos = { activo: boolean; caida_alerta: number; mediciones: Medicion[] };
const VACIO = { fecha: hoyLocal(), aves: "10", promedio: "", minimo: "", nota: "" };

/** Saturación de oxígeno del lote: señal temprana del síndrome ascítico en altura. */
export default function Oximetria({ loteId, esVet, onCantidad }: { loteId: number; esVet: boolean; onCantidad: (n: number) => void }) {
  const avisar = useToast();
  const [datos, setDatos] = useState<Datos | null>(null);
  const [abierto, setAbierto] = useState(false);
  const [form, setForm] = useState(VACIO);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState("");

  async function cargar() {
    const d = await api<Datos>(`/lotes/${loteId}/oximetria`);
    setDatos(d);
    onCantidad(d.mediciones.length);
  }

  useEffect(() => {
    cargar().catch((err) => avisar(mensajeError(err), "riesgo"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loteId]);

  async function guardar() {
    setError("");
    setGuardando(true);
    try {
      const r = await api<{ alerta: boolean }>(`/lotes/${loteId}/oximetria`, {
        method: "POST",
        body: JSON.stringify({
          fecha: form.fecha,
          aves_medidas: Number(form.aves),
          spo2_promedio: Number(form.promedio),
          spo2_minimo: form.minimo === "" ? null : Number(form.minimo),
          nota: form.nota,
        }),
      });
      setAbierto(false);
      await cargar();
      avisar(r.alerta ? "Medición guardada. La saturación bajó: se avisó al productor." : "Medición guardada.", r.alerta ? "riesgo" : "ok");
    } catch (err) {
      setError(mensajeError(err, "No se guardó la medición"));
    } finally {
      setGuardando(false);
    }
  }

  if (!datos) return <p className="muted panel-body">Cargando…</p>;
  const campo = (k: keyof typeof VACIO) => ({
    value: form[k],
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setForm({ ...form, [k]: valorCampo(e) }),
  });

  return (
    <>
      <div className="panel-body oximetria-cabecera">
        <p className="muted">
          En altura, una saturación que baja avisa del síndrome ascítico antes de que aparezcan las bajas. Mide unas 10 aves por semana con un
          oxímetro de pulso. Si cae {datos.caida_alerta} puntos o más frente a la medición anterior, se avisa al productor.
        </p>
        {esVet && datos.activo && (
          <button className="btn primario" type="button" onClick={() => { setError(""); setForm({ ...VACIO, fecha: hoyLocal() }); setAbierto(true); }}>
            <Icon name="mas" size={15} /> Nueva medición
          </button>
        )}
      </div>
      {datos.mediciones.length === 0 ? (
        <Vacio icono="sanidad" titulo="Sin mediciones todavía" texto="El médico veterinario registra aquí la saturación de oxígeno del lote." />
      ) : (
        <div className="tabla-wrap">
          <table>
            <thead><tr><th>Fecha</th><th>Aves medidas</th><th>SpO₂ promedio</th><th>SpO₂ mínima</th><th>Cambio</th><th>Nota</th></tr></thead>
            <tbody>
              {datos.mediciones.map((m, i) => {
                const previa = datos.mediciones[i + 1];
                const cambio = previa ? m.spo2_promedio - previa.spo2_promedio : null;
                return (
                  <tr key={m.id}>
                    <td>{fecha(m.fecha)}</td>
                    <td className="num">{m.aves_medidas}</td>
                    <td className="num"><b>{num(m.spo2_promedio, 1)} %</b></td>
                    <td className="num">{m.spo2_minimo != null ? `${num(m.spo2_minimo, 1)} %` : "—"}</td>
                    <td className="num" style={cambio != null && cambio <= -datos.caida_alerta ? { color: "var(--riesgo)", fontWeight: 700 } : undefined}>
                      {cambio == null ? "—" : `${cambio > 0 ? "+" : cambio < 0 ? "−" : ""}${num(Math.abs(cambio), 1)}`}
                    </td>
                    <td>{m.nota || <span className="muted">—</span>}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      <DrawerForm abierto={abierto} titulo="Nueva medición de oxígeno" descripcion="Saturación medida con oxímetro de pulso en una muestra de aves." onCerrar={() => setAbierto(false)} onGuardar={guardar} guardando={guardando} textoGuardar="Guardar medición" error={error}>
        <Seccion titulo="Medición">
          <Campo label="Fecha"><input type="date" max={hoyLocal()} {...campo("fecha")} required /></Campo>
          <Campo label="Aves medidas"><input type="number" min="1" max="200" {...campo("aves")} required /></Campo>
          <Campo label="SpO₂ promedio (%)"><input type="number" min="50" max="100" step="0.1" {...campo("promedio")} required /></Campo>
          <Campo label="SpO₂ más baja (%)" ayuda="Opcional."><input type="number" min="30" max="100" step="0.1" {...campo("minimo")} /></Campo>
          <Campo label="Nota" ancho><textarea rows={2} maxLength={500} {...campo("nota")} /></Campo>
        </Seccion>
      </DrawerForm>
    </>
  );
}
