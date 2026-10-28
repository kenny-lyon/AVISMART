import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import "./landing.css";
import { LARGO_NOMBRE, alEscribir } from "../textos";

type Turnstile = {
  render: (el: HTMLElement, opciones: Record<string, unknown>) => string;
  reset: (id?: string) => void;
};
type Envio = { mensaje: string; horas_para_confirmar: number; enlace_desarrollo?: string };

/** Carga el widget antibots de Cloudflare solo si el servidor tiene la clave configurada. */
function useTurnstile(contenedor: React.RefObject<HTMLDivElement | null>, activo: boolean) {
  const [sitekey, setSitekey] = useState<string | null>(null);
  const widget = useRef<string | null>(null);

  useEffect(() => {
    api<{ turnstile_sitekey: string | null }>("/contacto/config")
      .then((c) => setSitekey(c.turnstile_sitekey))
      .catch(() => setSitekey(null));
  }, []);

  useEffect(() => {
    if (!sitekey || !activo) return;
    const pintar = () => {
      const ts = (window as unknown as { turnstile?: Turnstile }).turnstile;
      if (ts && contenedor.current && !widget.current) {
        widget.current = ts.render(contenedor.current, { sitekey, language: "es", theme: "light" });
      }
    };
    if (!document.getElementById("cf-turnstile")) {
      const script = document.createElement("script");
      script.id = "cf-turnstile";
      script.src = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
      script.async = true;
      script.onload = pintar;
      document.head.appendChild(script);
    } else {
      pintar();
    }
    return () => {
      widget.current = null;
    };
  }, [sitekey, activo, contenedor]);

  function reiniciar() {
    (window as unknown as { turnstile?: Turnstile }).turnstile?.reset(widget.current ?? undefined);
  }

  return { requerido: !!sitekey, reiniciar };
}

export default function Contacto() {
  const [menu, setMenu] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [enviado, setEnviado] = useState<(Envio & { correo: string }) | null>(null);
  const [error, setError] = useState("");
  const cajaTurnstile = useRef<HTMLDivElement>(null);
  const turnstile = useTurnstile(cajaTurnstile, !enviado);

  async function enviar(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    const formulario = e.currentTarget;
    const datos = Object.fromEntries(new FormData(formulario).entries()) as Record<string, string>;
    const token = datos["cf-turnstile-response"] ?? "";
    delete datos["cf-turnstile-response"];
    if (turnstile.requerido && !token) {
      setError("Espera a que termine la verificación antibots antes de enviar.");
      return;
    }
    setEnviando(true);
    try {
      const respuesta = await api<Envio>("/contacto", { method: "POST", body: JSON.stringify({ ...datos, turnstile_token: token }) });
      setEnviado({ ...respuesta, correo: datos.email });
      formulario.reset();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo enviar la solicitud");
      turnstile.reiniciar();
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
          <p>Consulta un plan o cuéntanos qué necesita tu operación avicola.</p>
          <div className="contact-points">
            {/* DEMO oculto por ahora: <div><strong>Demo personalizada</strong><span>Usamos ejemplos acordes con tu escala y operación.</span></div> */}
            <div><strong>Onboarding acompañado</strong><span>Configuramos contigo la primera granja avícola y sus galpones.</span></div>
            <div><strong>Acceso controlado</strong><span>Una vez validada tu solicitud, recibirás tus credenciales de acceso.</span></div>
          </div>
        </section>
        <section className="contact-card" id="formulario">
          {enviado ? (
            <div className="contact-success">
              <span>✉</span><h2>Revisa tu correo</h2>
              <p>
                Enviamos un enlace de confirmación a <b>{enviado.correo}</b>. Ábrelo en las próximas{" "}
                {enviado.horas_para_confirmar} horas para que tu solicitud llegue a nuestro equipo.
              </p>
              <p className="contact-nota">¿No lo ves? Revisa la carpeta de spam o promociones.</p>
              {enviado.enlace_desarrollo && (
                <p className="contact-nota">
                  ¿Prefieres hacerlo ahora? <a href={enviado.enlace_desarrollo}>Confirmar mi correo</a>
                </p>
              )}
              <button className="pf-button yellow" onClick={() => setEnviado(null)}>Enviar otra solicitud</button>
            </div>
          ) : (
            <form className="contact-form" onSubmit={enviar}>
              <h2>Cuéntanos sobre tu operación</h2>
              {error && <div className="error">{error}</div>}
              <div className="contact-grid">
                <label>Nombre completo *<input name="nombre" required minLength={3} maxLength={LARGO_NOMBRE} onInput={alEscribir("persona")} /></label>
                <label>Correo electrónico *<input name="email" type="email" required /></label>
                <label>Celular (opcional)
                  <input name="telefono" type="tel" inputMode="tel" maxLength={20} pattern="[+0-9 \-]{9,20}" placeholder="Ejm: 987 654 321"
                    title="Celular de 9 dígitos que empieza con 9" />
                </label>
                <label>Empresa o granja avícola<input name="empresa" maxLength={LARGO_NOMBRE} onInput={alEscribir("lugar")} /></label>
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
                <label className="wide">Mensaje *<textarea name="mensaje" rows={5} minLength={10} maxLength={1500} required placeholder="Cuéntanos cómo manejas actualmente tu producción…" /></label>
                {/* Campo trampa: invisible para las personas; los bots suelen llenarlo. */}
                <label className="campo-trampa" aria-hidden="true">Sitio web<input name="sitio_web" tabIndex={-1} autoComplete="off" /></label>
              </div>
              {turnstile.requerido && <div className="contact-turnstile" ref={cajaTurnstile} />}
              <button className="pf-button yellow large" disabled={enviando}>{enviando ? "Enviando…" : "Enviar solicitud"}</button>
              <small>Te enviaremos un correo para confirmar tu dirección. Usaremos estos datos únicamente para responder tu solicitud.</small>
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
