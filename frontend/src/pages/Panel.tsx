import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, fecha, num, type Panel } from "../api";
import { useAuth } from "../auth";
import { Ayuda, Campo, DrawerForm, Icon, PageHeader, Panel as Caja, Seccion, Vacio, mensajeError, useToast } from "../components/ui";
import { useLote } from "../lote";

export default function PanelPage() {
  const { usuario } = useAuth();
  const { loteId } = useLote();
  const avisar = useToast();
  const [panel, setPanel] = useState<Panel | null>(null);
  const [error, setError] = useState("");
  const [clima, setClima] = useState(false);
  const [temp, setTemp] = useState("");
  const [humedad, setHumedad] = useState("");
  const [guardando, setGuardando] = useState(false);

  async function cargar() {
    if (!loteId) return;
    setPanel(await api<Panel>(`/lotes/${loteId}/panel`));
  }

  useEffect(() => {
    cargar().catch((err) => setError(mensajeError(err)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loteId]);

  async function guardarClima() {
    if (!loteId) return;
    setError("");
    setGuardando(true);
    try {
      const data = await api<{ alertas: { mensaje: string }[] }>(`/lotes/${loteId}/clima`, {
        method: "POST",
        body: JSON.stringify({ temperatura: Number(temp), humedad: Number(humedad) }),
      });
      setClima(false);
      setTemp("");
      setHumedad("");
      avisar(data.alertas.length ? data.alertas[0].mensaje : "Lectura guardada. El galpón sigue dentro del rango.", data.alertas.length ? "riesgo" : "ok");
      await cargar();
    } catch (err) {
      setError(mensajeError(err, "No se guardó la lectura"));
    } finally {
      setGuardando(false);
    }
  }

  if (!panel) return <p className="muted">{error || "Cargando el lote…"}</p>;
  const rol = usuario?.rol ?? "";
  const activo = panel.lote.estado === "ACTIVO";
  const puedeClima = activo && ["PRODUCTOR", "OPERATIVO", "ADMIN"].includes(rol);
  const puedeRegistrar = activo && ["PRODUCTOR", "OPERATIVO"].includes(rol);
  // El último pesaje se compara con la curva del día en que se pesó, no con la de hoy.
  const pesaje = [...panel.serie].reverse().find((p) => p.peso != null) ?? null;
  const diferencia = pesaje?.peso ? (pesaje.peso / pesaje.esperado - 1) * 100 : 0;
  const pesoBajo = pesaje !== null && diferencia < -10;
  const diasSinPesar = pesaje ? panel.dia_vida - pesaje.dia : null;
  const atencion = panel.carencias.length + panel.vacunas_vencidas.length;

  return (
    <>
      <PageHeader
        eyebrow={`${panel.lote.galpon} · ${panel.lote.linea}`}
        titulo={`Día ${panel.dia_vida}${activo ? "" : " · lote cerrado"}`}
        descripcion={[
          `${num(panel.lote.poblacion_inicial)} pollitos${panel.lote.sexo ? ` ${panel.lote.sexo.toLowerCase()}` : ""}`,
          `ingreso ${fecha(panel.lote.fecha_ingreso)}`,
          panel.lote.proveedor ? `origen ${panel.lote.proveedor}` : null,
          panel.lote.edad_saca_dias ? `saca prevista día ${panel.lote.edad_saca_dias} (${num(panel.lote.peso_objetivo_g)} g)` : null,
        ].filter(Boolean).join(" · ")}
        acciones={
          puedeRegistrar && (
            <Link className="btn primario" to="/registro"><Icon name="mas" /> Registrar el día</Link>
          )
        }
      />

      <div className="kpis">
        <article className="kpi">
          <span className="kpi-icono"><Icon name="ave" /></span>
          <div>
            <span>
              Aves vivas
              <Ayuda titulo="Aves vivas">
                Pollitos que ingresaron al galpón menos todas las bajas anotadas en el registro diario.
              </Ayuda>
            </span>
            <strong>{num(panel.aves_vivas)}</strong>
            <em>{num(panel.muertes)} bajas desde el ingreso</em>
          </div>
        </article>
        <article className={panel.mortalidad_acumulada > 4 ? "kpi riesgo" : "kpi"}>
          <span className="kpi-icono"><Icon name="aviso" /></span>
          <div>
            <span>
              Mortalidad acumulada
              <Ayuda titulo="Mortalidad acumulada">
                Porcentaje de pollitos que murieron desde el ingreso. En engorde lo habitual es terminar la campaña
                cerca de <b>4–5 %</b>. Además, si en un solo día mueren más de <b>{panel.umbral_mortalidad} aves</b>,
                el sistema avisa al veterinario.
              </Ayuda>
            </span>
            <strong>{num(panel.mortalidad_acumulada, 2)}%</strong>
            <em>alerta si mueren más de {panel.umbral_mortalidad} en un día</em>
          </div>
        </article>
        <article className={pesoBajo ? "kpi riesgo" : "kpi"}>
          <span className="kpi-icono"><Icon name="peso" /></span>
          <div>
            <span>
              Peso promedio por ave
              <Ayuda titulo="Peso promedio por ave">
                Se pesa un grupo de pollos del galpón (por ejemplo 50), se suma su peso y se divide entre la cantidad.
                Ese promedio se compara con lo que debería pesar un pollo <b>{panel.lote.linea}</b> de la misma edad
                según la guía de la línea genética.
              </Ayuda>
            </span>
            <strong>{pesaje ? `${num(pesaje.peso ?? 0)} g` : "—"}</strong>
            <em>
              {pesaje
                ? `día ${pesaje.dia}: esperado ${num(pesaje.esperado)} g (${diferencia >= 0 ? "+" : ""}${num(diferencia)} %)`
                : "todavía no hay pesajes"}
            </em>
          </div>
        </article>
        <article className="kpi acento">
          <span className="kpi-icono"><Icon name="grafico" /></span>
          <div>
            <span>
              Conversión alimenticia
              <Ayuda titulo="Conversión alimenticia (FCR)">
                Cuántos <b>kg de alimento</b> se necesitaron para que el lote gane <b>1 kg de peso</b>. Por ejemplo,
                1,50 significa 1,5 kg de alimento por cada kilo de pollo. <b>Mientras más bajo, mejor</b>: el alimento
                se está aprovechando.
              </Ayuda>
            </span>
            <strong>{panel.fcr ?? "—"}</strong>
            <em>
              {panel.epef ? (
                <>
                  Eficiencia (EPEF) {num(panel.epef)}
                  <Ayuda titulo="Eficiencia productiva (EPEF)">
                    Un solo número que resume el lote: junta cuántas aves sobreviven, cuánto pesan, su edad y la
                    conversión. <b>Mientras más alto, mejor</b>. Se usa sobre todo al cierre: más de <b>300</b> se
                    considera un buen resultado.
                  </Ayuda>
                </>
              ) : (
                "aparece con los primeros registros"
              )}
            </em>
          </div>
        </article>
      </div>
      {diasSinPesar !== null && diasSinPesar > 2 && activo && (
        <div className="aviso alerta">
          <Icon name="aviso" />
          <span>
            El último pesaje fue hace <b>{diasSinPesar} días</b> (día {pesaje?.dia}). Hoy, día {panel.dia_vida}, la curva
            espera <b>{num(panel.peso_esperado_g)} g</b>. Registra el día para mantener el seguimiento al día.
          </span>
        </div>
      )}

      <div className="rejilla dos">
        <Caja
          titulo={
            <>
              Peso del lote frente a lo esperado
              <Ayuda titulo="¿Cómo leer este gráfico?">
                <b>Abajo</b> está la edad del lote en días desde que llegaron los pollitos. <b>A la izquierda</b>, el
                peso promedio de un pollo en gramos. La <b>línea</b> es lo que debería pesar un pollo {panel.lote.linea}
                cada día; cada <b>punto</b> es un pesaje del registro diario. Si los puntos quedan por debajo de la
                línea, el lote va atrasado. Pasa el mouse sobre un día para ver el detalle.
              </Ayuda>
            </>
          }
          descripcion={`Ganancia promedio ${num(panel.ganancia_diaria_g, 1)} g por día`}
          acciones={
            <div className="legend">
              <span><i className="swatch curve" />Esperado ({panel.lote.linea})</span>
              <span><i className="swatch real" />Pesaje registrado</span>
            </div>
          }
        >
          <Chart serie={panel.serie} ingreso={panel.lote.fecha_ingreso} linea={panel.lote.linea} />
        </Caja>

        <div className="rejilla">
          <Caja titulo="Atención" descripcion={atencion ? `${atencion} punto(s) por revisar` : "Sin pendientes sanitarios"}>
            {atencion === 0 ? (
              <p className="muted" style={{ margin: 0 }}>No hay carencias activas ni vacunas vencidas.</p>
            ) : (
              <div className="lista-avisos">
                {panel.carencias.map((c) => (
                  <div className="aviso alerta" key={`c${c.id}`}>
                    <Icon name="sanidad" />
                    <span><b>{c.medicamento}</b> en carencia: no faenar hasta el {fecha(c.libre_faena)} ({c.dias_restantes} d).</span>
                  </div>
                ))}
                {panel.vacunas_vencidas.map((v) => (
                  <div className="aviso riesgo" key={`v${v.id}`}>
                    <Icon name="aviso" />
                    <span><b>{v.nombre}</b> vencida desde el {fecha(v.fecha_programada)}{v.dias_atraso > 0 ? ` (${v.dias_atraso} d)` : ""}.</span>
                  </div>
                ))}
                <Link to="/sanidad">Ir a vacunas y tratamientos</Link>
              </div>
            )}
          </Caja>

          <Caja
            titulo="Clima del galpón"
            descripcion={`Rango de hoy ${num(panel.temp_min)}–${num(panel.temp_max)} °C · humedad 50–70 %`}
            acciones={puedeClima && <button className="btn small secondary" type="button" onClick={() => { setError(""); setClima(true); }}><Icon name="mas" size={15} /> Lectura</button>}
          >
            {panel.lectura ? (
              <>
                <div className="clima-actual">
                  <div><strong>{panel.lectura.temperatura.toFixed(1)} °C</strong><span>temperatura</span></div>
                  <div><strong>{panel.lectura.humedad.toFixed(0)} %</strong><span>humedad</span></div>
                </div>
                <p className="muted" style={{ margin: 0, fontSize: 13 }}>Última lectura: {fecha(panel.lectura.fecha_hora)} {panel.lectura.fecha_hora.slice(11, 16)}</p>
              </>
            ) : (
              <p className="muted" style={{ margin: 0 }}>Todavía no hay lecturas del galpón.</p>
            )}
          </Caja>
        </div>
      </div>

      <Caja
        className="panel-separado"
        titulo="Últimos días"
        descripcion={`Alimento acumulado ${num(panel.alimento_kg)} kg · ${panel.alertas_abiertas} alerta(s) abierta(s)`}
        acciones={<Link className="btn small secondary" to="/alertas">Ver alertas</Link>}
        sinPadding
      >
        {panel.registros.length === 0 ? (
          <Vacio icono="registro" titulo="Aún no hay registros diarios" texto="El operativo o el productor anota bajas, consumo y peso cada día." />
        ) : (
          <div className="tabla-wrap">
            <table>
              <thead>
                <tr><th>Fecha</th><th>Bajas</th><th>Alimento (kg)</th><th>Agua (L)</th><th>Peso (g)</th></tr>
              </thead>
              <tbody>
                {panel.registros.map((row) => (
                  <tr key={row.id}>
                    <td>{fecha(row.fecha)}</td>
                    <td className="num">{row.mortalidad > panel.umbral_mortalidad ? <b style={{ color: "var(--riesgo)" }}>{row.mortalidad}</b> : row.mortalidad}</td>
                    <td className="num">{num(row.alimento_kg, 1)}</td>
                    <td className="num">{num(row.agua_l, 1)}</td>
                    <td className="num">{num(row.peso_muestra_g)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Caja>

      <DrawerForm
        abierto={clima}
        titulo="Registrar lectura del galpón"
        descripcion={`Rango esperado para el día ${panel.dia_vida}: ${num(panel.temp_min)}–${num(panel.temp_max)} °C y 50–70 % de humedad.`}
        onCerrar={() => setClima(false)}
        onGuardar={guardarClima}
        guardando={guardando}
        textoGuardar="Guardar lectura"
        error={error}
      >
        <Seccion titulo="Lectura">
          <Campo label="Temperatura (°C)">
            <input type="number" step="0.1" min="-10" max="50" value={temp} onChange={(e) => setTemp(e.target.value)} required />
          </Campo>
          <Campo label="Humedad (%)">
            <input type="number" step="1" min="0" max="100" value={humedad} onChange={(e) => setHumedad(e.target.value)} required />
          </Campo>
        </Seccion>
      </DrawerForm>
    </>
  );
}

function sumarDias(iso: string, dias: number) {
  const [y, m, d] = iso.split("-").map(Number);
  const f = new Date(y, m - 1, d + dias);
  return `${String(f.getDate()).padStart(2, "0")}/${String(f.getMonth() + 1).padStart(2, "0")}/${f.getFullYear()}`;
}

function Chart({ serie, ingreso, linea }: { serie: Panel["serie"]; ingreso: string; linea: string }) {
  const [activo, setActivo] = useState<number | null>(null);
  const w = 680;
  const h = 280;
  const izq = 58;
  const der = 14;
  const arr = 14;
  const abj = 46;
  const maxDia = Math.max(...serie.map((p) => p.dia), 7);
  const tope = Math.max(...serie.map((p) => Math.max(p.esperado, p.peso ?? 0)), 200);
  const paso = tope > 2000 ? 500 : tope > 800 ? 250 : 100;
  const maxPeso = Math.ceil(tope / paso) * paso;
  const x = (dia: number) => izq + (dia / maxDia) * (w - izq - der);
  const y = (peso: number) => h - abj - (peso / maxPeso) * (h - arr - abj);
  const curva = serie.map((p) => `${x(p.dia)},${y(p.esperado)}`).join(" ");
  const reales = serie.filter((p) => p.peso != null);
  const marcas = Array.from({ length: maxPeso / paso + 1 }, (_, i) => i * paso);
  const dias = Array.from({ length: Math.floor(maxDia / 7) + 1 }, (_, i) => i * 7);
  const punto = activo !== null ? serie.find((p) => p.dia === activo) ?? null : null;

  function mover(e: React.PointerEvent<SVGSVGElement>) {
    const caja = e.currentTarget.getBoundingClientRect();
    const svgX = ((e.clientX - caja.left) / caja.width) * w;
    const dia = Math.round(((svgX - izq) / (w - izq - der)) * maxDia);
    setActivo(Math.min(Math.max(dia, 0), maxDia));
  }

  return (
    <div className="chart-wrap">
      <svg
        className="chart"
        viewBox={`0 0 ${w} ${h}`}
        role="img"
        aria-label={`Peso promedio por ave registrado frente a la curva ${linea}`}
        onPointerMove={mover}
        onPointerDown={mover}
        onPointerLeave={() => setActivo(null)}
      >
        {marcas.map((m) => (
          <g key={m}>
            <line x1={izq} x2={w - der} y1={y(m)} y2={y(m)} stroke="#eef1ea" />
            <text x={izq - 8} y={y(m) + 4} textAnchor="end">{num(m)}</text>
          </g>
        ))}
        {dias.map((d) => (
          <text key={d} x={x(d)} y={h - abj + 18} textAnchor="middle">{d}</text>
        ))}
        <text className="eje" x={(izq + w - der) / 2} y={h - 6} textAnchor="middle">Edad del lote (días desde el ingreso)</text>
        <text className="eje" transform={`translate(13 ${(arr + h - abj) / 2}) rotate(-90)`} textAnchor="middle">Peso por ave (g)</text>
        <polyline fill="none" stroke="#b9c8bd" strokeWidth="2.5" strokeLinejoin="round" points={curva} />
        {punto && <line x1={x(punto.dia)} x2={x(punto.dia)} y1={arr} y2={h - abj} stroke="#c9d2c8" strokeDasharray="4 4" />}
        {punto && <circle cx={x(punto.dia)} cy={y(punto.esperado)} r="4" fill="#fffef9" stroke="#8fa597" strokeWidth="2" />}
        {reales.map((p) => (
          <circle key={p.dia} cx={x(p.dia)} cy={y(p.peso!)} r={activo === p.dia ? 6 : 3.8} fill="#287354" stroke="#fffef9" strokeWidth="1.5" />
        ))}
      </svg>
      {punto && (
        <div
          className="chart-tip"
          style={{ left: `${(x(punto.dia) / w) * 100}%`, transform: `translateX(${punto.dia > maxDia * 0.6 ? "-105%" : "5%"})` }}
        >
          <strong>Día {punto.dia} · {sumarDias(ingreso, punto.dia)}</strong>
          <span>Esperado: <b>{num(punto.esperado)} g</b></span>
          {punto.peso != null ? (
            <>
              <span>Pesaje: <b>{num(punto.peso)} g</b> ({punto.peso >= punto.esperado ? "+" : ""}{num((punto.peso / punto.esperado - 1) * 100)} %)</span>
              {punto.mortalidad != null && <span>Bajas ese día: <b>{punto.mortalidad}</b></span>}
            </>
          ) : (
            <span className="muted-claro">Sin pesaje ese día</span>
          )}
        </div>
      )}
    </div>
  );
}
