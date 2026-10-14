import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth";
import "./landing.css";

const SERVICIOS = [
  // DEMO oculto por ahora:
  // { n: "01", titulo: "Demostración personalizada", texto: "Recorremos AviSmart con ejemplos cercanos al tamaño, tipo de operación y necesidades de tu granja avícola." },
  { n: "01", titulo: "Configuración inicial", texto: "Preparamos la información básica de la granja avícola, los galpones y los parámetros necesarios para comenzar." },
  { n: "02", titulo: "Capacitación del personal", texto: "Explicamos a cada integrante cómo utilizar las funciones correspondientes a su trabajo cotidiano." },
  { n: "03", titulo: "Puesta en marcha del primer galpón", texto: "Acompañamos la apertura de la primera campaña y verificamos que el registro diario quede correctamente establecido." },
  { n: "04", titulo: "Soporte técnico", texto: "Atendemos dudas, problemas de acceso y consultas sobre la operación general de la plataforma." },
  { n: "05", titulo: "Alertas y Telegram", texto: "Ayudamos a configurar los umbrales y el canal de Telegram para que los avisos lleguen al responsable indicado." },
  { n: "06", titulo: "Acompañamiento de adopción", texto: "Revisamos el uso inicial del sistema y ayudamos al equipo a incorporar AviSmart en su rutina de trabajo." },
];

export default function Servicios() {
  const { usuario } = useAuth();
  const [menu, setMenu] = useState(false);
  const entrar = usuario ? "/panel" : "/login";

  return (
    <div className="pf-page services-page">
      <header className="pf-header services-header">
        <Link className="pf-brand" to="/"><img className="pf-brand-mark" src="/images/avismart-logo.png" alt="" /><span><strong>AviSmart</strong><small>Gestión avícola</small></span></Link>
        <button className="pf-menu-button" type="button" aria-label="Abrir menú" aria-expanded={menu} onClick={() => setMenu(!menu)}><span/><span/><span/></button>
        <nav className={menu ? "pf-nav open" : "pf-nav"} onClick={() => setMenu(false)}>
          <a href="/#solucion">Qué resuelve</a>
          <a href="/#funciones">Funcionalidades</a>
          <Link to="/servicios">Servicios</Link>
          <Link to="/contacto">Contacto</Link>
        </nav>
        <div className="pf-header-actions">{/* DEMO oculto por ahora: <Link className="pf-link-button" to={entrar}>{usuario ? "Ir al panel" : "Iniciar sesión"}</Link><Link className="pf-button yellow" to="/contacto">Solicitar demo</Link> */}<Link className="pf-button yellow" to={entrar}>{usuario ? "Ir al panel" : "Iniciar sesión"}</Link></div>
      </header>

      <main>
        <section className="services-hero">
          <img src="/images/avismart-hero-broiler.webp" alt="Galpón moderno con pollos de engorde" />
          <div className="services-hero-shade" />
          <div className="pf-container services-hero-content">
            <p className="pf-eyebrow light"><span/>Servicios AviSmart</p>
            <h1>No entregamos solo un sistema. Te ayudamos a ponerlo en marcha.</h1>
            {/* DEMO oculto por ahora: "Desde la primera demostración hasta la adopción…" */}
            <p>Desde la configuración inicial hasta la adopción por el equipo, acompañamos la incorporación de AviSmart en la operación de la granja avícola.</p>
            <Link className="pf-button yellow large" to="/contacto">Hablar con nosotros</Link>
          </div>
        </section>

        <section className="services-intro">
          <div className="pf-container services-intro-grid">
            <p className="pf-eyebrow"><span/>Acompañamiento real</p>
            <h2>La tecnología funciona mejor cuando el equipo sabe cómo aprovecharla.</h2>
            <p>AviSmart se adapta al trabajo de una granja avícola de engorde. Por eso combinamos la plataforma con configuración, capacitación y seguimiento durante los primeros pasos.</p>
          </div>
        </section>

        <section className="services-list-section">
          <div className="pf-container services-grid">
            {SERVICIOS.map((servicio) => (
              <article key={servicio.n} className={servicio.n === "01" ? "featured" : ""}>
                <span>{servicio.n}</span><div><h2>{servicio.titulo}</h2><p>{servicio.texto}</p></div>
                <Link to="/contacto" aria-label={`Consultar sobre ${servicio.titulo}`}>→</Link>
              </article>
            ))}
          </div>
        </section>

        <section className="services-process">
          <div className="pf-container">
            <div className="services-process-heading"><p className="pf-eyebrow"><span/>Así trabajamos</p><h2>Un inicio ordenado, sin dejar al equipo solo.</h2></div>
            <div className="services-process-grid"><article><b>1</b><h3>Conocemos tu operación</h3><p>Revisamos cómo registran actualmente sus galpones y qué dificultades necesitan resolver.</p></article><article><b>2</b><h3>Configuramos contigo</h3><p>Preparamos AviSmart y realizamos el recorrido inicial con las personas responsables.</p></article><article><b>3</b><h3>Acompañamos el arranque</h3><p>Resolvemos dudas durante el primer uso y ajustamos el flujo cuando sea necesario.</p></article></div>
          </div>
        </section>

        <section className="services-cta"><div className="pf-container"><div><p className="pf-eyebrow light"><span/>Siguiente paso</p><h2>Conversemos sobre tu granja avícola.</h2>{/* DEMO oculto por ahora: <p>Solicita una demostración y cuéntanos cómo manejas actualmente tu producción.</p> */}<p>Si ya trabajas con AviSmart, ingresa con tu cuenta.</p></div>{/* DEMO oculto por ahora: <Link className="pf-button yellow large" to="/contacto">Solicitar demostración</Link> */}<Link className="pf-button yellow large" to={entrar}>{usuario ? "Ir al panel" : "Iniciar sesión"}</Link></div></section>
      </main>

      <footer className="pf-footer"><div className="pf-container pf-footer-grid"><div><Link className="pf-brand footer" to="/"><img className="pf-brand-mark" src="/images/avismart-logo.png" alt="" /><span><strong>AviSmart</strong><small>Gestión avícola</small></span></Link><p>Software para el seguimiento de pollos de engorde, desde el ingreso de los pollitos hasta la venta, galpón por galpón.</p></div><div><strong>Plataforma</strong><a href="/#funciones">Funcionalidades</a><Link to="/servicios">Servicios</Link><Link to="/login">Iniciar sesión</Link></div><div><strong>Contacto</strong>{/* DEMO oculto por ahora: <Link to="/contacto">Solicitar demo</Link> */}<Link to="/contacto">Soporte</Link></div></div><div className="pf-container pf-footer-bottom"><span>© 2026 AviSmart</span><span>Gestión responsable para producción avícola.</span></div></footer>
    </div>
  );
}
