import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { api, avisarCambios, fecha, type Organizacion, type SolicitudContacto, type Usuario } from "../../api";
import { DrawerCredencial, type Credencial } from "../../components/Cuentas";
import { Campo, DrawerForm, Estado, Icon, PageHeader, Panel, Seccion, Tabs, Vacio, mensajeError, useToast } from "../../components/ui";

type Alta = { organizacion: Organizacion; usuario: Usuario; clave_temporal: string };

export default function Clientes() {
  const location = useLocation();
  const navigate = useNavigate();
  const avisar = useToast();
  const desde = (location.state as { solicitud?: SolicitudContacto } | null)?.solicitud ?? null;
  const [clientes, setClientes] = useState<Organizacion[]>([]);
  const [filtro, setFiltro] = useState("ACTIVA");
  const [nuevo, setNuevo] = useState(desde !== null);
  const [form, setForm] = useState({
    nombre: desde ? desde.empresa || desde.nombre : "",
    productorNombre: desde?.nombre ?? "",
    productorEmail: desde?.email ?? "",
  });
  const [solicitudId, setSolicitudId] = useState<number | null>(desde?.id ?? null);
  const [creado, setCreado] = useState<{ id: number; titulo: string; datos: Credencial } | null>(null);
  const [error, setError] = useState("");
  const [guardando, setGuardando] = useState(false);

  async function cargar() {
    setClientes(await api<Organizacion[]>("/plataforma/organizaciones"));
  }

  useEffect(() => {
    cargar().catch((err) => avisar(mensajeError(err), "riesgo"));
    // La solicitud llega una sola vez; se limpia para que recargar no la repita.
    if (desde) navigate(location.pathname, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function abrirNuevo() {
    setError("");
    setSolicitudId(null);
    setForm({ nombre: "", productorNombre: "", productorEmail: "" });
    setNuevo(true);
  }

  async function crear() {
    setError("");
    setGuardando(true);
    try {
      const data = await api<Alta>("/plataforma/organizaciones", {
        method: "POST",
        body: JSON.stringify({
          nombre: form.nombre,
          productor_nombre: form.productorNombre,
          productor_email: form.productorEmail,
          solicitud_id: solicitudId,
        }),
      });
      setNuevo(false);
      setSolicitudId(null);
      setFiltro("ACTIVA");
      setCreado({
        id: data.organizacion.id,
        titulo: `Cliente "${data.organizacion.nombre}" creado`,
        datos: { email: data.usuario.email, clave: data.clave_temporal },
      });
      avisarCambios();
      await cargar();
    } catch (err) {
      setError(mensajeError(err, "No se pudo crear el cliente"));
    } finally {
      setGuardando(false);
    }
  }

  const visibles = filtro === "TODOS" ? clientes : clientes.filter((c) => c.estado === filtro);

  return (
    <>
      <PageHeader
        eyebrow="Plataforma"
        titulo="Clientes"
        descripcion="Cada cliente es una organización con su productor, su personal y sus granjas avícolas."
        acciones={<button className="btn primario" type="button" onClick={abrirNuevo}><Icon name="mas" /> Nuevo cliente</button>}
      />

      <div className="kpis">
        <article className="kpi"><span className="kpi-icono"><Icon name="clientes" /></span><div><span>Clientes activos</span><strong>{clientes.filter((c) => c.estado === "ACTIVA").length}</strong></div></article>
        <article className="kpi riesgo"><span className="kpi-icono"><Icon name="pausa" /></span><div><span>Suspendidos</span><strong>{clientes.filter((c) => c.estado === "SUSPENDIDA").length}</strong></div></article>
        <article className="kpi acento"><span className="kpi-icono"><Icon name="lotes" /></span><div><span>Lotes activos</span><strong>{clientes.reduce((t, c) => t + c.lotes_activos, 0)}</strong></div></article>
        <article className="kpi"><span className="kpi-icono"><Icon name="cuentas" /></span><div><span>Cuentas activas</span><strong>{clientes.reduce((t, c) => t + c.usuarios_activos, 0)}</strong></div></article>
      </div>

      <Panel sinPadding>
        <div className="barra-lista">
          <Tabs
            valor={filtro}
            onCambio={setFiltro}
            items={[
              { id: "ACTIVA", label: "Activos", cantidad: clientes.filter((c) => c.estado === "ACTIVA").length },
              { id: "SUSPENDIDA", label: "Suspendidos", cantidad: clientes.filter((c) => c.estado === "SUSPENDIDA").length },
              { id: "TODOS", label: "Todos", cantidad: clientes.length },
            ]}
          />
        </div>
        {visibles.length === 0 ? (
          <Vacio icono="clientes" titulo="No hay clientes en esta vista" />
        ) : (
          <div className="tabla-wrap">
            <table>
              <thead>
                <tr><th>Cliente</th><th>Productor</th><th>Personal</th><th>Granjas</th><th>Lotes activos</th><th>Estado</th><th /></tr>
              </thead>
              <tbody>
                {visibles.map((c) => (
                  <tr key={c.id} className="clicable" onClick={() => navigate(`/plataforma/clientes/${c.id}`)}>
                    <td className="celda-principal"><strong>{c.nombre}</strong><small>Desde {c.creada_en ? fecha(c.creada_en) : "—"}</small></td>
                    <td className="celda-principal">
                      <strong>{c.responsables[0]?.nombre ?? "—"}</strong>
                      <small>{c.responsables[0]?.email}</small>
                    </td>
                    <td>{c.personal.OPERARIO} op. · {c.personal.VETERINARIO} vet.</td>
                    <td className="num">{c.granjas}</td>
                    <td className="num">{c.lotes_activos}</td>
                    <td><Estado valor={c.estado} /></td>
                    <td className="acciones"><button className="link-button" type="button">Gestionar</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <DrawerForm
        abierto={nuevo}
        titulo="Nuevo cliente"
        descripcion={solicitudId
          ? "Datos tomados de la solicitud de contacto. Si quien escribió no es el dueño de la granja, cambia el productor por el correcto: la solicitud quedará enlazada igual."
          : "Crea la organización y la cuenta de su productor."}
        onCerrar={() => setNuevo(false)}
        onGuardar={crear}
        guardando={guardando}
        textoGuardar="Crear cliente"
        error={error}
      >
        <Seccion titulo="Organización">
          <Campo label="Nombre del cliente" ancho ayuda="Empresa o granja avícola.">
            <input value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} required minLength={3} />
          </Campo>
        </Seccion>
        <Seccion titulo="Productor responsable">
          <Campo label="Nombre completo" ancho>
            <input value={form.productorNombre} onChange={(e) => setForm({ ...form, productorNombre: e.target.value })} required minLength={3} />
          </Campo>
          <Campo label="Correo" ancho ayuda="Con este correo entrará al sistema. Después podrás agregar a sus operarios y veterinarios.">
            <input type="email" value={form.productorEmail} onChange={(e) => setForm({ ...form, productorEmail: e.target.value })} required />
          </Campo>
        </Seccion>
      </DrawerForm>

      <DrawerCredencial
        credencial={creado?.datos ?? null}
        titulo={creado?.titulo ?? ""}
        onCerrar={() => {
          const id = creado?.id;
          setCreado(null);
          if (id) navigate(`/plataforma/clientes/${id}`);
        }}
      />
    </>
  );
}
