import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, avisarCambios, fecha, ROLES_CLIENTE, type Organizacion } from "../../api";
import { useAuth } from "../../auth";
import Cuentas from "../../components/Cuentas";
import { Campo, DrawerForm, Estado, Icon, PageHeader, mensajeError, useToast } from "../../components/ui";

type Eliminado = { respaldo: string; exportacion: string; datos: unknown };

/** Descarga en el navegador la exportación de los datos del cliente eliminado. */
function descargar(nombre: string, datos: unknown) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(datos, null, 2)], { type: "application/json" }));
  const enlace = document.createElement("a");
  enlace.href = url;
  enlace.download = nombre;
  enlace.click();
  URL.revokeObjectURL(url);
}

export default function ClienteDetalle() {
  const { id } = useParams();
  const navigate = useNavigate();
  const avisar = useToast();
  const { entrarSoporte } = useAuth();
  const [cliente, setCliente] = useState<Organizacion | null>(null);
  const [error, setError] = useState("");
  const [eliminar, setEliminar] = useState(false);
  const [confirmacion, setConfirmacion] = useState("");
  const [eliminando, setEliminando] = useState(false);
  const [errorEliminar, setErrorEliminar] = useState("");

  async function cargar() {
    setCliente(await api<Organizacion>(`/plataforma/organizaciones/${id}`));
  }

  useEffect(() => {
    cargar().catch((err) => setError(mensajeError(err)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function cambiarEstado() {
    if (!cliente) return;
    const suspender = cliente.estado === "ACTIVA";
    if (suspender && !window.confirm(`Todas las cuentas de ${cliente.nombre} dejarán de entrar. ¿Suspender?`)) return;
    try {
      setCliente(await api<Organizacion>(`/plataforma/organizaciones/${cliente.id}`, {
        method: "PATCH",
        body: JSON.stringify({ estado: suspender ? "SUSPENDIDA" : "ACTIVA" }),
      }));
      avisar(suspender ? `${cliente.nombre} quedó suspendido.` : `${cliente.nombre} volvió a estar activo.`);
      avisarCambios();
    } catch (err) {
      avisar(mensajeError(err, "No se pudo cambiar el estado"), "riesgo");
    }
  }

  async function abrirSoporte() {
    if (!cliente) return;
    try {
      await entrarSoporte(cliente.id);
      navigate("/panel", { replace: true });
    } catch (err) {
      avisar(mensajeError(err, "No se pudo abrir el modo soporte"), "riesgo");
    }
  }

  function abrirEliminar() {
    setConfirmacion("");
    setErrorEliminar("");
    setEliminar(true);
  }

  async function confirmarEliminar() {
    if (!cliente) return;
    setEliminando(true);
    setErrorEliminar("");
    try {
      const r = await api<Eliminado>(`/plataforma/organizaciones/${cliente.id}/eliminar`, {
        method: "POST",
        body: JSON.stringify({ confirmacion }),
      });
      descargar(r.exportacion, r.datos);
      avisar(`${cliente.nombre} fue eliminado. Se descargó el archivo con su información.`);
      avisarCambios();
      navigate("/plataforma/clientes", { replace: true });
    } catch (err) {
      setErrorEliminar(mensajeError(err, "No se pudo eliminar el cliente"));
    } finally {
      setEliminando(false);
    }
  }

  if (!cliente) return <p className="muted">{error || "Cargando cliente…"}</p>;

  const suspendido = cliente.estado === "SUSPENDIDA";

  return (
    <>
      <p style={{ margin: "0 0 10px" }}>
        <Link to="/plataforma/clientes">← Clientes</Link>
      </p>
      <PageHeader
        eyebrow="Cliente"
        titulo={cliente.nombre}
        descripcion={<>Cliente desde {cliente.creada_en ? fecha(cliente.creada_en) : "—"} · <Estado valor={cliente.estado} /> · Telegram {cliente.telegram_vinculado ? "vinculado" : "sin vincular"}</>}
        acciones={
          <>
            <button className="btn primario" type="button" onClick={abrirSoporte} title="Configura granjas, galpones y el primer lote con los permisos de su productor">
              <Icon name="cuentas" size={16} /> Entrar como soporte
            </button>
            <button className={suspendido ? "btn secondary" : "btn danger"} type="button" onClick={cambiarEstado}>
              <Icon name="pausa" size={16} /> {suspendido ? "Reactivar cliente" : "Suspender"}
            </button>
            {suspendido && (
              <button className="btn danger" type="button" onClick={abrirEliminar}>
                <Icon name="papelera" size={16} /> Eliminar
              </button>
            )}
          </>
        }
      />

      {cliente.origen && (
        <div className="aviso info" style={{ marginBottom: 16 }}>
          <Icon name="aviso" />
          <span>
            Origen: solicitud de <b>{cliente.origen.nombre}</b> ({cliente.origen.email}) del {fecha(cliente.origen.fecha)}.
            El contacto inicial lo hizo otra persona, no el productor.
          </span>
        </div>
      )}

      <div className="kpis">
        <article className="kpi"><span className="kpi-icono"><Icon name="cuentas" /></span><div><span>Productores</span><strong>{cliente.personal.PRODUCTOR}</strong></div></article>
        <article className="kpi"><span className="kpi-icono"><Icon name="registro" /></span><div><span>Operarios</span><strong>{cliente.personal.OPERARIO}</strong></div></article>
        <article className="kpi"><span className="kpi-icono"><Icon name="sanidad" /></span><div><span>Veterinarios</span><strong>{cliente.personal.VETERINARIO}</strong></div></article>
        <article className="kpi acento"><span className="kpi-icono"><Icon name="granjas" /></span><div><span>Granjas · lotes activos</span><strong>{cliente.granjas} · {cliente.lotes_activos}</strong></div></article>
      </div>

      <Cuentas
        base={`/plataforma/organizaciones/${cliente.id}/usuarios`}
        roles={["OPERARIO", "VETERINARIO"]}
        gestiona={ROLES_CLIENTE}
        onCambio={() => cargar().catch(() => undefined)}
        titulo="Personal del cliente"
        descripcion="El productor principal se crea junto con el cliente. Aquí puedes agregar operarios y médicos veterinarios; cada alta genera una clave temporal. El productor también puede agregar a su personal."
      />

      <DrawerForm
        abierto={eliminar}
        titulo="Eliminar cliente"
        descripcion={<>Se eliminarán <b>{cliente.nombre}</b> y toda su información: cuentas, granjas, galpones, lotes, registros, sanidad y alertas.</>}
        onCerrar={() => setEliminar(false)}
        onGuardar={confirmarEliminar}
        guardando={eliminando}
        textoGuardar="Eliminar para siempre"
        error={errorEliminar}
        peligro
      >
        <div className="aviso info">
          <Icon name="aviso" />
          <span>
            Esta acción no se puede deshacer. Por seguridad, guardaremos una <b>copia de respaldo</b> y se descargará un
            archivo con <b>toda la información del cliente</b>, por si necesitas entregársela o restaurarla más adelante.
          </span>
        </div>
        <Campo label={`Para confirmar, escribe el nombre del cliente: ${cliente.nombre}`} ancho>
          <input value={confirmacion} onChange={(e) => setConfirmacion(e.target.value)} autoComplete="off" required />
        </Campo>
      </DrawerForm>
    </>
  );
}
