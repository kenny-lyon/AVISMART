import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api";
import "./landing.css";

type Estado = { tipo: "cargando" } | { tipo: "ok"; nombre: string } | { tipo: "error"; mensaje: string };

/** Página a la que lleva el enlace del correo. Confirma con POST para que los
    escáneres de enlaces de los correos no gasten el token al abrirlo solos. */
export default function Confirmar() {
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const [estado, setEstado] = useState<Estado>({ tipo: "cargando" });
  const enviado = useRef(false);

  useEffect(() => {
    if (enviado.current) return;
    enviado.current = true;
    if (!token) {
      setEstado({ tipo: "error", mensaje: "El enlace está incompleto." });
      return;
    }
    api<{ nombre: string }>("/contacto/confirmar", { method: "POST", body: JSON.stringify({ token }) })
      .then((r) => setEstado({ tipo: "ok", nombre: r.nombre }))
      .catch((err) => setEstado({ tipo: "error", mensaje: err instanceof Error ? err.message : "No se pudo confirmar" }));
  }, [token]);

  return (
    <div className="pf-page confirmar-page">
      <section className="confirmar-card">
        <Link to="/" aria-label="Ir al inicio de AviSmart"><img src="/images/avismart-logo.png" alt="" /></Link>
        {estado.tipo === "cargando" && (
          <>
            <h1>Confirmando tu correo…</h1>
            <p>Un momento, por favor.</p>
          </>
        )}
        {estado.tipo === "ok" && (
          <>
            <div className="confirmar-icono ok">✓</div>
            <h1>¡Correo confirmado!</h1>
            <p>Gracias, {estado.nombre}. Tu solicitud ya llegó al equipo de AviSmart y te responderemos pronto a este correo.</p>
            <Link className="pf-button yellow" to="/">Volver al inicio</Link>
          </>
        )}
        {estado.tipo === "error" && (
          <>
            <div className="confirmar-icono error">!</div>
            <h1>No pudimos confirmar</h1>
            <p>{estado.mensaje}</p>
            <Link className="pf-button yellow" to="/contacto">Ir al formulario de contacto</Link>
          </>
        )}
      </section>
    </div>
  );
}
