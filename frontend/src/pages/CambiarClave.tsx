import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { inicio } from "../api";
import { useAuth } from "../auth";

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
          <p className="hint">Usa al menos 10 caracteres y no compartas tu clave.</p>
          {error && <div className="error">{error}</div>}
          <label>Clave temporal</label>
          <input type="password" value={actual} onChange={(e) => setActual(e.target.value)} autoComplete="current-password" required />
          <label>Nueva clave</label>
          <input type="password" minLength={10} value={nueva} onChange={(e) => setNueva(e.target.value)} autoComplete="new-password" required />
          <label>Confirmar nueva clave</label>
          <input type="password" minLength={10} value={confirmacion} onChange={(e) => setConfirmacion(e.target.value)} autoComplete="new-password" required />
          <button className="btn full" disabled={guardando}>{guardando ? "Guardando…" : "Guardar nueva clave"}</button>
          <button className="btn secondary full" type="button" onClick={salir}>Cancelar y salir</button>
        </form>
      </section>
    </div>
  );
}
