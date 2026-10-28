import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api";
import CampoClave, { problemaClave } from "../components/CampoClave";

export default function RestablecerClave() {
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const [nueva, setNueva] = useState("");
  const [confirmacion, setConfirmacion] = useState("");
  const [error, setError] = useState("");
  const [guardando, setGuardando] = useState(false);
  const [listo, setListo] = useState<string | null>(null);

  async function guardar(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (nueva !== confirmacion) {
      setError("Las claves no coinciden");
      return;
    }
    const problema = problemaClave(nueva);
    if (problema) {
      setError(problema);
      return;
    }
    setGuardando(true);
    try {
      const r = await api<{ email: string }>("/auth/restablecer-clave", {
        method: "POST",
        body: JSON.stringify({ token, clave_nueva: nueva }),
      });
      setListo(r.email);
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
          <Link to="/" className="logo-inicio" aria-label="Ir al inicio de AviSmart" title="Ir al inicio">
            <img className="mark" src="/images/avismart-logo.png" alt="" />
          </Link>
          <h1>Crea tu clave nueva.</h1>
          <p>Usa entre 8 y 15 caracteres, con letras, números y símbolos. Al guardarla se cerrarán todas las sesiones abiertas de tu cuenta.</p>
        </div>
        <small>Acceso privado · AviSmart</small>
      </section>
      <section className="login-panel">
        <div className="card login-card">
          {listo ? (
            <>
              <h2>Clave actualizada</h2>
              <p className="hint">Ya puedes entrar con tu clave nueva. Te enviamos un aviso a tu correo por seguridad.</p>
              <Link className="btn full" to="/login">Iniciar sesión</Link>
            </>
          ) : !token ? (
            <>
              <h2>Enlace incompleto</h2>
              <p className="hint">Abre el enlace completo del correo o pide uno nuevo.</p>
              <Link className="btn full" to="/olvide-clave">Pedir un enlace nuevo</Link>
            </>
          ) : (
            <form onSubmit={guardar}>
              <h2>Nueva clave</h2>
              {error && (
                <div className="error">
                  {error}
                  {/venci|usado/.test(error) && <> <Link to="/olvide-clave">Pedir un enlace nuevo</Link></>}
                </div>
              )}
              <CampoClave id="nueva" label="Nueva clave" value={nueva} onChange={setNueva} autoComplete="new-password" minLength={8} autoFocus reglas />
              <CampoClave id="confirmacion" label="Confirmar nueva clave" value={confirmacion} onChange={setConfirmacion} autoComplete="new-password" minLength={8} />
              <button className="btn full" disabled={guardando}>{guardando ? "Guardando…" : "Guardar clave nueva"}</button>
            </form>
          )}
        </div>
      </section>
    </div>
  );
}
