import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, fecha, hoyLocal, num, type Tratamiento, type Vacuna } from "../api";
import { useAuth } from "../auth";
import { Campo, Drawer, DrawerForm, Estado, Icon, PageHeader, Panel, Seccion, Tabs, Vacio, mensajeError, useToast } from "../components/ui";
import { useLote } from "../lote";
import { valorCampo } from "../textos";

type VacunaCatalogo = { nombre: string; via: string; dia: number; nota: string };
type Medicamento = { nombre: string; uso: string; dosis: string[]; vias: string[]; dias: number; carencia: number };
const TRAT_VACIO = { medicamento: "", dosis: "", via: "", inicio: hoyLocal(), dias: "", carencia: "", aves: "", diagnostico: "" };

/** Última fecha que se puede programar: 70 días después del ingreso. */
function finCampana(ingreso: string) {
  return diaDelLote(ingreso, 70);
}

/** Fecha de ingreso + días, en formato YYYY-MM-DD. */
function diaDelLote(ingreso: string, dias: number) {
  const [y, m, d] = ingreso.split("-").map(Number);
  const f = new Date(y, m - 1, d + dias);
  return `${f.getFullYear()}-${String(f.getMonth() + 1).padStart(2, "0")}-${String(f.getDate()).padStart(2, "0")}`;
}
type Revision = { tipo: "vacuna"; item: Vacuna } | { tipo: "tratamiento"; item: Tratamiento };

export default function Sanidad() {
  const { usuario } = useAuth();
  const { loteId, resumen } = useLote();
  const avisar = useToast();
  const [pestana, setPestana] = useState("tratamientos");
  const [vacunas, setVacunas] = useState<Vacuna[]>([]);
  const [tratamientos, setTratamientos] = useState<Tratamiento[]>([]);
  const [error, setError] = useState("");
  const [guardando, setGuardando] = useState(false);

  const [nuevoTrat, setNuevoTrat] = useState(false);
  const [trat, setTrat] = useState(TRAT_VACIO);
  const [catalogo, setCatalogo] = useState<{ vacunas: VacunaCatalogo[]; medicamentos: Medicamento[] }>({ vacunas: [], medicamentos: [] });
  const [nuevaVac, setNuevaVac] = useState(false);
  const [vac, setVac] = useState({ nombre: "", fecha: hoyLocal() });
  const [revision, setRevision] = useState<Revision | null>(null);
  const [aplicando, setAplicando] = useState<Vacuna | null>(null);
  const [aplicacion, setAplicacion] = useState({ fecha: hoyLocal(), nota: "" });
  const [nota, setNota] = useState("");
  const [iniciando, setIniciando] = useState<Tratamiento | null>(null);
  const [fechaInicio, setFechaInicio] = useState(hoyLocal());

  const lote = resumen?.lotes.find((l) => l.id === loteId);
  const activo = lote?.estado === "ACTIVO";
  const puedeCargar = (usuario?.rol === "PRODUCTOR" || usuario?.rol === "OPERARIO") && activo;
  const esVet = usuario?.rol === "VETERINARIO";
  const vetActivo = esVet && activo;
  const hoy = hoyLocal();
  const enSieteDias = (() => {
    const f = new Date();
    f.setDate(f.getDate() + 7);
    return `${f.getFullYear()}-${String(f.getMonth() + 1).padStart(2, "0")}-${String(f.getDate()).padStart(2, "0")}`;
  })();

  useEffect(() => {
    api<{ vacunas: VacunaCatalogo[]; medicamentos: Medicamento[] }>("/catalogo/sanidad").then(setCatalogo).catch(() => undefined);
  }, []);

  // Desde «Revisión de bajas» (posible brote): abre la receta con el diagnóstico ya escrito.
  const [parametros, setParametros] = useSearchParams();
  useEffect(() => {
    if (!parametros.get("indicar") || !vetActivo) return;
    setError("");
    setTrat({ ...TRAT_VACIO, inicio: hoyLocal(), diagnostico: parametros.get("diagnostico") ?? "" });
    setNuevoTrat(true);
    setPestana("tratamientos");
    setParametros({}, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vetActivo]);

  const producto = catalogo.medicamentos.find((m) => m.nombre === trat.medicamento) ?? null;
  const vacunaElegida = catalogo.vacunas.find((v) => v.nombre === vac.nombre) ?? null;

  function elegirMedicamento(nombre: string) {
    const m = catalogo.medicamentos.find((x) => x.nombre === nombre);
    setTrat({
      ...trat,
      medicamento: nombre,
      dosis: m?.dosis[0] ?? "",
      via: m?.vias[0] ?? "",
      dias: m ? String(m.dias) : "",
      carencia: m ? String(m.carencia) : "",
    });
  }

  function elegirVacuna(nombre: string) {
    const v = catalogo.vacunas.find((x) => x.nombre === nombre);
    // Propone la fecha según la edad recomendada; si ya pasó, deja hoy.
    const sugerida = v && lote ? diaDelLote(lote.fecha_ingreso, v.dia) : hoyLocal();
    setVac({ nombre, fecha: sugerida < hoyLocal() ? hoyLocal() : sugerida });
  }

  async function cargar() {
    if (!loteId) return;
    const data = await api<{ vacunas: Vacuna[]; tratamientos: Tratamiento[] }>(`/lotes/${loteId}/sanidad`);
    setVacunas(data.vacunas);
    setTratamientos(data.tratamientos);
  }

  useEffect(() => {
    cargar().catch((err) => avisar(mensajeError(err), "riesgo"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loteId]);

  async function enviar(accion: () => Promise<unknown>, exito: string, cerrar: () => void) {
    setError("");
    setGuardando(true);
    try {
      await accion();
      await cargar();
      cerrar();
      avisar(exito);
    } catch (err) {
      setError(mensajeError(err, "No se guardó"));
    } finally {
      setGuardando(false);
    }
  }

  function guardarTratamiento() {
    // El veterinario indica (receta); el personal registra lo que ya aplicó.
    return enviar(
      () =>
        api(esVet ? `/lotes/${loteId}/tratamientos/indicar` : `/lotes/${loteId}/tratamientos`, {
          method: "POST",
          body: JSON.stringify({
            medicamento: trat.medicamento,
            dosis: trat.dosis,
            via: trat.via,
            fecha_inicio: trat.inicio,
            dias_tratamiento: Number(trat.dias),
            dias_carencia: Number(trat.carencia),
            aves_tratadas: trat.aves.trim() ? Number(trat.aves) : null,
            ...(esVet ? { diagnostico: trat.diagnostico } : {}),
          }),
        }),
      esVet
        ? "Tratamiento indicado. El productor y el operario reciben el aviso para iniciarlo."
        : "Tratamiento registrado. La carencia ya corre y queda pendiente del veterinario.",
      () => {
        setNuevoTrat(false);
        setTrat({ ...TRAT_VACIO, inicio: hoyLocal() });
      },
    );
  }

  function guardarVacuna() {
    return enviar(
      () => api(`/lotes/${loteId}/sanidad`, { method: "POST", body: JSON.stringify({ nombre: vac.nombre, fecha_programada: vac.fecha }) }),
      esVet ? "Vacuna programada. El personal ya puede registrar la aplicación." : "Vacuna propuesta. Falta que el veterinario apruebe la fecha.",
      () => {
        setNuevaVac(false);
        setVac({ nombre: "", fecha: hoyLocal() });
      },
    );
  }

  function decidir(decision: "VALIDADA" | "OBSERVADA") {
    if (!revision) return;
    const ruta = revision.tipo === "vacuna" ? `/vacunas/${revision.item.id}/validar` : `/tratamientos/${revision.item.id}/validar`;
    const mensaje =
      decision === "OBSERVADA"
        ? revision.tipo === "tratamiento"
          ? "Tratamiento observado. La carencia sigue contando: el medicamento ya se aplicó."
          : "Vacuna observada."
        : revision.tipo === "vacuna" && revision.item.estado === "PENDIENTE"
          ? "Fecha aprobada. El personal ya puede registrar la aplicación."
          : "Conformidad registrada.";
    return enviar(
      () => api(ruta, { method: "POST", body: JSON.stringify({ decision, observacion: nota }) }),
      mensaje,
      () => setRevision(null),
    );
  }

  function abrirInicio(t: Tratamiento) {
    setError("");
    setFechaInicio(t.fecha_inicio <= hoyLocal() ? t.fecha_inicio : hoyLocal());
    setIniciando(t);
  }

  function guardarInicio() {
    if (!iniciando) return;
    return enviar(
      () => api(`/tratamientos/${iniciando.id}/iniciar`, { method: "POST", body: JSON.stringify({ fecha_inicio: fechaInicio }) }),
      "Tratamiento iniciado. Desde hoy corre la carencia.",
      () => setIniciando(null),
    );
  }

  function abrirTratamiento() {
    setError("");
    setTrat({ ...TRAT_VACIO, inicio: hoyLocal() });
    setNuevoTrat(true);
  }

  function abrirAplicacion(v: Vacuna) {
    setError("");
    setAplicacion({ fecha: v.fecha_programada <= hoyLocal() ? v.fecha_programada : hoyLocal(), nota: "" });
    setAplicando(v);
  }

  function guardarAplicacion() {
    if (!aplicando) return;
    return enviar(
      () =>
        api(`/vacunas/${aplicando.id}/aplicar`, {
          method: "POST",
          body: JSON.stringify({ fecha_aplicacion: aplicacion.fecha, nota: aplicacion.nota }),
        }),
      "Aplicación registrada. Queda pendiente la conformidad del veterinario.",
      () => setAplicando(null),
    );
  }

  /** Qué toca hacer con la vacuna según su etapa y el rol de quien mira. */
  function accionVacuna(v: Vacuna): { texto: string; hacer: () => void } {
    if (esVet && v.estado === "PENDIENTE") return { texto: "Aprobar fecha", hacer: () => revisar({ tipo: "vacuna", item: v }) };
    if (esVet && v.estado === "APLICADA") return { texto: "Dar conformidad", hacer: () => revisar({ tipo: "vacuna", item: v }) };
    if (puedeCargar && v.estado === "PROGRAMADA") return { texto: "Registrar aplicación", hacer: () => abrirAplicacion(v) };
    return { texto: "Ver detalle", hacer: () => revisar({ tipo: "vacuna", item: v }) };
  }

  function estadoVacuna(v: Vacuna) {
    const atrasada = v.fecha_programada <= hoy;
    if (v.estado === "PENDIENTE") return atrasada ? <Estado valor="VENCIDA" texto="Fecha sin aprobar" /> : <Estado valor="PENDIENTE" texto="Fecha por aprobar" />;
    if (v.estado === "PROGRAMADA") return atrasada ? <Estado valor="VENCIDA" texto="Por aplicar" /> : <Estado valor="PROGRAMADA" texto="Programada" />;
    if (v.estado === "APLICADA") return <Estado valor="APLICADA" texto="Aplicada · por revisar" />;
    if (v.estado === "VALIDADA") return <Estado valor="VALIDADA" texto="Conforme" />;
    return <Estado valor={v.estado} />;
  }

  function revisar(r: Revision) {
    setError("");
    setNota("");
    setRevision(r);
  }

  const porIniciar = tratamientos.filter((t) => t.estado === "INDICADO");
  const pendientesT = tratamientos.filter((t) => t.estado === "PENDIENTE").length;
  const pendientesV = vacunas.filter((v) => v.estado === "PENDIENTE" || v.estado === "APLICADA").length;
  const enCarencia = tratamientos.filter((t) => t.en_carencia);
  const puedeRevisar =
    esVet &&
    !!revision &&
    (revision.tipo === "tratamiento" ? revision.item.estado === "PENDIENTE" : ["PENDIENTE", "APLICADA"].includes(revision.item.estado));

  return (
    <>
      <PageHeader
        titulo="Vacunas y tratamientos"
        descripcion="Vacunas: el personal propone la fecha o la programa el veterinario; luego se registra la aplicación y el veterinario da su conformidad. Tratamientos: el veterinario puede indicarlos y el personal los inicia; el sistema cuenta la carencia hasta la faena."
        acciones={
          (puedeCargar || vetActivo) && (
            <>
              <button className="btn secondary" type="button" onClick={() => { setError(""); setNuevaVac(true); }}>
                <Icon name="mas" /> Programar vacuna
              </button>
              <button className="btn primario" type="button" onClick={abrirTratamiento}>
                <Icon name="mas" /> {esVet ? "Indicar tratamiento" : "Registrar tratamiento"}
              </button>
            </>
          )
        }
      />

      {porIniciar.length > 0 && (
        <div className="aviso info">
          <Icon name="sanidad" />
          <span>
            {esVet
              ? <>Indicaste {porIniciar.length} tratamiento(s) que el personal aún no inicia: <b>{porIniciar.map((t) => t.medicamento).join(", ")}</b>.</>
              : <>El veterinario indicó <b>{porIniciar.map((t) => `${t.medicamento} (${t.dosis})`).join(", ")}</b>. Pulsa <b>Iniciar</b> cuando empieces a darlo.</>}
          </span>
        </div>
      )}

      {enCarencia.length > 0 && (
        <div className="aviso alerta">
          <Icon name="aviso" />
          <span>
            Lote en carencia: no faenar hasta el <b>{fecha(enCarencia.map((t) => t.libre_faena).sort().slice(-1)[0])}</b>
            {" "}({enCarencia.map((t) => t.medicamento).join(", ")}).
          </span>
        </div>
      )}

      <Panel sinPadding>
        <div className="barra-lista">
          <Tabs
            valor={pestana}
            onCambio={setPestana}
            items={[
              { id: "tratamientos", label: "Tratamientos", cantidad: tratamientos.length },
              { id: "vacunas", label: "Vacunas", cantidad: vacunas.length },
            ]}
          />
          {esVet && (pendientesT + pendientesV > 0) && (
            <span className="muted">{pendientesT + pendientesV} registro(s) esperan tu revisión</span>
          )}
        </div>

        {pestana === "tratamientos" &&
          (tratamientos.length === 0 ? (
            <Vacio icono="sanidad" titulo="Sin tratamientos en este lote" texto="Cuando se aplique un medicamento, regístralo aquí para controlar la carencia." />
          ) : (
            <div className="tabla-wrap">
              <table>
                <thead>
                  <tr><th>Medicamento</th><th>Aplicación</th><th>Carencia</th><th>Estado</th><th /></tr>
                </thead>
                <tbody>
                  {tratamientos.map((t) => (
                    <tr key={t.id}>
                      <td className="celda-principal">
                        <strong>{t.medicamento}</strong>
                        <small>
                          {t.dosis} · {t.via} · {t.aves_tratadas ? `${num(t.aves_tratadas)} aves` : "todo el lote"}
                          {t.indicado ? " · indicado por el veterinario" : ""}
                        </small>
                      </td>
                      <td>
                        {t.estado === "INDICADO"
                          ? <span className="muted">Desde el {fecha(t.fecha_inicio)} · {t.dias_tratamiento} días</span>
                          : <>{fecha(t.fecha_inicio)} – {fecha(t.ultima_dosis)}</>}
                      </td>
                      <td>
                        {t.estado === "INDICADO"
                          ? <span className="muted">Corre al iniciar</span>
                          : t.en_carencia
                            ? <Estado valor="VENCIDA" texto={`Hasta ${fecha(t.libre_faena)}`} />
                            : <Estado valor="ACTIVO" texto={`Libre desde ${fecha(t.libre_faena)}`} />}
                      </td>
                      <td>
                        {t.estado === "INDICADO"
                          ? <Estado valor="INDICADO" texto="Indicado · por iniciar" />
                          : t.estado === "VALIDADA" ? <Estado valor="VALIDADA" texto="Conforme" /> : <Estado valor={t.estado} />}
                      </td>
                      <td className="acciones">
                        {puedeCargar && t.estado === "INDICADO" ? (
                          <button className="link-button" type="button" onClick={() => abrirInicio(t)}>Iniciar</button>
                        ) : (
                          <button className="link-button" type="button" onClick={() => revisar({ tipo: "tratamiento", item: t })}>
                            {esVet && t.estado === "PENDIENTE" ? "Revisar" : "Ver detalle"}
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}

        {pestana === "vacunas" &&
          (vacunas.length === 0 ? (
            <Vacio icono="sanidad" titulo="Sin vacunas programadas" texto="Programa el calendario del lote: Newcastle, bronquitis infecciosa, Gumboro…" />
          ) : (
            <div className="tabla-wrap">
              <table>
                <thead>
                  <tr><th>Vacuna</th><th>Programada</th><th>Aplicada</th><th>Estado</th><th /></tr>
                </thead>
                <tbody>
                  {vacunas.map((v) => {
                    const accion = accionVacuna(v);
                    return (
                      <tr key={v.id}>
                        <td className="celda-principal">
                          <strong>{v.nombre}</strong>
                          {v.observacion && <small>{v.observacion}</small>}
                        </td>
                        <td>{fecha(v.fecha_programada)}</td>
                        <td>{v.fecha_aplicacion ? fecha(v.fecha_aplicacion) : <span className="muted">—</span>}</td>
                        <td>{estadoVacuna(v)}</td>
                        <td className="acciones">
                          <button className="link-button" type="button" onClick={accion.hacer}>{accion.texto}</button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ))}
      </Panel>

      <DrawerForm
        abierto={nuevoTrat}
        titulo={esVet ? "Indicar tratamiento" : "Registrar tratamiento"}
        descripcion={esVet
          ? "Receta para el lote: el productor o el operario la inician y la suministran. La carencia corre desde que la inicien."
          : "Los días de carencia son los que indica el frasco, contados desde la última dosis."}
        onCerrar={() => setNuevoTrat(false)}
        onGuardar={guardarTratamiento}
        guardando={guardando}
        textoGuardar={esVet ? "Indicar tratamiento" : "Registrar tratamiento"}
        error={error}
      >
        {esVet && (
          <Seccion titulo="Diagnóstico">
            <Campo label="Motivo de la indicación" ancho ayuda="Lo verán el productor y el operario junto con la receta.">
              <textarea
                rows={3}
                minLength={5}
                maxLength={500}
                required
                value={trat.diagnostico}
                onChange={(e) => setTrat({ ...trat, diagnostico: e.target.value })}
                placeholder="Ej. Colibacilosis: mortalidad alta y lesiones en la necropsia"
              />
            </Campo>
          </Seccion>
        )}
        <Seccion titulo="Medicamento">
          <Campo label="Nombre" ancho ayuda={producto ? `Uso: ${producto.uso}.` : "Elige el producto aplicado."}>
            <select value={trat.medicamento} onChange={(e) => elegirMedicamento(e.target.value)} required>
              <option value="" disabled>Seleccionar medicamento…</option>
              {catalogo.medicamentos.map((m) => <option key={m.nombre} value={m.nombre}>{m.nombre}</option>)}
            </select>
          </Campo>
          <Campo label="Dosis">
            <select value={trat.dosis} onChange={(e) => setTrat({ ...trat, dosis: e.target.value })} disabled={!producto} required>
              {!producto && <option value="">Primero elige el medicamento</option>}
              {producto?.dosis.map((d) => <option key={d}>{d}</option>)}
            </select>
          </Campo>
          <Campo label="Vía">
            <select value={trat.via} onChange={(e) => setTrat({ ...trat, via: e.target.value })} disabled={!producto} required>
              {!producto && <option value="">—</option>}
              {producto?.vias.map((v) => <option key={v}>{v}</option>)}
            </select>
          </Campo>
        </Seccion>
        <Seccion titulo="Aplicación y carencia">
          <Campo label={esVet ? "Iniciar desde" : "Primer día"} ayuda={esVet ? "Hoy o dentro de los próximos 7 días." : undefined}>
            <input
              type="date"
              min={esVet ? hoy : lote?.fecha_ingreso}
              max={esVet ? enSieteDias : hoyLocal()}
              value={trat.inicio}
              onChange={(e) => setTrat({ ...trat, inicio: e.target.value })}
              required
            />
          </Campo>
          <Campo label="Días de tratamiento">
            <input type="number" min="1" max="30" value={trat.dias} onChange={(e) => setTrat({ ...trat, dias: valorCampo(e) })} required />
          </Campo>
          <Campo label="Días de carencia" ayuda={producto ? `Sugerido: ${producto.carencia} días. Confirma con la etiqueta del frasco.` : "Según la etiqueta del producto."}>
            <input type="number" min="0" max="60" value={trat.carencia} onChange={(e) => setTrat({ ...trat, carencia: valorCampo(e) })} required />
          </Campo>
          <Campo label="Aves tratadas" ayuda="Vacío = todo el lote.">
            <input type="number" min="1" max="100000" value={trat.aves} onChange={(e) => setTrat({ ...trat, aves: valorCampo(e) })} />
          </Campo>
        </Seccion>
      </DrawerForm>

      <DrawerForm
        abierto={nuevaVac}
        titulo="Programar vacuna"
        descripcion={esVet
          ? "Queda programada y aprobada. El productor o el operario registran la aplicación."
          : "Propón la fecha. El veterinario la aprueba y después se registra la aplicación."}
        onCerrar={() => setNuevaVac(false)}
        onGuardar={guardarVacuna}
        guardando={guardando}
        textoGuardar="Programar vacuna"
        error={error}
      >
        <Seccion titulo="Vacuna">
          <Campo
            label="Nombre"
            ancho
            ayuda={vacunaElegida ? `Vía: ${vacunaElegida.via} · edad habitual: día ${vacunaElegida.dia}. ${vacunaElegida.nota}` : "Calendario habitual del pollo de engorde."}
          >
            <select value={vac.nombre} onChange={(e) => elegirVacuna(e.target.value)} required>
              <option value="" disabled>Seleccionar vacuna…</option>
              {catalogo.vacunas.map((v) => (
                <option key={v.nombre} value={v.nombre}>{v.nombre} — día {v.dia}</option>
              ))}
            </select>
          </Campo>
          <Campo label="Fecha programada" ancho ayuda={vacunaElegida ? "Propuesta según la edad del lote; puedes cambiarla." : undefined}>
            <input type="date" min={lote?.fecha_ingreso} max={lote ? finCampana(lote.fecha_ingreso) : undefined} value={vac.fecha} onChange={(e) => setVac({ ...vac, fecha: e.target.value })} required />
          </Campo>
        </Seccion>
      </DrawerForm>

      <DrawerForm
        abierto={iniciando !== null}
        titulo="Iniciar tratamiento"
        descripcion={iniciando ? `${iniciando.medicamento} · ${iniciando.dosis} · ${iniciando.via} · ${iniciando.dias_tratamiento} días` : undefined}
        onCerrar={() => setIniciando(null)}
        onGuardar={guardarInicio}
        guardando={guardando}
        textoGuardar="Iniciar tratamiento"
        error={error}
      >
        {iniciando && (
          <dl className="ficha">
            <dt>Indicado por</dt><dd>Médico veterinario</dd>
            <dt>Diagnóstico</dt><dd>{iniciando.diagnostico}</dd>
            <dt>Aves</dt><dd>{iniciando.aves_tratadas ? num(iniciando.aves_tratadas) : "Todo el lote"}</dd>
            <dt>Carencia</dt><dd>{iniciando.dias_carencia} días después de la última dosis</dd>
          </dl>
        )}
        <Seccion titulo="Inicio">
          <Campo label="Fecha en que empezaste a darlo" ancho ayuda="Desde esta fecha se cuentan los días de tratamiento y la carencia.">
            <input type="date" value={fechaInicio} min={lote?.fecha_ingreso} max={hoyLocal()} onChange={(e) => setFechaInicio(e.target.value)} required />
          </Campo>
        </Seccion>
      </DrawerForm>

      <DrawerForm
        abierto={aplicando !== null}
        titulo="Registrar aplicación"
        descripcion={aplicando ? `${aplicando.nombre} · programada para el ${fecha(aplicando.fecha_programada)}` : undefined}
        onCerrar={() => setAplicando(null)}
        onGuardar={guardarAplicacion}
        guardando={guardando}
        textoGuardar="Registrar aplicación"
        error={error}
      >
        <Seccion titulo="Aplicación">
          <Campo label="Fecha en que se aplicó" ancho>
            <input type="date" value={aplicacion.fecha} max={hoyLocal()} min={lote?.fecha_ingreso} onChange={(e) => setAplicacion({ ...aplicacion, fecha: e.target.value })} required />
          </Campo>
          <Campo label="Nota" ancho ayuda="Opcional: lote o serie del frasco, aves vacunadas, incidencias.">
            <textarea rows={3} maxLength={500} value={aplicacion.nota} onChange={(e) => setAplicacion({ ...aplicacion, nota: e.target.value })} />
          </Campo>
        </Seccion>
      </DrawerForm>

      <Drawer
        abierto={revision !== null}
        titulo={revision ? (revision.tipo === "vacuna" ? revision.item.nombre : revision.item.medicamento) : ""}
        descripcion={revision?.tipo === "vacuna" ? "Vacuna del lote" : "Tratamiento del lote"}
        onCerrar={() => setRevision(null)}
        pie={
          puedeRevisar ? (
            <>
              <button className="btn secondary" type="button" disabled={guardando} onClick={() => decidir("OBSERVADA")}>Observar</button>
              <button className="btn" type="button" disabled={guardando} onClick={() => decidir("VALIDADA")}>
                {revision?.tipo === "vacuna" ? (revision.item.estado === "PENDIENTE" ? "Aprobar fecha" : "Dar conformidad") : "Validar"}
              </button>
            </>
          ) : (
            <button className="btn secondary" type="button" onClick={() => setRevision(null)}>Cerrar</button>
          )
        }
      >
        {error && <div className="aviso riesgo">{error}</div>}
        {revision?.tipo === "tratamiento" && (
          <dl className="ficha">
            <dt>Estado</dt><dd><Estado valor={revision.item.estado} /></dd>
            <dt>Origen</dt><dd>{revision.item.indicado ? "Indicado por el veterinario" : "Registrado por el personal"}</dd>
            <dt>Dosis y vía</dt><dd>{revision.item.dosis} · {revision.item.via}</dd>
            <dt>Aves</dt><dd>{revision.item.aves_tratadas ? num(revision.item.aves_tratadas) : "Todo el lote"}</dd>
            <dt>Aplicación</dt><dd>{fecha(revision.item.fecha_inicio)} al {fecha(revision.item.ultima_dosis)} ({revision.item.dias_tratamiento} días)</dd>
            <dt>Carencia</dt><dd>{revision.item.dias_carencia} días · libre para faena desde el {fecha(revision.item.libre_faena)}</dd>
            {revision.item.diagnostico && (<><dt>Diagnóstico</dt><dd>{revision.item.diagnostico}</dd></>)}
          </dl>
        )}
        {revision?.tipo === "vacuna" && (
          <dl className="ficha">
            <dt>Estado</dt><dd><Estado valor={revision.item.estado} /></dd>
            <dt>Programada</dt><dd>{fecha(revision.item.fecha_programada)}</dd>
            <dt>Aplicada</dt><dd>{revision.item.fecha_aplicacion ? fecha(revision.item.fecha_aplicacion) : "Todavía no"}</dd>
            {revision.item.nota_aplicacion && (<><dt>Nota del galpón</dt><dd>{revision.item.nota_aplicacion}</dd></>)}
            {revision.item.observacion && (<><dt>Observación del veterinario</dt><dd>{revision.item.observacion}</dd></>)}
          </dl>
        )}
        {puedeRevisar && revision && (
          <Campo label={revision.tipo === "vacuna" ? "Observación" : "Diagnóstico o indicación"} ayuda="Queda registrado con tu nombre.">
            <textarea
              rows={4}
              value={nota}
              onChange={(e) => setNota(e.target.value)}
              placeholder={revision.tipo === "vacuna" && revision.item.estado === "PENDIENTE" ? "Ej. Fecha adecuada para la edad del lote" : "Ej. Aplicación conforme"}
            />
          </Campo>
        )}
      </Drawer>
    </>
  );
}
