import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { inicio } from "../api";
import { useAuth } from "../auth";

export default function Login() {
  const { entrar } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setCargando(true);
    try {
      const usuario = await entrar(email, password);
      navigate(usuario.debe_cambiar_clave ? "/cambiar-clave" : inicio(usuario));
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo entrar");
    } finally {
      setCargando(false);
    }
  }

  return (
    <div className="login">
      <section className="login-side">
        <div>
          <Link to="/" className="logo-inicio" aria-label="Ir al inicio de AviSmart" title="Ir al inicio">
            <img className="mark" src="/images/avismart-logo.png" alt="" />
          </Link>
          <h1>Tus galpones, en un solo lugar.</h1>
          <p>
            AviSmart lleva el engorde día a día: peso, mortalidad, alimento y el clima del galpón.
            Si la sanidad se sale de rango, el aviso queda para el veterinario y el productor.
          </p>
        </div>
        <small>Granja avícola de engorde · Puno</small>
      </section>
      <section className="login-panel">
        <form className="card login-card" onSubmit={submit}>
          <h2>Entrar</h2>
          <p className="hint">Acceso privado para personal autorizado de la granja avícola.</p>
          {error && <div className="error">{error}</div>}
          <label>Correo</label>
          <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" autoComplete="username" required />
          <label>Clave</label>
          <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" autoComplete="current-password" required />
          <button className="btn full" disabled={cargando}>
            {cargando ? "Ingresando…" : "Iniciar sesión"}
          </button>
          <p className="hint access-note">Las cuentas son entregadas por el administrador. AviSmart no permite registro público.</p>
          <p className="hint" style={{ marginTop: 16, marginBottom: 0 }}>
            <Link to="/">Volver a la página de AviSmart</Link>
          </p>
        </form>
      </section>
    </div>
  );
}
