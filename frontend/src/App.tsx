import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import { inicio } from "./api";
import PlataformaShell from "./components/PlataformaShell";
import Shell from "./components/Shell";
import { useAuth } from "./auth";
import { LoteProvider } from "./lote";
import Alertas from "./pages/Alertas";
import Camara from "./pages/Camara";
import CambiarClave from "./pages/CambiarClave";
import Contacto from "./pages/Contacto";
import Configuracion from "./pages/Configuracion";
import Instalaciones from "./pages/Instalaciones";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Lotes from "./pages/Lotes";
import Panel from "./pages/Panel";
import ClienteDetalle from "./pages/plataforma/ClienteDetalle";
import Clientes from "./pages/plataforma/Clientes";
import CuentasPlataforma from "./pages/plataforma/CuentasPlataforma";
import Propietario from "./pages/Propietario";
import Registro from "./pages/Registro";
import Sanidad from "./pages/Sanidad";
import Servicios from "./pages/Servicios";

function Cargando() {
  return <p className="muted" style={{ padding: 32 }}>Cargando AviSmart…</p>;
}

/** Zona de las organizaciones cliente: granjas avícolas, lotes y sanidad. */
function ZonaCliente() {
  const { usuario, listo } = useAuth();
  if (!listo) return <Cargando />;
  if (!usuario) return <Navigate to="/login" replace />;
  if (usuario.debe_cambiar_clave) return <Navigate to="/cambiar-clave" replace />;
  if (usuario.rol === "PLATAFORMA") return <Navigate to={inicio(usuario)} replace />;
  return (
    <LoteProvider>
      <Shell>
        <Outlet />
      </Shell>
    </LoteProvider>
  );
}

/** Zona del propietario de AviSmart: clientes y solicitudes, sin datos productivos. */
function ZonaPlataforma() {
  const { usuario, listo } = useAuth();
  if (!listo) return <Cargando />;
  if (!usuario) return <Navigate to="/login" replace />;
  if (usuario.debe_cambiar_clave) return <Navigate to="/cambiar-clave" replace />;
  if (usuario.rol !== "PLATAFORMA") return <Navigate to={inicio(usuario)} replace />;
  return (
    <PlataformaShell>
      <Outlet />
    </PlataformaShell>
  );
}

export default function App() {
  const { usuario, listo } = useAuth();
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/contacto" element={<Contacto />} />
      <Route path="/servicios" element={<Servicios />} />
      <Route path="/login" element={listo && usuario ? <Navigate to={usuario.debe_cambiar_clave ? "/cambiar-clave" : inicio(usuario)} replace /> : <Login />} />
      <Route path="/cambiar-clave" element={<CambiarClave />} />
      <Route path="/propietario" element={<Navigate to="/plataforma/solicitudes" replace />} />
      <Route path="/solicitudes" element={<Navigate to="/plataforma/solicitudes" replace />} />
      <Route element={<ZonaCliente />}>
        <Route path="/panel" element={<Panel />} />
        <Route path="/registro" element={<Registro />} />
        <Route path="/sanidad" element={<Sanidad />} />
        <Route path="/camara" element={<Camara />} />
        <Route path="/alertas" element={<Alertas />} />
        <Route path="/lotes" element={<Lotes />} />
        <Route path="/instalaciones" element={<Instalaciones />} />
        <Route path="/config" element={<Configuracion />} />
      </Route>
      <Route element={<ZonaPlataforma />}>
        <Route path="/plataforma/clientes" element={<Clientes />} />
        <Route path="/plataforma/clientes/:id" element={<ClienteDetalle />} />
        <Route path="/plataforma/solicitudes" element={<Propietario />} />
        <Route path="/plataforma/cuentas" element={<CuentasPlataforma />} />
      </Route>
      <Route path="*" element={<Navigate to={usuario ? inicio(usuario) : "/"} replace />} />
    </Routes>
  );
}
