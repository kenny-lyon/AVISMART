import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, avisarCambios, type SolicitudContacto } from "../api";
import { Drawer, Estado, Icon, PageHeader, Panel, Tabs, Vacio, mensajeError, useToast } from "../components/ui";

const MOTIVOS: Record<string, string> = { DEMO: "Demo", COMERCIAL: "Comercial", SOPORTE: "Soporte", ALIANZA: "Alianza" };
const PLANES: Record<string, string> = { POR_DEFINIR: "Por definir", BASICO: "Básico", PROFESIONAL: "Profesional", EMPRESARIAL: "Empresarial" };

function cuando(iso: string) {
  return new Date(iso).toLocaleString("es-PE", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

export default function Propietario() {
  const navigate = useNavigate();
  const avisar = useToast();
  const [solicitudes, setSolicitudes] = useState<SolicitudContacto[]>([]);
  const [filtro, setFiltro] = useState("NUEVA");
  const [detalle, setDetalle] = useState<SolicitudContacto | null>(null);

  async function cargar() {
    try {
      setSolicitudes(await api<SolicitudContacto[]>("/plataforma/solicitudes"));
    } catch (err) {
      avisar(mensajeError(err, "No se pudieron cargar las solicitudes"), "riesgo");
    }
  }

  useEffect(() => {
    cargar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function cambiarEstado(item: SolicitudContacto, estado: SolicitudContacto["estado"]) {
    try {
      const actualizada = await api<SolicitudContacto>(`/plataforma/solicitudes/${item.id}`, { method: "PATCH", body: JSON.stringify({ estado }) });
      setSolicitudes((lista) => lista.map((s) => (s.id === item.id ? actualizada : s)));
      setDetalle(null);
      avisarCambios();
      avisar(estado === "CONTACTADA" ? "Solicitud marcada como contactada." : estado === "NUEVA" ? "Solicitud movida a la bandeja." : "Solicitud descartada.");
    } catch (err) {
      avisar(mensajeError(err, "No se pudo actualizar"), "riesgo");
    }
  }

  // «Descartadas» reúne las descartadas y las de clientes que se eliminaron (dados de baja).
  const enPestana = (s: SolicitudContacto, pestana: string) =>
    pestana === "DESCARTADA" ? s.estado === "DESCARTADA" || s.estado === "BAJA" : s.estado === pestana;
  const cuenta = (pestana: string) => solicitudes.filter((s) => enPestana(s, pestana)).length;
  const bandeja = solicitudes.filter((s) => s.estado !== "SOSPECHOSA");
  const visibles = filtro === "TODAS" ? bandeja : solicitudes.filter((s) => enPestana(s, filtro));
  const etiqueta = (s: SolicitudContacto) => (s.estado === "BAJA" ? "Cliente dado de baja" : undefined);

  return (
    <>
      <PageHeader
        eyebrow="Plataforma"
        titulo="Solicitudes"
        descripcion="Solo llegan aquí las solicitudes con el correo confirmado. Las detectadas por el filtro antispam quedan aparte en «Sospechosas»."
        acciones={<button className="btn secondary" type="button" onClick={cargar}>Actualizar</button>}
      />

      <Panel sinPadding>
        <div className="barra-lista">
          <Tabs
            valor={filtro}
            onCambio={setFiltro}
            items={[
              { id: "NUEVA", label: "Nuevas", cantidad: cuenta("NUEVA") },
              { id: "CONTACTADA", label: "Contactadas", cantidad: cuenta("CONTACTADA") },
              { id: "CLIENTE", label: "Clientes", cantidad: cuenta("CLIENTE") },
              { id: "DESCARTADA", label: "Descartadas", cantidad: cuenta("DESCARTADA") },
              { id: "TODAS", label: "Todas", cantidad: bandeja.length },
              { id: "SOSPECHOSA", label: "Sospechosas", cantidad: cuenta("SOSPECHOSA") },
            ]}
          />
        </div>
        {visibles.length === 0 ? (
          <Vacio icono="solicitudes" titulo="No hay solicitudes en este estado" texto="Las que lleguen desde la web aparecerán aquí." />
        ) : (
          <div className="tabla-wrap">
            <table>
              <thead>
                <tr><th>Interesado</th><th>Motivo</th><th>Escala</th><th>Plan</th><th>Recibida</th><th>Estado</th><th /></tr>
              </thead>
              <tbody>
                {visibles.map((s) => (
                  <tr key={s.id} className="clicable" onClick={() => setDetalle(s)}>
                    <td className="celda-principal">
                      <strong>{s.empresa || s.nombre}</strong>
                      <small>
                        {s.nombre} · {s.email}{s.motivo_sospecha ? ` · ${s.motivo_sospecha}` : ""}
                        {s.cuenta_existente?.organizacion && s.estado !== "CLIENTE" ? ` · ya es cliente: ${s.cuenta_existente.organizacion.nombre}` : ""}
                      </small>
                    </td>
                    <td>{MOTIVOS[s.motivo] ?? s.motivo}</td>
                    <td>{s.aves || <span className="muted">—</span>}</td>
                    <td>{PLANES[s.plan] ?? s.plan}</td>
                    <td>{cuando(s.creada_en)}</td>
                    <td><Estado valor={s.estado} texto={etiqueta(s)} /></td>
                    <td className="acciones"><button className="link-button" type="button">Abrir</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <Drawer
        abierto={detalle !== null}
        titulo={detalle ? detalle.empresa || detalle.nombre : ""}
        descripcion={detalle ? `${detalle.nombre} · ${detalle.pais}` : undefined}
        onCerrar={() => setDetalle(null)}
        ancho="amplio"
        pie={
          detalle && (
            <>
              {["NUEVA", "CONTACTADA", "SOSPECHOSA"].includes(detalle.estado) && (
                <button className="btn secondary" type="button" onClick={() => cambiarEstado(detalle, "DESCARTADA")}>Descartar</button>
              )}
              {detalle.estado === "DESCARTADA" && (
                <button className="btn secondary" type="button" onClick={() => cambiarEstado(detalle, "NUEVA")}>Volver a Nuevas</button>
              )}
              {detalle.estado === "SOSPECHOSA" && (
                <button className="btn" type="button" onClick={() => cambiarEstado(detalle, "NUEVA")}>Es legítima</button>
              )}
              {detalle.estado === "NUEVA" && (
                <button className="btn secondary" type="button" onClick={() => cambiarEstado(detalle, "CONTACTADA")}>Marcar contactada</button>
              )}
              {detalle.cuenta_existente?.organizacion && detalle.estado !== "CLIENTE" && (
                <button className="btn primario" type="button" onClick={() => navigate(`/plataforma/clientes/${detalle.cuenta_existente!.organizacion!.id}`)}>
                  <Icon name="flecha" size={16} /> Ver cliente
                </button>
              )}
              {(detalle.estado === "NUEVA" || detalle.estado === "CONTACTADA") && !detalle.cuenta_existente && (
                <button className="btn primario" type="button" onClick={() => navigate("/plataforma/clientes", { state: { solicitud: detalle } })}>
                  <Icon name="flecha" size={16} /> Convertir en cliente
                </button>
              )}
            </>
          )
        }
      >
        {detalle && (
          <>
            {detalle.cuenta_existente && detalle.estado !== "CLIENTE" && (
              <div className="aviso info" style={{ marginBottom: 16 }}>
                <Icon name="aviso" />
                <span>
                  {detalle.cuenta_existente.organizacion ? (
                    <>
                      Este correo ya tiene una cuenta en el cliente <b>{detalle.cuenta_existente.organizacion.nombre}</b>
                      {detalle.cuenta_existente.organizacion.estado === "SUSPENDIDA" ? " (suspendido). Si quiere volver, reactívalo desde su ficha" : ". Atiéndelo desde su ficha"}
                      {" "}en lugar de crear otro cliente.
                    </>
                  ) : (
                    "Este correo pertenece a una cuenta de la plataforma. No se puede usar para un cliente."
                  )}
                </span>
              </div>
            )}
            <dl className="ficha">
              <dt>Estado</dt><dd><Estado valor={detalle.estado} texto={etiqueta(detalle)} /></dd>
              {detalle.motivo_sospecha && (<><dt>Motivo de sospecha</dt><dd>{detalle.motivo_sospecha}</dd></>)}
              <dt>Correo confirmado</dt><dd>{detalle.verificada_en ? cuando(detalle.verificada_en) : "No"}</dd>
              <dt>Correo</dt><dd><a href={`mailto:${detalle.email}?subject=AviSmart — respuesta a tu solicitud`}>{detalle.email}</a></dd>
              <dt>Celular</dt>
              <dd>
                {detalle.telefono ? (
                  <>
                    <a href={`tel:+51${detalle.telefono}`}>{detalle.telefono.replace(/(\d{3})(\d{3})(\d{3})/, "$1 $2 $3")}</a>
                    {" · "}
                    <a href={`https://wa.me/51${detalle.telefono}`} target="_blank" rel="noreferrer">WhatsApp</a>
                  </>
                ) : (
                  "No indicado"
                )}
              </dd>
              <dt>Motivo</dt><dd>{MOTIVOS[detalle.motivo] ?? detalle.motivo}</dd>
              <dt>Aves por ciclo</dt><dd>{detalle.aves || "No indicado"}</dd>
              <dt>Plan</dt><dd>{PLANES[detalle.plan] ?? detalle.plan}</dd>
              <dt>Recibida</dt><dd>{cuando(detalle.creada_en)}</dd>
              {detalle.atendida_en && (<><dt>Atendida</dt><dd>{cuando(detalle.atendida_en)}</dd></>)}
            </dl>
            <p className="campo-label" style={{ margin: "0 0 8px" }}>Mensaje</p>
            <p className="cita">{detalle.mensaje}</p>
          </>
        )}
      </Drawer>
    </>
  );
}
