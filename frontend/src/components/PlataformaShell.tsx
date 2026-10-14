import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { api, type SolicitudContacto } from "../api";
import { useAuth } from "../auth";
import Layout from "./Layout";

/** Marco del propietario de AviSmart: administra clientes, no opera granjas avícolas. */
export default function PlataformaShell({ children }: { children: React.ReactNode }) {
  const { usuario } = useAuth();
  const { pathname } = useLocation();
  const [nuevas, setNuevas] = useState(0);

  useEffect(() => {
    const contar = () =>
      api<SolicitudContacto[]>("/plataforma/solicitudes")
        .then((lista) => setNuevas(lista.filter((s) => s.estado === "NUEVA").length))
        .catch(() => setNuevas(0));
    contar();
    window.addEventListener("avismart:cambios", contar);
    const intervalo = window.setInterval(contar, 60_000);
    return () => {
      window.removeEventListener("avismart:cambios", contar);
      window.clearInterval(intervalo);
    };
  }, [pathname]);

  return (
    <Layout
      subtitulo="Plataforma"
      grupos={[
        {
          titulo: "Comercial",
          items: [
            { to: "/plataforma/clientes", label: "Clientes", icono: "clientes" },
            { to: "/plataforma/solicitudes", label: "Solicitudes", icono: "solicitudes", contador: nuevas },
          ],
        },
        { titulo: "Equipo", items: [{ to: "/plataforma/cuentas", label: "Cuentas de plataforma", icono: "cuentas" }] },
      ]}
      contexto={
        <>
          <small>Propietario de la plataforma</small>
          <strong>{usuario?.nombre}</strong>
        </>
      }
    >
      {children}
    </Layout>
  );
}
