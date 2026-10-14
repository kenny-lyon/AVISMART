import { useEffect, useState } from "react";
import { api, fecha, hoyLocal, num, type Tratamiento, type Vacuna } from "../api";
import { useAuth } from "../auth";
import { Campo, Drawer, DrawerForm, Estado, Icon, PageHeader, Panel, Seccion, Tabs, Vacio, mensajeError, useToast } from "../components/ui";
import { useLote } from "../lote";

type VacunaCatalogo = { nombre: string; via: string; dia: number; nota: string };
type Medicamento = { nombre: string; uso: string; dosis: string[]; vias: string[]; dias: number; carencia: number };
const TRAT_VACIO = { medicamento: "", dosis: "", via: "", inicio: hoyLocal(), dias: "", carencia: "", aves: "" };

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
  const [nota, setNota] = useState("");

  const lote = resumen?.lotes.find((l) => l.id === loteId);
  const activo = lote?.estado === "ACTIVO";
  const puedeCargar = (usuario?.rol === "PRODUCTOR" || usuario?.rol === "OPERATIVO") && activo;
  const esVet = usuario?.rol === "VETERINARIO";
  const hoy = hoyLocal();

  useEffect(() => {
    api<{ vacunas: VacunaCatalogo[]; medicamentos: Medicamento[] }>("/catalogo/sanidad").then(setCatalogo).catch(() => undefined);
  }, []);

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
    return enviar(
      () =>
        api(`/lotes/${loteId}/tratamientos`, {
          method: "POST",
          body: JSON.stringify({
            medicamento: trat.medicamento,
            dosis: trat.dosis,
            via: trat.via,
            fecha_inicio: trat.inicio,
            dias_tratamiento: Number(trat.dias),
            dias_carencia: Number(trat.carencia),
            aves_tratadas: trat.aves.trim() ? Number(trat.aves) : null,
          }),
        }),
      "Tratamiento registrado. La carencia ya corre y queda pendiente del veterinario.",
      () => {
        setNuevoTrat(false);
        setTrat({ ...TRAT_VACIO, inicio: hoyLocal() });
      },
    );
  }

  function guardarVacuna() {
    return enviar(
      () => api(`/lotes/${loteId}/sanidad`, { method: "POST", body: JSON.stringify({ nombre: vac.nombre, fecha_programada: vac.fecha }) }),
      "Vacuna programada. Queda pendiente de validación del veterinario.",
      () => {
        setNuevaVac(false);
        setVac({ nombre: "", fecha: hoyLocal() });
      },
    );
  }

  function decidir(decision: "VALIDADA" | "OBSERVADA") {
    if (!revision) return;
    const ruta = revision.tipo === "vacuna" ? `/vacunas/${revision.item.id}/validar` : `/tratamientos/${revision.item.id}/validar`;
    return enviar(
      () => api(ruta, { method: "POST", body: JSON.stringify({ decision, observacion: nota }) }),
      decision === "VALIDADA" ? "Registro validado." : "Registro observado.",
      () => setRevision(null),
    );
  }

  function revisar(r: Revision) {
    setError("");
    setNota("");
    setRevision(r);
  }

  const pendientesT = tratamientos.filter((t) => t.estado === "PENDIENTE").length;
  const pendientesV = vacunas.filter((v) => v.estado === "PENDIENTE").length;
  const enCarencia = tratamientos.filter((t) => t.en_carencia);

  return (
    <>
      <PageHeader
        titulo="Vacunas y tratamientos"
        descripcion="El personal registra lo aplicado en el lote. El sistema cuenta la carencia hasta la faena y el veterinario valida o deja su observación."
        acciones={
          puedeCargar && (
            <>
              <button className="btn secondary" type="button" onClick={() => { setError(""); setNuevaVac(true); }}>
                <Icon name="mas" /> Programar vacuna
              </button>
              <button className="btn primario" type="button" onClick={() => { setError(""); setNuevoTrat(true); }}>
                <Icon name="mas" /> Registrar tratamiento
              </button>
            </>
          )
        }
      />

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
                        <small>{t.dosis} · {t.via} · {t.aves_tratadas ? `${num(t.aves_tratadas)} aves` : "todo el lote"}</small>
                      </td>
                      <td>{fecha(t.fecha_inicio)} – {fecha(t.ultima_dosis)}</td>
                      <td>
                        {t.en_carencia
                          ? <Estado valor="VENCIDA" texto={`Hasta ${fecha(t.libre_faena)}`} />
                          : <Estado valor="ACTIVO" texto={`Libre desde ${fecha(t.libre_faena)}`} />}
                      </td>
                      <td><Estado valor={t.estado} /></td>
                      <td className="acciones">
                        <button className="link-button" type="button" onClick={() => revisar({ tipo: "tratamiento", item: t })}>
                          {esVet && t.estado === "PENDIENTE" ? "Revisar" : "Ver detalle"}
                        </button>
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
                  <tr><th>Vacuna</th><th>Fecha programada</th><th>Estado</th><th /></tr>
                </thead>
                <tbody>
                  {vacunas.map((v) => {
                    const vencida = v.estado === "PENDIENTE" && v.fecha_programada <= hoy;
                    return (
                      <tr key={v.id}>
                        <td className="celda-principal">
                          <strong>{v.nombre}</strong>
                          {v.observacion && <small>{v.observacion}</small>}
                        </td>
                        <td>{fecha(v.fecha_programada)}</td>
                        <td>{vencida ? <Estado valor="VENCIDA" texto="Vencida" /> : <Estado valor={v.estado} />}</td>
                        <td className="acciones">
                          <button className="link-button" type="button" onClick={() => revisar({ tipo: "vacuna", item: v })}>
                            {esVet && v.estado === "PENDIENTE" ? "Revisar" : "Ver detalle"}
                          </button>
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
        titulo="Registrar tratamiento"
        descripcion="Los días de carencia son los que indica el frasco, contados desde la última dosis."
        onCerrar={() => setNuevoTrat(false)}
        onGuardar={guardarTratamiento}
        guardando={guardando}
        textoGuardar="Registrar tratamiento"
        error={error}
      >
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
          <Campo label="Primer día">
            <input type="date" value={trat.inicio} onChange={(e) => setTrat({ ...trat, inicio: e.target.value })} required />
          </Campo>
          <Campo label="Días de tratamiento">
            <input type="number" min="1" max="30" value={trat.dias} onChange={(e) => setTrat({ ...trat, dias: e.target.value })} required />
          </Campo>
          <Campo label="Días de carencia" ayuda={producto ? `Sugerido: ${producto.carencia} días. Confirma con la etiqueta del frasco.` : "Según la etiqueta del producto."}>
            <input type="number" min="0" max="60" value={trat.carencia} onChange={(e) => setTrat({ ...trat, carencia: e.target.value })} required />
          </Campo>
          <Campo label="Aves tratadas" ayuda="Vacío = todo el lote.">
            <input type="number" min="1" value={trat.aves} onChange={(e) => setTrat({ ...trat, aves: e.target.value })} />
          </Campo>
        </Seccion>
      </DrawerForm>

      <DrawerForm
        abierto={nuevaVac}
        titulo="Programar vacuna"
        descripcion="Queda pendiente hasta que el veterinario la valide."
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
            <input type="date" value={vac.fecha} onChange={(e) => setVac({ ...vac, fecha: e.target.value })} required />
          </Campo>
        </Seccion>
      </DrawerForm>

      <Drawer
        abierto={revision !== null}
        titulo={revision ? (revision.tipo === "vacuna" ? revision.item.nombre : revision.item.medicamento) : ""}
        descripcion={revision?.tipo === "vacuna" ? "Vacuna del lote" : "Tratamiento del lote"}
        onCerrar={() => setRevision(null)}
        pie={
          esVet && revision?.item.estado === "PENDIENTE" ? (
            <>
              <button className="btn secondary" type="button" disabled={guardando} onClick={() => decidir("OBSERVADA")}>Observar</button>
              <button className="btn" type="button" disabled={guardando} onClick={() => decidir("VALIDADA")}>Validar</button>
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
            {revision.item.observacion && (<><dt>Observación</dt><dd>{revision.item.observacion}</dd></>)}
          </dl>
        )}
        {esVet && revision?.item.estado === "PENDIENTE" && (
          <Campo label={revision.tipo === "vacuna" ? "Observación" : "Diagnóstico o indicación"} ayuda="Queda registrado con tu nombre.">
            <textarea rows={4} value={nota} onChange={(e) => setNota(e.target.value)} placeholder="Ej. Aplicación conforme" />
          </Campo>
        )}
      </Drawer>
    </>
  );
}
