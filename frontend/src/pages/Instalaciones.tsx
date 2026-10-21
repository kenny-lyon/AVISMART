import { useState } from "react";
import { Link } from "react-router-dom";
import { api, num, type Galpon, type Granja } from "../api";
import { Campo, DrawerForm, Icon, PageHeader, Panel, Seccion, Vacio, mensajeError, useToast } from "../components/ui";
import { useLote } from "../lote";
import UbicacionGranja, { type Ubicacion } from "../components/UbicacionGranja";

const SIN_UBICACION: Ubicacion = { departamento: "", provincia: "", distrito: "", latitud: null, longitud: null };

const MAX_GALPONES = 10;
const MAX_CAPACIDAD = 100_000;

/** Mismo criterio que el servidor: primer número libre de la granja (Galpón 01 … Galpón 10). */
function siguienteGalpon(g: Granja) {
  const usados = new Set(g.galpones.map((x) => Number(/^galp[oó]n\s*0*(\d{1,2})$/i.exec(x.nombre.trim())?.[1])));
  const n = Array.from({ length: MAX_GALPONES }, (_, i) => i + 1).find((i) => !usados.has(i)) ?? MAX_GALPONES;
  return `Galpón ${String(n).padStart(2, "0")}`;
}

/** Enlace gratuito para llegar a la granja (abre la app de mapas del celular). */
function comoLlegar(g: Granja) {
  return `https://www.google.com/maps/dir/?api=1&destination=${g.latitud},${g.longitud}`;
}

type Edicion =
  | { tipo: "granja"; granja?: Granja }
  | { tipo: "galpon"; granja: Granja; galpon?: Galpon };

export default function Instalaciones() {
  const { resumen, recargar } = useLote();
  const avisar = useToast();
  const [edicion, setEdicion] = useState<Edicion | null>(null);
  const [nombre, setNombre] = useState("");
  const [extra, setExtra] = useState("");
  const [ubicacion, setUbicacion] = useState<Ubicacion>(SIN_UBICACION);
  const [error, setError] = useState("");
  const [guardando, setGuardando] = useState(false);
  const granjas = resumen?.granjas ?? [];
  const lotesActivos = (galponId: number) => (resumen?.lotes ?? []).filter((l) => l.galpon_id === galponId && l.estado === "ACTIVO");

  function abrir(e: Edicion) {
    setError("");
    if (e.tipo === "granja") {
      setNombre(e.granja?.nombre ?? "");
      setExtra(e.granja?.ubicacion ?? "");
      setUbicacion({
        departamento: e.granja?.departamento ?? "",
        provincia: e.granja?.provincia ?? "",
        distrito: e.granja?.distrito ?? "",
        latitud: e.granja?.latitud ?? null,
        longitud: e.granja?.longitud ?? null,
      });
    } else {
      setNombre(e.galpon?.nombre ?? siguienteGalpon(e.granja));
      setExtra(e.galpon ? String(e.galpon.capacidad) : "");
    }
    setEdicion(e);
  }

  async function guardar() {
    if (!edicion) return;
    setError("");
    setGuardando(true);
    try {
      if (edicion.tipo === "granja") {
        // Con el distrito elegido, la ubicación legible la arma el sistema ("Juliaca, San Román, Puno").
        const cuerpo = JSON.stringify({ nombre, ...ubicacion, ubicacion: ubicacion.distrito ? "" : extra });
        if (edicion.granja) await api(`/granjas/${edicion.granja.id}`, { method: "PUT", body: cuerpo });
        else await api("/granjas", { method: "POST", body: cuerpo });
        avisar(edicion.granja ? "Granja avícola actualizada." : "Granja avícola registrada. Ahora agrega sus galpones.");
      } else {
        const cuerpo = JSON.stringify({ capacidad: Number(extra) });
        if (edicion.galpon) await api(`/galpones/${edicion.galpon.id}`, { method: "PUT", body: cuerpo });
        else await api(`/granjas/${edicion.granja.id}/galpones`, { method: "POST", body: cuerpo });
        avisar(edicion.galpon ? "Galpón actualizado." : `Galpón "${nombre}" agregado.`);
      }
      await recargar();
      setEdicion(null);
    } catch (err) {
      setError(mensajeError(err, "No se pudo guardar"));
    } finally {
      setGuardando(false);
    }
  }

  const esGranja = edicion?.tipo === "granja";
  const editando = edicion ? (edicion.tipo === "granja" ? !!edicion.granja : !!edicion.galpon) : false;
  const totalGalpones = granjas.reduce((t, g) => t + g.galpones.length, 0);

  return (
    <>
      <PageHeader
        titulo="Granjas avícolas y galpones"
        descripcion={`${granjas.length} granja(s) avícola(s) · ${totalGalpones} galpón(es). Cada lote se abre dentro de un galpón.`}
        acciones={
          <button className="btn primario" type="button" onClick={() => abrir({ tipo: "granja" })}>
            <Icon name="mas" /> Nueva granja avícola
          </button>
        }
      />

      {granjas.length === 0 ? (
        <Panel>
          <Vacio
            icono="granjas"
            titulo="Registra tu primera granja avícola"
            texto="Indica su nombre y ubicación; después agregas los galpones con su capacidad."
            accion={<button className="btn" type="button" onClick={() => abrir({ tipo: "granja" })}><Icon name="mas" /> Nueva granja avícola</button>}
          />
        </Panel>
      ) : (
        granjas.map((granja) => (
          <Panel
            key={granja.id}
            titulo={granja.nombre}
            descripcion={
              <>
                {granja.ubicacion}
                {granja.latitud !== null && (
                  <a className="enlace-mapa" href={comoLlegar(granja)} target="_blank" rel="noreferrer">
                    <Icon name="ubicacion" size={14} /> Cómo llegar
                  </a>
                )}
              </>
            }
            sinPadding
            acciones={
              <>
                <button className="btn small secondary" type="button" onClick={() => abrir({ tipo: "granja", granja })}>
                  <Icon name="editar" size={15} /> Editar
                </button>
                <button
                  className="btn small"
                  type="button"
                  onClick={() => abrir({ tipo: "galpon", granja })}
                  disabled={granja.galpones.length >= MAX_GALPONES}
                  title={granja.galpones.length >= MAX_GALPONES ? `Una granja avícola puede tener hasta ${MAX_GALPONES} galpones` : undefined}
                >
                  <Icon name="mas" size={15} /> Agregar galpón
                </button>
              </>
            }
          >
            {granja.galpones.length === 0 ? (
              <Vacio icono="granjas" titulo="Sin galpones" texto="Agrega el primer galpón para poder abrir lotes." />
            ) : (
              <div className="tabla-wrap">
                <table>
                  <thead>
                    <tr><th>Galpón</th><th>Capacidad</th><th>Ocupación actual</th><th /></tr>
                  </thead>
                  <tbody>
                    {granja.galpones.map((galpon) => {
                      const activos = lotesActivos(galpon.id);
                      const aves = activos.reduce((t, l) => t + l.poblacion_inicial, 0);
                      return (
                        <tr key={galpon.id}>
                          <td className="celda-principal"><strong>{galpon.nombre}</strong></td>
                          <td className="num">{num(galpon.capacidad)} aves</td>
                          <td>{activos.length ? `${activos.length} lote(s) activo(s) · ${num(aves)} pollitos` : <span className="muted">Libre</span>}</td>
                          <td className="acciones">
                            <button className="link-button" type="button" onClick={() => abrir({ tipo: "galpon", granja, galpon })}>Editar</button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </Panel>
        ))
      )}

      {granjas.some((g) => g.galpones.length) && (resumen?.lotes.length ?? 0) === 0 && (
        <div className="aviso info" style={{ marginTop: 16 }}>
          Ya tienes galpones. Siguiente paso: <Link to="/lotes">abrir el primer lote</Link>.
        </div>
      )}

      <DrawerForm
        abierto={edicion !== null}
        titulo={esGranja ? (editando ? "Editar granja avícola" : "Nueva granja avícola") : editando ? "Editar galpón" : "Agregar galpón"}
        descripcion={edicion?.tipo === "galpon" ? edicion.granja.nombre : "Datos generales de la instalación."}
        onCerrar={() => setEdicion(null)}
        onGuardar={guardar}
        guardando={guardando}
        textoGuardar={editando ? "Guardar cambios" : esGranja ? "Registrar granja avícola" : "Agregar galpón"}
        error={error}
      >
        <Seccion titulo={esGranja ? "Granja avícola" : "Galpón"}>
          {esGranja ? (
            <Campo label="Nombre" ancho>
              <input value={nombre} onChange={(e) => setNombre(e.target.value)} placeholder="Granja avícola San Fernando" required minLength={3} />
            </Campo>
          ) : (
            <Campo label="Galpón" ancho ayuda={editando ? "El número del galpón no cambia." : `Se numera solo, en orden. Máximo ${MAX_GALPONES} galpones por granja avícola.`}>
              <input value={nombre} readOnly aria-readonly="true" />
            </Campo>
          )}
          {esGranja ? (
            <UbicacionGranja valor={ubicacion} onCambio={setUbicacion} />
          ) : (
            <Campo label="Capacidad (aves)" ancho ayuda="Número máximo de pollitos que admite el galpón (hasta 100 000).">
              <input
                type="number"
                min="1"
                max={MAX_CAPACIDAD}
                inputMode="numeric"
                value={extra}
                onChange={(e) => {
                  // Solo dígitos y nunca más de 100 000: no deja seguir escribiendo ceros.
                  const digitos = e.target.value.replace(/\D/g, "").slice(0, 6);
                  setExtra(digitos && Number(digitos) > MAX_CAPACIDAD ? String(MAX_CAPACIDAD) : digitos);
                }}
                placeholder="6000"
                required
              />
            </Campo>
          )}
        </Seccion>
      </DrawerForm>
    </>
  );
}
