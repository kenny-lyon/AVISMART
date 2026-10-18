import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

type Respuesta = { mensaje: string; minutos: number; enlace_desarrollo?: string };

export default function OlvideClave() {
  const [email, setEmail] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState("");
  const [respuesta, setRespuesta] = useState<Respuesta | null>(null);

  async function enviar(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setEnviando(true);
    try {
      setRespuesta(await api<Respuesta>("/auth/olvide-clave", { method: "POST", body: JSON.stringify({ email }) }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo enviar el pedido");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="login">
      <section className="login-side">
        <div>
          <Link to="/" className="logo-inicio" aria-label="Ir al inicio de AviSmart" title="Ir al inicio">
            <img className="mark" src="/images/avismart-logo.png" alt="" />
          </Link>
          <h1>Recupera tu acceso.</h1>
          <p>Te enviaremos un enlace a tu correo para que crees una clave nueva. Por seguridad, se cerrarán las sesiones abiertas de tu cuenta.</p>
        </div>
        <small>Acceso privado · AviSmart</small>
      </section>
      <section className="login-panel">
        <div className="card login-card">
          {respuesta ? (
            <>
              <h2>Revisa tu correo</h2>
              <p className="hint">
                {respuesta.mensaje}. El enlace vence en {respuesta.minutos} minutos y sirve una sola vez. Si no lo ves, revisa la carpeta de spam.
              </p>
              {respuesta.enlace_desarrollo && (
                <div className="dev-enlace">
                  <b>Modo desarrollo:</b> el envío de correos aún no está configurado.
                  <a href={respuesta.enlace_desarrollo}>Abrir enlace para crear la clave</a>
                </div>
              )}
              <Link className="btn full" to="/login">Volver a iniciar sesión</Link>
            </>
          ) : (
            <form onSubmit={enviar}>
              <h2>¿Olvidaste tu clave?</h2>
              <p className="hint">Escribe el correo con el que entras a AviSmart.</p>
              {error && <div className="error">{error}</div>}
              <label htmlFor="email">Correo</label>
              <input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username" autoFocus required />
              <button className="btn full" disabled={enviando}>{enviando ? "Enviando…" : "Enviar enlace"}</button>
              <p className="hint access-note">
                ¿No tienes acceso a ese correo? Pide a tu productor o al equipo de AviSmart que restablezca tu clave.
              </p>
              <p className="hint" style={{ marginTop: 16, marginBottom: 0 }}>
                <Link to="/login">Volver a iniciar sesión</Link>
              </p>
            </form>
          )}
        </div>
      </section>
    </div>
  );
}
