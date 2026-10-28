import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { inicio } from "../api";
import { useAuth } from "../auth";
import CampoClave, { problemaClave } from "../components/CampoClave";

export default function CambiarClave() {
  const { usuario, cambiarClave, salir } = useAuth();
  const navigate = useNavigate();
  const [actual, setActual] = useState("");
  const [nueva, setNueva] = useState("");
  const [confirmacion, setConfirmacion] = useState("");
  const [error, setError] = useState("");
  const [guardando, setGuardando] = useState(false);

  if (!usuario) return <Navigate to="/login" replace />;
  if (!usuario.debe_cambiar_clave) return <Navigate to={inicio(usuario)} replace />;

  async function guardar(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (nueva !== confirmacion) {
      setError("Las nuevas claves no coinciden");
      return;
    }
    const problema = problemaClave(nueva);
    if (problema) {
      setError(problema);
      return;
    }
    setGuardando(true);
    try {
      await cambiarClave(actual, nueva);
      navigate(usuario ? inicio(usuario) : "/login", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cambiar la clave");
    } finally {
      setGuardando(false);
    }
  }

  return (
    <div className="login">
      <section className="login-side">
        <div>
          <img className="mark" src="/images/avismart-logo.png" alt="" />
          <h1>Protege tu acceso.</h1>
          <p>La clave recibida es temporal. Crea una clave personal antes de comenzar a trabajar en AviSmart.</p>
        </div>
        <small>Acceso privado · AviSmart</small>
      </section>
      <section className="login-panel">
        <form className="card login-card" onSubmit={guardar}>
          <h2>Cambiar clave</h2>
          <p className="hint">Usa entre 8 y 15 caracteres, con letras, números y símbolos, y no compartas tu clave.</p>
          {error && <div className="error">{error}</div>}
          {/* Usuario oculto: así el gestor de contraseñas del navegador guarda la clave nueva en esta cuenta. */}
          <input className="usuario-oculto" type="email" name="username" autoComplete="username" value={usuario.email} readOnly tabIndex={-1} aria-hidden="true" />
          <CampoClave id="actual" label="Clave temporal" value={actual} onChange={setActual} autoComplete="current-password" autoFocus />
          <CampoClave id="nueva" label="Nueva clave" value={nueva} onChange={setNueva} autoComplete="new-password" minLength={8} reglas />
          <CampoClave id="confirmacion" label="Confirmar nueva clave" value={confirmacion} onChange={setConfirmacion} autoComplete="new-password" minLength={8} />
          <button className="btn full" disabled={guardando}>{guardando ? "Guardando…" : "Guardar nueva clave"}</button>
          <button className="btn secondary full" type="button" onClick={salir}>Cancelar y salir</button>
        </form>
      </section>
    </div>
  );
}
