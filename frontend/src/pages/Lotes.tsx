import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, descargar, fecha, hoyLocal, num, type CierreLote, type Lote, type Panel as PanelLote } from "../api";
import { useAuth } from "../auth";
import { Campo, DrawerForm, Estado, Icon, PageHeader, Panel, Seccion, Tabs, Vacio, mensajeError, useToast, Ayuda } from "../components/ui";
import { useLote } from "../lote";
import { LARGO_GUIA, LARGO_NOMBRE, limpiarTexto, valorCampo, textoDe } from "../textos";
import { EvidenciasLote, ZonaEvidencia, type Adjunto, type Seccion as SeccionEvidencia } from "../components/Evidencias";

const hoy = hoyLocal;
const SEXOS: Record<string, string> = { MIXTO: "Mixto", MACHOS: "Machos", HEMBRAS: "Hembras" };
const RECEPCION_VACIA = {
  proveedor: "",
  guia: "",
  sexo: "MIXTO",
  recibidos: "",
  descartes: "0",
  pesoLlegada: "42",
  precio: "",
  pesoObjetivo: "2800",
  edadSaca: "42",
  observaciones: "",
};
const CIERRE_VACIO = { fecha: "", aves: "", peso: "", precio: "", pollitos: "", alimento: "", sanidad: "", otros: "0", observaciones: "" };

type CatalogoLotes = {
  lineas: { nombre: string; curva: [number, number][] }[];
  incubadoras: string[];
  vacunas_incubadora: { nombre: string; via: string }[];
};
const LINEAS_BASE = ["Ross 308", "Cobb 500", "Hubbard", "Arbor Acres"];

/** Peso esperado (g) a cierta edad según la curva de la línea: interpolación lineal entre semanas. */
function pesoCurva(curva: [number, number][] | undefined, dia: number) {
  if (!curva?.length || !dia) return null;
  if (dia >= curva[curva.length - 1][0]) return curva[curva.length - 1][1];
  for (let i = 1; i < curva.length; i++) {
    const [d0, p0] = curva[i - 1];
    const [d1, p1] = curva[i];
    if (dia <= d1) return Math.round(p0 + ((p1 - p0) * (dia - d0)) / (d1 - d0));
  }
  return null;
}

/** Fecha local (AAAA-MM-DD) de hace `dias` días. */
function haceDias(dias: number) {
  const f = new Date();
  f.setDate(f.getDate() - dias);
  return `${f.getFullYear()}-${String(f.getMonth() + 1).padStart(2, "0")}-${String(f.getDate()).padStart(2, "0")}`;
}

export default function Lotes() {
  const { usuario } = useAuth();
  const { resumen, recargar, elegir } = useLote();
  const navigate = useNavigate();
  const avisar = useToast();
  const [filtro, setFiltro] = useState("ACTIVO");
  const [error, setError] = useState("");
  const [guardando, setGuardando] = useState(false);

  const [abriendo, setAbriendo] = useState(false);
  const [galponId, setGalponId] = useState<number | null>(null);
  const [linea, setLinea] = useState("Cobb 500");
  const [catalogo, setCatalogo] = useState<CatalogoLotes | null>(null);
  const [vacunasIncubadora, setVacunasIncubadora] = useState<string[]>([]);
  const [fechaIngreso, setFechaIngreso] = useState(hoy);
  const [recepcion, setRecepcion] = useState(RECEPCION_VACIA);

  const [cerrando, setCerrando] = useState<Lote | null>(null);
  const [vivas, setVivas] = useState<number | null>(null);
  const [cierre, setCierre] = useState(CIERRE_VACIO);

  const galpones = resumen?.galpones ?? [];
  const lotes = resumen?.lotes ?? [];
  const variasGranjas = (resumen?.granjas.length ?? 0) > 1;
  const galpon = galpones.find((g) => g.id === galponId) ?? null;
  // Un galpón solo admite un lote activo a la vez.
  const ocupante = (id: number) => lotes.find((l) => l.galpon_id === id && l.estado === "ACTIVO");
  const libres = galpones.filter((g) => !ocupante(g.id));
  const recibidos = Number(recepcion.recibidos || 0);
  const descartes = Number(recepcion.descartes || 0);
  const alojados = Math.max(recibidos - descartes, 0);
  const costoEstimado = recibidos * Number(recepcion.precio || 0);
  const setR = (k: keyof typeof RECEPCION_VACIA) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
    setRecepcion({ ...recepcion, [k]: valorCampo(e) });
  const puedeGestionar = usuario?.rol === "PRODUCTOR" || usuario?.rol === "ADMIN";
  const visibles = filtro === "TODOS" ? lotes : lotes.filter((l) => l.estado === filtro);

  const curvaLinea = catalogo?.lineas.find((l) => l.nombre === linea)?.curva;
  const pesoEsperadoSaca = pesoCurva(curvaLinea, Number(recepcion.edadSaca));

  const [evidencias, setEvidencias] = useState<Adjunto[]>([]);
  const [verEvidencias, setVerEvidencias] = useState<Lote | null>(null);
  const deSeccion = (seccion: SeccionEvidencia) => evidencias.filter((a) => a.seccion === seccion);
  const zona = (seccion: SeccionEvidencia, ayuda: string, obligatoria = false) => (
    <ZonaEvidencia
      seccion={seccion}
      ayuda={ayuda}
      obligatoria={obligatoria}
      archivos={deSeccion(seccion)}
      ruta="/adjuntos/temporales"
      onCambio={(lista) => setEvidencias([...evidencias.filter((a) => a.seccion !== seccion), ...lista])}
    />
  );

  function abrirFormulario() {
    setError("");
    if (!catalogo) api<CatalogoLotes>("/catalogo/lotes").then(setCatalogo).catch(() => undefined);
    setFechaIngreso(hoy());
    setRecepcion(RECEPCION_VACIA);
    setVacunasIncubadora([]);
    setEvidencias([]);
    setGalponId(libres[0]?.id ?? null);
    setAbriendo(true);
  }

  async function crear() {
    if (!galponId) return;
    setError("");
    if (!evidencias.some((a) => a.seccion === "GUIA")) {
      setError("Adjunta la foto o el PDF de la guía de remisión (sección 2) para abrir el lote.");
      return;
    }
    setGuardando(true);
    try {
      const lote = await api<Lote>("/lotes", {
        method: "POST",
        body: JSON.stringify({
          galpon_id: galponId,
          linea,
          fecha_ingreso: fechaIngreso,
          proveedor: recepcion.proveedor,
          guia: recepcion.guia,
          sexo: recepcion.sexo,
          cantidad_recibida: recibidos,
          descarte_llegada: descartes,
          peso_llegada_g: Number(recepcion.pesoLlegada),
          precio_pollito: Number(recepcion.precio),
          peso_objetivo_g: Number(recepcion.pesoObjetivo),
          edad_saca_dias: Number(recepcion.edadSaca),
          observaciones: recepcion.observaciones,
          vacunas_incubadora: vacunasIncubadora,
          adjuntos: evidencias.map((a) => a.id),
        }),
      });
      await recargar();
      elegir(lote.id);
      setAbriendo(false);
      setFiltro("ACTIVO");
      avisar(`Lote ${lote.linea} abierto en ${lote.galpon}.`);
    } catch (err) {
      setError(mensajeError(err, "No se pudo abrir el lote"));
    } finally {
      setGuardando(false);
    }
  }

  async function prepararCierre(lote: Lote) {
    setError("");
    setCierre({ ...CIERRE_VACIO, fecha: hoy() });
    setVivas(null);
    setCerrando(lote);
    try {
      const panel = await api<PanelLote>(`/lotes/${lote.id}/panel`);
      setVivas(panel.aves_vivas);
      setCierre((c) => ({ ...c, aves: String(panel.aves_vivas), pollitos: lote.costo_pollitos != null ? String(lote.costo_pollitos) : c.pollitos }));
    } catch (err) {
      setError(mensajeError(err, "No se pudo preparar el cierre"));
    }
  }

  async function cerrar() {
    if (!cerrando) return;
    setError("");
    setGuardando(true);
    try {
      const resultado = await api<CierreLote>(`/lotes/${cerrando.id}/cerrar`, {
        method: "POST",
        body: JSON.stringify({
          fecha_cierre: cierre.fecha,
          aves_vendidas: Number(cierre.aves),
          peso_total_kg: Number(cierre.peso),
          precio_venta_kg: Number(cierre.precio),
          costo_pollitos: Number(cierre.pollitos),
          costo_alimento: Number(cierre.alimento),
          costo_sanidad: Number(cierre.sanidad),
          otros_costos: Number(cierre.otros),
          observaciones: cierre.observaciones,
        }),
      });
      await recargar();
      setCerrando(null);
      avisar(`Lote cerrado. Margen: S/ ${num(resultado.margen, 2)}.`);
    } catch (err) {
      setError(mensajeError(err, "No se pudo cerrar el lote"));
    } finally {
      setGuardando(false);
    }
  }

  async function bajar(lote: Lote, formato: "pdf" | "xlsx") {
    try {
      await descargar(`/lotes/${lote.id}/reporte.${formato}`, `avismart-lote-${lote.id}.${formato}`);
    } catch (err) {
      avisar(mensajeError(err, "No se pudo descargar el reporte"), "riesgo");
    }
  }

  const ingreso = Number(cierre.peso || 0) * Number(cierre.precio || 0);
  const pesoPromedio = Number(cierre.aves) > 0 ? (Number(cierre.peso || 0) * 1000) / Number(cierre.aves) : 0;
  const costos = ["pollitos", "alimento", "sanidad", "otros"].reduce((t, k) => t + Number(cierre[k as keyof typeof cierre] || 0), 0);
  const margen = ingreso - costos;
  const campoCierre = (k: keyof typeof cierre) => ({
    value: cierre[k],
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setCierre({ ...cierre, [k]: valorCampo(e) }),
  });

  return (
    <>
      <PageHeader
        titulo="Lotes"
        descripcion="Cada campaña de engorde vive en un lote, desde el ingreso de los pollitos hasta la venta."
        acciones={
          puedeGestionar && galpones.length > 0 && (
            <button className="btn primario" type="button" onClick={abrirFormulario}>
              <Icon name="mas" /> Abrir lote
            </button>
          )
        }
      />

      <Panel sinPadding>
        <div className="barra-lista">
          <Tabs
            valor={filtro}
            onCambio={setFiltro}
            items={[
              { id: "ACTIVO", label: "Activos", cantidad: lotes.filter((l) => l.estado === "ACTIVO").length },
              { id: "CERRADO", label: "Cerrados", cantidad: lotes.filter((l) => l.estado === "CERRADO").length },
              { id: "TODOS", label: "Todos", cantidad: lotes.length },
            ]}
          />
        </div>
        {galpones.length === 0 ? (
          <Vacio
            icono="granjas"
            titulo="Primero registra un galpón"
            texto="Los lotes se abren dentro de un galpón de tu granja avícola."
            accion={<Link className="btn" to="/instalaciones">Ir a Granjas y galpones</Link>}
          />
        ) : visibles.length === 0 ? (
          <Vacio icono="lotes" titulo={filtro === "CERRADO" ? "No hay lotes cerrados" : "No hay lotes en esta vista"} />
        ) : (
          <div className="tabla-wrap">
            <table>
              <thead>
                <tr><th>Lote</th><th>Origen</th><th>Ingreso</th><th>Pollitos</th><th>Edad</th><th>Estado</th><th /></tr>
              </thead>
              <tbody>
                {visibles.map((lote) => (
                  <tr key={lote.id}>
                    <td className="celda-principal">
                      <strong>{lote.galpon} · {lote.linea}</strong>
                      {variasGranjas && <small>{lote.granja}</small>}
                    </td>
                    <td className="celda-principal">
                      <strong>{lote.proveedor ?? <span className="muted">—</span>}</strong>
                      {lote.sexo && <small>{SEXOS[lote.sexo] ?? lote.sexo}{lote.guia ? ` · guía ${lote.guia}` : ""}</small>}
                    </td>
                    <td>{fecha(lote.fecha_ingreso)}</td>
                    <td className="num">{num(lote.poblacion_inicial)}</td>
                    <td className="num">día {lote.dia_vida}</td>
                    <td><Estado valor={lote.estado} /></td>
                    <td className="acciones">
                      <button className="link-button" type="button" onClick={() => { elegir(lote.id); navigate("/panel"); }}>Ver panel</button>
                      <button className="link-button" type="button" onClick={() => setVerEvidencias(lote)}>Evidencias</button>
                      {puedeGestionar && lote.estado === "ACTIVO" && (
                        <button className="link-button riesgo" type="button" onClick={() => prepararCierre(lote)}>Cerrar lote</button>
                      )}
                      {puedeGestionar && lote.estado === "CERRADO" && (
                        <>
                          <button className="link-button" type="button" onClick={() => bajar(lote, "pdf")}>PDF</button>
                          <button className="link-button" type="button" onClick={() => bajar(lote, "xlsx")}>Excel</button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <DrawerForm
        abierto={abriendo}
        titulo="Abrir lote"
        descripcion="Registra la recepción de los pollitos: de dónde vienen, cuántos llegaron y en qué estado."
        onCerrar={() => setAbriendo(false)}
        onGuardar={crear}
        guardando={guardando}
        textoGuardar="Abrir lote"
        error={error}
        ancho="amplio"
      >
        {libres.length === 0 && (
          <div className="aviso riesgo">
            <Icon name="aviso" />
            <span><b>Todos los galpones están ocupados.</b> Cierra el lote activo de un galpón (o agrega un galpón nuevo) para abrir otro.</span>
          </div>
        )}
        <Seccion titulo="1. Galpón y línea" marco>
          <Campo label="Galpón" ancho info="Un galpón solo puede tener un lote activo; los ocupados aparecen deshabilitados.">
            <select value={galponId ?? ""} onChange={(e) => {
              const nuevo = galpones.find((g) => g.id === Number(e.target.value));
              setGalponId(Number(e.target.value));
              // Al cambiar a un galpón más chico, los recibidos se ajustan a su capacidad.
              if (nuevo && Number(recepcion.recibidos) > nuevo.capacidad) {
                setRecepcion({ ...recepcion, recibidos: String(nuevo.capacidad), descartes: String(Math.min(Number(recepcion.descartes || 0), nuevo.capacidad - 1)) });
              }
            }} required>
              <option value="" disabled>Seleccionar galpón…</option>
              {galpones.map((g) => {
                const ocupado = ocupante(g.id);
                return (
                  <option key={g.id} value={g.id} disabled={!!ocupado}>
                    {variasGranjas ? `${g.granja} · ` : ""}{g.nombre} — capacidad {num(g.capacidad)}
                    {ocupado ? ` · OCUPADO (lote ${ocupado.linea} desde ${fecha(ocupado.fecha_ingreso)})` : " · libre"}
                  </option>
                );
              })}
            </select>
          </Campo>
          <Campo label="Línea genética" info="Define la curva de peso con la que se compara el lote.">
            <select value={linea} onChange={(e) => setLinea(e.target.value)}>
              {(catalogo?.lineas.map((l) => l.nombre) ?? LINEAS_BASE).map((n) => <option key={n}>{n}</option>)}
            </select>
          </Campo>
          <Campo label="Sexo">
            <select value={recepcion.sexo} onChange={setR("sexo")}>
              {Object.entries(SEXOS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </Campo>
          {zona("GALPON", "Fotos del galpón listo para recibir: cama de viruta, criadoras encendidas, bebederos y comederos.")}
        </Seccion>
        <Seccion titulo="2. Origen de los pollitos" marco>
          <Campo label="Incubadora o proveedor" ancho info="Elige una de la lista o escribe otra.">
            <input value={recepcion.proveedor} onChange={(e) => setRecepcion({ ...recepcion, proveedor: textoDe(e, "lugar", recepcion.proveedor) })} list="incubadoras" placeholder="Ej. San Fernando" required minLength={3} maxLength={LARGO_NOMBRE} autoComplete="off" />
            <datalist id="incubadoras">
              {catalogo?.incubadoras.map((n) => <option key={n} value={n} />)}
            </datalist>
          </Campo>
          <Campo label="Fecha de llegada" info="Hasta 70 días atrás.">
            <input type="date" value={fechaIngreso} min={haceDias(70)} max={hoy()} onChange={(e) => setFechaIngreso(e.target.value)} required />
          </Campo>
          <Campo label="N.º de guía de remisión" info="El número impreso en la guía.">
            <input value={recepcion.guia} onChange={(e) => setRecepcion({ ...recepcion, guia: limpiarTexto(e.target.value, "guia") })} placeholder="Ej. T001-004512" maxLength={LARGO_GUIA} />
          </Campo>
          {zona("GUIA", "Foto o PDF de la guía con la que llegaron los pollitos.", true)}
          {zona("ORIGEN", "Factura o boleta de la incubadora, si la tienes.")}
        </Seccion>
        {(catalogo?.vacunas_incubadora.length ?? 0) > 0 && (
          <Seccion titulo="3. Vacunas de la incubadora" marco>
            <div className="campo ancho">
              <span className="campo-label con-info">
                Vacunas que ya traen
                <Ayuda titulo="Vacunas de la incubadora" nota>
                  Marca las que figuran en la guía o en el certificado de la incubadora. Quedan registradas en Sanidad como aplicadas el
                  día de llegada, a la espera de la conformidad del veterinario.
                </Ayuda>
              </span>
              <div className="opciones-check">
                {catalogo?.vacunas_incubadora.map((v) => {
                  const marcada = vacunasIncubadora.includes(v.nombre);
                  return (
                    <label key={v.nombre} className={marcada ? "opcion-check marcada" : "opcion-check"}>
                      <input
                        type="checkbox"
                        checked={marcada}
                        onChange={() => setVacunasIncubadora(marcada ? vacunasIncubadora.filter((x) => x !== v.nombre) : [...vacunasIncubadora, v.nombre])}
                      />
                      <span><b>{v.nombre}</b><small>{v.via}</small></span>
                    </label>
                  );
                })}
              </div>
            </div>
            {zona("VACUNAS", "Certificado sanitario o de vacunación que entrega la incubadora.")}
          </Seccion>
        )}
        <Seccion titulo="4. Recepción" marco>
          <Campo label="Pollitos recibidos (según guía)" info={galpon ? `Capacidad de ${galpon.nombre}: ${num(galpon.capacidad)} aves.` : "Primero elige el galpón."}>
            <input type="number" min="1" max={galpon?.capacidad ?? 100000} value={recepcion.recibidos} onChange={(e) => {
              const valor = valorCampo(e);
              // Si bajan los recibidos, los descartados no pueden quedar iguales o mayores.
              const tope = Number(valor || 0) - 1;
              setRecepcion({ ...recepcion, recibidos: valor, descartes: valor && Number(recepcion.descartes) > tope ? String(Math.max(tope, 0)) : recepcion.descartes });
            }} placeholder={galpon ? `Hasta ${num(galpon.capacidad)}` : "Ej. 5000"} required />
          </Campo>
          <Campo label="Muertos o descartados al llegar">
            <input type="number" min="0" max={recibidos ? recibidos - 1 : galpon?.capacidad ?? 100000} value={recepcion.descartes} onChange={setR("descartes")} required />
          </Campo>
          <Campo label="Peso promedio al llegar (g)" info="Lo normal es 38–45 g por pollito.">
            <input type="number" min="25" max="70" step="0.1" value={recepcion.pesoLlegada} onChange={setR("pesoLlegada")} required />
          </Campo>
          <Campo
            label="Precio por pollito (S/)"
            info="Lo normal es entre S/ 1.50 y S/ 4.00. Se usa en el cierre económico."
            ayuda={recibidos && Number(recepcion.precio) > 0
              ? `Costo total: ${num(recibidos)} pollitos recibidos × S/ ${Number(recepcion.precio).toFixed(2)} = S/ ${num(costoEstimado, 2)}`
              : undefined}
          >
            <input type="number" min="0" max="10" step="0.01" value={recepcion.precio} onChange={setR("precio")} placeholder="Ej. 2.10" required />
          </Campo>
          <div className={galpon && alojados > galpon.capacidad ? "resumen-calculo campo ancho negativo" : "resumen-calculo campo ancho"}>
            <div><span>Recibidos</span><strong>{num(recibidos)}</strong></div>
            <div><span>Descartados</span><strong>{num(descartes)}</strong></div>
            <div className={galpon && alojados > galpon.capacidad ? "negativo" : "positivo"}>
              <span>Quedan en el galpón{galpon ? ` (máx. ${num(galpon.capacidad)})` : ""}</span>
              <strong>{num(alojados)}</strong>
            </div>
          </div>
          {zona("RECEPCION", "Fotos de los pollitos al llegar, del pesaje de la muestra y de los descartados.")}
        </Seccion>
        <Seccion titulo="5. Meta de la campaña" marco>
          <Campo
            label="Peso objetivo de venta (g)"
            ayuda={pesoEsperadoSaca ? (
              <>
                Un pollo {linea} de {recepcion.edadSaca} días debería pesar cerca de <b>{num(pesoEsperadoSaca)} g</b>.{" "}
                {Number(recepcion.pesoObjetivo) !== pesoEsperadoSaca && (
                  <button className="link-button" type="button" onClick={() => setRecepcion({ ...recepcion, pesoObjetivo: String(pesoEsperadoSaca) })}>
                    Usar este peso
                  </button>
                )}
              </>
            ) : undefined}
          >
            <input type="number" min="1000" max="5000" step="1" value={recepcion.pesoObjetivo} onChange={setR("pesoObjetivo")} required />
          </Campo>
          <Campo label="Edad de saca prevista (días)">
            <input type="number" min="21" max="70" value={recepcion.edadSaca} onChange={setR("edadSaca")} required />
          </Campo>
          <Campo label="Observaciones de la recepción" ancho info="Estado de los pollitos, temperatura del transporte, uniformidad…">
            <textarea rows={3} value={recepcion.observaciones} onChange={setR("observaciones")} />
          </Campo>
        </Seccion>
      </DrawerForm>

      <DrawerForm
        abierto={cerrando !== null}
        titulo="Cerrar lote"
        descripcion={cerrando ? `${cerrando.galpon} · ${cerrando.linea} · ingreso ${fecha(cerrando.fecha_ingreso)}. Después del cierre no se admiten nuevos registros.` : undefined}
        onCerrar={() => setCerrando(null)}
        onGuardar={cerrar}
        guardando={guardando}
        textoGuardar="Confirmar cierre"
        error={error}
        ancho="amplio"
        peligro
      >
        <Seccion titulo="Venta">
          <Campo label="Fecha de faena" ayuda="Día en que salieron las aves. Se usa para revisar la carencia de los tratamientos.">
            <input type="date" min={cerrando?.fecha_ingreso} max={hoy()} {...campoCierre("fecha")} required />
          </Campo>
          <Campo label="Aves vendidas" ayuda={vivas !== null ? `Aves vivas registradas: ${num(vivas)}.` : "Calculando aves vivas…"}>
            <input type="number" min="1" max={vivas ?? undefined} {...campoCierre("aves")} required />
          </Campo>
          <Campo label="Peso total vendido (kg)">
            <input type="number" min="0.01" max="600000" step="0.01" {...campoCierre("peso")} required />
          </Campo>
          <Campo label="Precio de venta por kg (S/)">
            <input type="number" min="0.01" max="50" step="0.01" {...campoCierre("precio")} required />
          </Campo>
        </Seccion>
        <Seccion titulo="Costos de la campaña (S/)">
          <Campo label="Pollitos"><input type="number" min="0" max="10000000" step="0.01" {...campoCierre("pollitos")} required /></Campo>
          <Campo label="Alimento"><input type="number" min="0" max="10000000" step="0.01" {...campoCierre("alimento")} required /></Campo>
          <Campo label="Sanidad"><input type="number" min="0" max="10000000" step="0.01" {...campoCierre("sanidad")} required /></Campo>
          <Campo label="Otros"><input type="number" min="0" max="10000000" step="0.01" {...campoCierre("otros")} required /></Campo>
        </Seccion>
        <Seccion titulo="Resultado estimado">
          <div className="resumen-calculo campo ancho">
            <div><span>Ingreso</span><strong>S/ {num(ingreso, 2)}</strong></div>
            <div><span>Costos</span><strong>S/ {num(costos, 2)}</strong></div>
            <div><span>Peso promedio por ave</span><strong>{pesoPromedio ? `${num(pesoPromedio)} g` : "—"}</strong></div>
            <div className={margen >= 0 ? "positivo" : "negativo"}><span>Margen</span><strong>S/ {num(margen, 2)}</strong></div>
          </div>
          <Campo label="Observaciones" ancho>
            <textarea rows={3} {...campoCierre("observaciones")} />
          </Campo>
        </Seccion>
      </DrawerForm>
      <EvidenciasLote lote={verEvidencias} puedeEditar={puedeGestionar} onCerrar={() => setVerEvidencias(null)} />
    </>
  );
}
