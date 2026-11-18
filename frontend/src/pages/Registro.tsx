import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, fecha, hoyLocal, num, type Balanza, type Panel as PanelLote } from "../api";
import { Campo, Icon, PageHeader, Panel, Seccion, Tabs, Vacio, mensajeError, useToast } from "../components/ui";
import { useLote } from "../lote";
import { valorCampo } from "../textos";
import { ZonaEvidencia, type Adjunto, type Seccion as SeccionEvidencia } from "../components/Evidencias";

const VACIO = { mortalidad: "", descartadas: "", alimento: "", agua: "", peso: "", luz: "", pesos: "", machos: "", hembras: "" };

type Modo = "PROMEDIO" | "GRUPO" | "INDIVIDUAL" | "SEXO" | "BALANZA";
type Grupo = { aves: string; kg: string };
const MODOS: { id: Modo; label: string; ayuda: string }[] = [
  { id: "PROMEDIO", label: "Solo promedio", ayuda: "Anota directamente el peso promedio por ave." },
  { id: "GRUPO", label: "En grupo", ayuda: "Recomendado del día 0 al 21: pesa varias aves juntas en un balde o jaba (sin contar la tara) y anota cuántas eran y los kilos. El promedio se calcula solo." },
  { id: "INDIVIDUAL", label: "Ave por ave", ayuda: "Recomendado desde el día 21: pesa al menos 5 aves de distintas zonas del galpón. Así se mide la uniformidad y el CV del lote." },
  { id: "SEXO", label: "Machos y hembras", ayuda: "Si el lote es mixto, pesa machos y hembras por separado: crecen distinto y conviene ver cada curva." },
  { id: "BALANZA", label: "Balanza automática", ayuda: "Usa las aves que se subieron solas a la balanza del galpón ese día. Las lecturas de un ave subiendo o de dos aves juntas ya están descartadas." },
];

function gruposValidos(grupos: Grupo[]) {
  return grupos.map((g) => ({ aves: Number(g.aves), kg: Number(g.kg) })).filter((g) => g.aves > 0 && g.kg > 0);
}

/** Promedio que sale de los pesos anotados, si alcanzan. */
function muestraCalculada(modo: Modo, datos: typeof VACIO, grupos: Grupo[]) {
  if (modo === "GRUPO") {
    const validos = gruposValidos(grupos);
    const aves = validos.reduce((t, g) => t + g.aves, 0);
    if (!aves) return null;
    return { promedio: (validos.reduce((t, g) => t + g.kg, 0) * 1000) / aves, texto: `${aves} aves en ${validos.length} pesada(s).` };
  }
  const lista = modo === "INDIVIDUAL" ? leerPesos(datos.pesos) : modo === "SEXO" ? [...leerPesos(datos.machos), ...leerPesos(datos.hembras)] : [];
  if (lista.length < 5) return null;
  const u = uniformidad(lista);
  return { promedio: u.promedio, texto: `${lista.length} aves · uniformidad ${num(u.pct)} % (dentro de ±10 % del promedio).` };
}

/** Pesos escritos a mano ("2950 3010, 2880") → números. */
function leerPesos(texto: string) {
  return texto.split(/[\s,;]+/).filter(Boolean).map(Number).filter((n) => n > 0);
}

/** Aves dentro de ±10 % del promedio de la muestra. */
function uniformidad(pesos: number[]) {
  const promedio = pesos.reduce((t, p) => t + p, 0) / pesos.length;
  return { promedio, pct: (pesos.filter((p) => Math.abs(p - promedio) <= promedio * 0.1).length / pesos.length) * 100 };
}
const FASES = ["Preinicio", "Inicio", "Crecimiento", "Acabado", "Retiro"];

export default function Registro() {
  const { loteId, recargar } = useLote();
  const avisar = useToast();
  const [panel, setPanel] = useState<PanelLote | null>(null);
  const [dia, setDia] = useState(hoyLocal);
  const [datos, setDatos] = useState(VACIO);
  // Vacío = el que indica el plan para hoy.
  const [fase, setFase] = useState("");
  const [modo, setModo] = useState<Modo>("PROMEDIO");
  const [grupos, setGrupos] = useState<Grupo[]>([{ aves: "", kg: "" }]);
  const [balanzaDia, setBalanzaDia] = useState<Balanza | null>(null);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState("");
  const [resultado, setResultado] = useState<{ fecha: string; alertas: { mensaje: string; tipo: string }[] } | null>(null);
  // Evidencias opcionales: se suben al elegirlas y se vinculan al registro al guardar.
  const [evidencias, setEvidencias] = useState<Adjunto[]>([]);
  const zona = (seccion: SeccionEvidencia, ayuda: string) => (
    <ZonaEvidencia
      seccion={seccion}
      ayuda={ayuda}
      archivos={evidencias.filter((a) => a.seccion === seccion)}
      ruta="/adjuntos/temporales"
      onCambio={(lista) => setEvidencias([...evidencias.filter((a) => a.seccion !== seccion), ...lista])}
    />
  );

  async function cargar() {
    if (!loteId) return;
    const data = await api<PanelLote>(`/lotes/${loteId}/panel`);
    setPanel(data);
    // Con balanza en el galpón se usa ella; sin balanza, en grupo del día 0 al 21 y ave por ave después.
    setModo(data.balanza?.suficiente ? "BALANZA" : data.pesaje.metodo_sugerido);
  }

  // Pesadas de la balanza para el día que se registra.
  useEffect(() => {
    if (!loteId || modo !== "BALANZA") return;
    setBalanzaDia(null);
    api<Balanza>(`/lotes/${loteId}/balanza?fecha=${dia}`).then(setBalanzaDia).catch(() => setBalanzaDia(null));
  }, [loteId, modo, dia]);

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
          peso_muestra_g: calculado ? Math.round(calculado.promedio) : Number(datos.peso),
          fase_alimento: fase || panel?.alimento_hoy?.nombre || "",
          adjuntos: evidencias.map((a) => a.id),
          descartadas: Number(datos.descartadas || 0),
          horas_luz: datos.luz === "" ? null : Number(datos.luz),
          pesos_muestra: modo === "INDIVIDUAL" ? leerPesos(datos.pesos) : [],
          pesos_machos: modo === "SEXO" ? leerPesos(datos.machos) : [],
          pesos_hembras: modo === "SEXO" ? leerPesos(datos.hembras) : [],
          grupos: modo === "GRUPO" ? gruposValidos(grupos) : [],
          usar_balanza: modo === "BALANZA",
        }),
      });
      setResultado({ fecha: dia, alertas: data.alertas });
      setDatos(VACIO);
      setGrupos([{ aves: "", kg: "" }]);
      setFase("");
      setEvidencias([]);
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
  const set = (k: keyof typeof VACIO) => (e: React.ChangeEvent<HTMLInputElement>) => setDatos({ ...datos, [k]: valorCampo(e) });
  const yaRegistrado = panel.registros.some((r) => r.fecha === dia);
  const sugerido: Modo = panel.pesaje.metodo_sugerido;
  const calculado = modo === "BALANZA"
    ? balanzaDia?.estadisticas
      ? { promedio: balanzaDia.estadisticas.promedio, texto: `${balanzaDia.validas} aves válidas de la balanza · uniformidad ${num(balanzaDia.estadisticas.uniformidad)} % · CV ${num(balanzaDia.estadisticas.cv, 1)} %.` }
      : null
    : muestraCalculada(modo, datos, grupos);
  const modos = MODOS.filter((m) => m.id !== "BALANZA" || panel.balanza);
  const campoPesos = (k: "pesos" | "machos" | "hembras", label: string, ejemplo: string) => {
    const lista = leerPesos(datos[k]);
    return (
      <Campo
        label={label}
        ancho
        ayuda={lista.length >= 5
          ? `${lista.length} aves · promedio ${num(Math.round(uniformidad(lista).promedio))} g · uniformidad ${num(uniformidad(lista).pct)} %`
          : "Anota al menos 5 pesos separados por espacios."}
      >
        <textarea rows={2} value={datos[k]} placeholder={ejemplo} onChange={(e) => setDatos({ ...datos, [k]: e.target.value.replace(/[^\d\s,;]/g, "").slice(0, 1200) })} />
      </Campo>
    );
  };
  const setGrupo = (i: number, cambio: Partial<Grupo>) => setGrupos(grupos.map((g, j) => (j === i ? { ...g, ...cambio } : g)));

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
                    <input type="number" min="0" max={panel.aves_vivas} inputMode="numeric" value={datos.mortalidad} onChange={set("mortalidad")} placeholder={anterior ? `Anterior: ${anterior.mortalidad}` : "0"} required />
                  </Campo>
                  <Campo label="De ellas, sacrificadas" ayuda="Aves débiles o cojas que se retiraron. El resto murió sola.">
                    <input type="number" min="0" max={Number(datos.mortalidad || 0)} inputMode="numeric" value={datos.descartadas} onChange={set("descartadas")} placeholder="0" />
                  </Campo>
                  {zona("BAJAS", "Foto de las aves muertas del día, por ejemplo en la bandeja de bajas, o de la hoja donde se anotaron. Sirve al veterinario para revisar la causa.")}
                </Seccion>
                <Seccion titulo="3. Consumo">
                  <Campo
                    label="Tipo de alimento"
                    ancho
                    ayuda={panel.alimento_hoy ? `Según el plan del veterinario hoy corresponde ${panel.alimento_hoy.nombre}${panel.alimento_hoy.producto ? ` (${panel.alimento_hoy.producto})` : ""}. Cámbialo solo si diste otro.` : undefined}
                  >
                    <select value={fase || panel.alimento_hoy?.nombre || ""} onChange={(e) => setFase(e.target.value)}>
                      {FASES.map((f) => <option key={f}>{f}</option>)}
                    </select>
                  </Campo>
                  <Campo label="Alimento (kg)">
                    <input type="number" min="0" max={Math.floor(panel.aves_vivas * 0.35 + 1)} step="0.1" inputMode="decimal" value={datos.alimento} onChange={set("alimento")} placeholder={anterior ? `Anterior: ${num(anterior.alimento_kg, 1)}` : ""} required />
                  </Campo>
                  <Campo label="Agua (L)" ayuda={panel.agua_medidor_hoy_l != null ? `El medidor del galpón lleva ${num(panel.agua_medidor_hoy_l, 1)} L hoy.` : undefined}>
                    <input type="number" min="0" max={Math.floor(panel.aves_vivas * 0.8 + 1)} step="0.1" inputMode="decimal" value={datos.agua} onChange={set("agua")} placeholder={anterior ? `Anterior: ${num(anterior.agua_l, 1)}` : ""} required />
                  </Campo>
                  <Campo label="Horas de luz" ayuda="Horas que estuvo encendida la luz del galpón. Opcional.">
                    <input type="number" min="0" max="24" step="0.5" inputMode="decimal" value={datos.luz} onChange={set("luz")} placeholder="Ej. 18" />
                  </Campo>
                  {zona("CONSUMO", "Foto de los sacos de alimento usados, de la balanza o de la lectura del medidor de agua.")}
                </Seccion>
                <Seccion titulo="4. Pesaje">
                  <div className="pesaje-modo">
                    <Tabs items={modos.map((m) => ({ id: m.id, label: m.id === sugerido ? `${m.label} (sugerido)` : m.label }))} valor={modo} onCambio={(id) => setModo(id as Modo)} />
                    <p className="muted">{MODOS.find((m) => m.id === modo)!.ayuda}</p>
                  </div>
                  {modo === "GRUPO" && (
                    <div className="pesaje-grupos">
                      {grupos.map((g, i) => (
                        <div className="pesaje-grupo" key={i}>
                          <span>Pesada {i + 1}</span>
                          <input type="number" min="1" max="500" inputMode="numeric" aria-label="Aves" placeholder="Aves" value={g.aves} onChange={(e) => setGrupo(i, { aves: valorCampo(e) })} />
                          <input type="number" min="0" step="0.01" inputMode="decimal" aria-label="Kilos" placeholder="Kilos" value={g.kg} onChange={(e) => setGrupo(i, { kg: valorCampo(e) })} />
                          {grupos.length > 1 && <button type="button" className="btn small secondary" onClick={() => setGrupos(grupos.filter((_, j) => j !== i))}>Quitar</button>}
                        </div>
                      ))}
                      <button type="button" className="btn small secondary" onClick={() => setGrupos([...grupos, { aves: "", kg: "" }])}><Icon name="mas" size={15} /> Otra pesada</button>
                    </div>
                  )}
                  {modo === "BALANZA" && balanzaDia && !balanzaDia.suficiente && (
                    <div className="aviso alerta pesaje-modo">
                      <Icon name="aviso" />
                      <span>La balanza tiene {balanzaDia.validas} pesada(s) válida(s) del {fecha(dia)}. Se necesitan al menos 5: elige otro modo o espera más pesadas.</span>
                    </div>
                  )}
                  {modo === "INDIVIDUAL" && campoPesos("pesos", "Pesos de cada ave (g)", "2950 3010 2880 3120 2990")}
                  {modo === "SEXO" && (
                    <>
                      {campoPesos("machos", "Machos (g)", "3150 3220 3080 3300 3190")}
                      {campoPesos("hembras", "Hembras (g)", "2700 2650 2780 2720 2690")}
                    </>
                  )}
                  <Campo
                    label="Peso promedio por ave (g)"
                    ayuda={calculado
                      ? `${calculado.texto} Para hoy la curva ${panel.lote.linea} espera cerca de ${num(panel.peso_esperado_g)} g.`
                      : `Para hoy la curva ${panel.lote.linea} espera cerca de ${num(panel.peso_esperado_g)} g.`}
                  >
                    <input type="number" min="25" max="6000" step="1" inputMode="numeric" value={calculado ? Math.round(calculado.promedio) : datos.peso} onChange={set("peso")} placeholder={`≈ ${Math.round(panel.peso_esperado_g)}`} required readOnly={!!calculado} />
                  </Campo>
                  {zona("PESAJE", "Foto de la balanza con el grupo de pollos pesado o de la hoja de pesaje.")}
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
