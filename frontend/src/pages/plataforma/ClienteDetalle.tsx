import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, avisarCambios, fecha, ROLES_CLIENTE, ROLES_PERSONAL, type Organizacion } from "../../api";
import Cuentas from "../../components/Cuentas";
import { Estado, Icon, PageHeader, mensajeError, useToast } from "../../components/ui";

export default function ClienteDetalle() {
  const { id } = useParams();
  const avisar = useToast();
  const [cliente, setCliente] = useState<Organizacion | null>(null);
  const [error, setError] = useState("");

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

  if (!cliente) return <p className="muted">{error || "Cargando cliente…"}</p>;

  return (
    <>
      <p style={{ margin: "0 0 10px" }}>
        <Link to="/plataforma/clientes">← Clientes</Link>
      </p>
      <PageHeader
        eyebrow="Cliente"
        titulo={cliente.nombre}
        descripcion={<>Cliente desde {cliente.creada_en ? fecha(cliente.creada_en) : "—"} · <Estado valor={cliente.estado} /></>}
        acciones={
          <button className={cliente.estado === "ACTIVA" ? "btn danger" : "btn"} type="button" onClick={cambiarEstado}>
            <Icon name="pausa" size={16} /> {cliente.estado === "ACTIVA" ? "Suspender cliente" : "Reactivar cliente"}
          </button>
        }
      />

      <div className="kpis">
        <article className="kpi"><span className="kpi-icono"><Icon name="cuentas" /></span><div><span>Productores</span><strong>{cliente.personal.PRODUCTOR}</strong></div></article>
        <article className="kpi"><span className="kpi-icono"><Icon name="registro" /></span><div><span>Operativos</span><strong>{cliente.personal.OPERATIVO}</strong></div></article>
        <article className="kpi"><span className="kpi-icono"><Icon name="sanidad" /></span><div><span>Veterinarios</span><strong>{cliente.personal.VETERINARIO}</strong></div></article>
        <article className="kpi acento"><span className="kpi-icono"><Icon name="granjas" /></span><div><span>Granjas · lotes activos</span><strong>{cliente.granjas} · {cliente.lotes_activos}</strong></div></article>
      </div>

      <Cuentas
        base={`/plataforma/organizaciones/${cliente.id}/usuarios`}
        roles={ROLES_PERSONAL}
        gestiona={ROLES_CLIENTE}
        onCambio={() => cargar().catch(() => undefined)}
        titulo="Personal del cliente"
        descripcion="Productor, operativos y médicos veterinarios. Cada alta genera una clave temporal; el productor también puede agregar a su personal."
      />
    </>
  );
}
