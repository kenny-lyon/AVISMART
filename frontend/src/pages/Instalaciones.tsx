import { useState } from "react";
import { Link } from "react-router-dom";
import { api, num, type Galpon, type Granja } from "../api";
import { Campo, DrawerForm, Icon, PageHeader, Panel, Seccion, Vacio, mensajeError, useToast } from "../components/ui";
import { useLote } from "../lote";

type Edicion =
  | { tipo: "granja"; granja?: Granja }
  | { tipo: "galpon"; granja: Granja; galpon?: Galpon };

export default function Instalaciones() {
  const { resumen, recargar } = useLote();
  const avisar = useToast();
  const [edicion, setEdicion] = useState<Edicion | null>(null);
  const [nombre, setNombre] = useState("");
  const [extra, setExtra] = useState("");
  const [error, setError] = useState("");
  const [guardando, setGuardando] = useState(false);
  const granjas = resumen?.granjas ?? [];
  const lotesActivos = (galponId: number) => (resumen?.lotes ?? []).filter((l) => l.galpon_id === galponId && l.estado === "ACTIVO");

  function abrir(e: Edicion) {
    setError("");
    if (e.tipo === "granja") {
      setNombre(e.granja?.nombre ?? "");
      setExtra(e.granja?.ubicacion ?? "");
    } else {
      setNombre(e.galpon?.nombre ?? "");
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
        const cuerpo = JSON.stringify({ nombre, ubicacion: extra });
        if (edicion.granja) await api(`/granjas/${edicion.granja.id}`, { method: "PUT", body: cuerpo });
        else await api("/granjas", { method: "POST", body: cuerpo });
        avisar(edicion.granja ? "Granja avícola actualizada." : "Granja avícola registrada. Ahora agrega sus galpones.");
      } else {
        const cuerpo = JSON.stringify({ nombre, capacidad: Number(extra) });
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
            descripcion={granja.ubicacion}
            sinPadding
            acciones={
              <>
                <button className="btn small secondary" type="button" onClick={() => abrir({ tipo: "granja", granja })}>
                  <Icon name="editar" size={15} /> Editar
                </button>
                <button className="btn small" type="button" onClick={() => abrir({ tipo: "galpon", granja })}>
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
          <Campo label="Nombre" ancho>
            <input value={nombre} onChange={(e) => setNombre(e.target.value)} placeholder={esGranja ? "Granja avícola San Martín" : "Galpón 1"} required minLength={esGranja ? 3 : 1} />
          </Campo>
          {esGranja ? (
            <Campo label="Ubicación" ancho>
              <input value={extra} onChange={(e) => setExtra(e.target.value)} placeholder="Juliaca, Puno" required minLength={2} />
            </Campo>
          ) : (
            <Campo label="Capacidad (aves)" ancho ayuda="Número máximo de pollitos que admite el galpón.">
              <input type="number" min="1" value={extra} onChange={(e) => setExtra(e.target.value)} placeholder="6000" required />
            </Campo>
          )}
        </Seccion>
      </DrawerForm>
    </>
  );
}
