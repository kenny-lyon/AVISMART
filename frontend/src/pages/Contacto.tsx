import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import "./landing.css";

export default function Contacto() {
  const [menu, setMenu] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [enviado, setEnviado] = useState(false);
  const [error, setError] = useState("");

  async function enviar(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setEnviando(true);
    setError("");
    const formulario = e.currentTarget;
    const datos = new FormData(formulario);
    try {
      await api("/contacto", { method: "POST", body: JSON.stringify(Object.fromEntries(datos.entries())) });
      formulario.reset();
      setEnviado(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo enviar la solicitud");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="pf-page contact-page">
      <header className="pf-header contact-header">
        <Link className="pf-brand" to="/"><img className="pf-brand-mark" src="/images/avismart-logo.png" alt="" /><span><strong>AviSmart</strong><small>Gestión avícola</small></span></Link>
        <button className="pf-menu-button" type="button" aria-label="Abrir menú" aria-expanded={menu} onClick={() => setMenu(!menu)}><span/><span/><span/></button>
        <nav className={menu ? "pf-nav open" : "pf-nav"} onClick={() => setMenu(false)}>
          <a href="/#solucion">Qué resuelve</a>
          <a href="/#funciones">Funcionalidades</a>
          <Link to="/servicios">Servicios</Link>
          <Link to="/contacto">Contacto</Link>
        </nav>
        <div className="pf-header-actions contact-header-actions">
          {/* DEMO oculto por ahora:
          <Link className="pf-link-button" to="/login">Iniciar sesión</Link>
          <a className="pf-button yellow" href="#formulario">Solicitar demo</a> */}
          <Link className="pf-button yellow" to="/login">Iniciar sesión</Link>
        </div>
      </header>
      <main className="contact-wrap">
        <section className="contact-copy">
          <p className="pf-eyebrow"><span/>Estamos para ayudarte</p>
          <h1>Hablemos sobre tu granja avícola.</h1>
          {/* DEMO oculto por ahora: "Solicita una demostración, consulta un plan…" */}
          <p>Consulta un plan o cuéntanos qué necesita tu operación. Esta solicitud no crea una cuenta automáticamente.</p>
          <div className="contact-points">
            {/* DEMO oculto por ahora: <div><strong>Demo personalizada</strong><span>Usamos ejemplos acordes con tu escala y operación.</span></div> */}
            <div><strong>Onboarding acompañado</strong><span>Configuramos contigo la primera granja avícola y sus galpones.</span></div>
            <div><strong>Acceso controlado</strong><span>Las credenciales se entregan después de validar al cliente.</span></div>
          </div>
        </section>
        <section className="contact-card" id="formulario">
          {enviado ? (
            <div className="contact-success">
              <span>✓</span><h2>Solicitud recibida</h2>
              <p>El equipo de AviSmart revisará tus datos y se pondrá en contacto contigo.</p>
              <button className="pf-button yellow" onClick={() => setEnviado(false)}>Enviar otra solicitud</button>
            </div>
          ) : (
            <form className="contact-form" onSubmit={enviar}>
              <h2>Cuéntanos sobre tu operación</h2>
              {error && <div className="error">{error}</div>}
              <div className="contact-grid">
                <label>Nombre completo *<input name="nombre" required minLength={3} /></label>
                <label>Correo electrónico *<input name="email" type="email" required /></label>
                <label>Empresa o granja avícola<input name="empresa" /></label>
                <label>País *<input name="pais" value="Perú" readOnly aria-readonly="true" title="Por ahora atendemos solo en Perú" /></label>
                <label>Número de aves por ciclo
                  <select name="aves" defaultValue=""><option value="">Seleccionar</option><option>Menos de 5 000</option><option>5 000 a 20 000</option></select>
                </label>
                <label>Motivo *
                  <select name="motivo" defaultValue="COMERCIAL" required>{/* DEMO oculto por ahora: <option value="DEMO">Solicitar demostración</option> */}<option value="COMERCIAL">Consulta comercial</option><option value="SOPORTE">Soporte técnico</option><option value="ALIANZA">Alianza o integración</option></select>
                </label>
                <label>Plan de interés
                  <select name="plan" defaultValue="POR_DEFINIR"><option value="POR_DEFINIR">Aún no lo sé</option><option value="BASICO">Básico</option></select>
                </label>
                <label className="wide">Mensaje *<textarea name="mensaje" rows={5} minLength={10} required placeholder="Cuéntanos cómo manejas actualmente tu producción…" /></label>
              </div>
              <button className="pf-button yellow large" disabled={enviando}>{enviando ? "Enviando…" : "Enviar solicitud"}</button>
              <small>Usaremos estos datos únicamente para responder y dar seguimiento a tu solicitud.</small>
            </form>
          )}
        </section>
      </main>
      <footer className="pf-footer">
        <div className="pf-container pf-footer-grid">
          <div>
            <Link className="pf-brand footer" to="/"><img className="pf-brand-mark" src="/images/avismart-logo.png" alt="" /><span><strong>AviSmart</strong><small>Gestión avícola</small></span></Link>
            <p>Software para el seguimiento de pollos de engorde, desde el ingreso de los pollitos hasta la venta, galpón por galpón.</p>
          </div>
          <div><strong>Plataforma</strong><a href="/#funciones">Funcionalidades</a><Link to="/servicios">Servicios</Link><Link to="/login">Iniciar sesión</Link></div>
          <div><strong>Contacto</strong>{/* DEMO oculto por ahora: <Link to="/contacto">Solicitar demo</Link> */}<Link to="/contacto">Soporte</Link></div>
        </div>
        <div className="pf-container pf-footer-bottom"><span>© 2026 AviSmart</span><span>Gestión responsable para producción avícola.</span></div>
      </footer>
    </div>
  );
}
