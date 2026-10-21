import { useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth";
import "./landing.css";

type IconName = "chart" | "alert" | "health" | "climate" | "users" | "report";

function Icon({ name }: { name: IconName }) {
  const paths: Record<IconName, ReactNode> = {
    chart: <><path d="M4 19V9"/><path d="M10 19V5"/><path d="M16 19v-7"/><path d="M22 19H2"/></>,
    alert: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"/><path d="M10 21h4"/></>,
    health: <><path d="M12 21s-8-4.6-8-11a4.5 4.5 0 0 1 8-2.8A4.5 4.5 0 0 1 20 10c0 6.4-8 11-8 11Z"/><path d="M9 12h6M12 9v6"/></>,
    climate: <><path d="M14 14.8V5a2 2 0 0 0-4 0v9.8a4 4 0 1 0 4 0Z"/><path d="M12 9v7"/></>,
    users: <><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></>,
    report: <><path d="M4 3h16v18H4z"/><path d="M8 8h8M8 12h8M8 16h5"/></>,
  };
  return <svg viewBox="0 0 24 24" aria-hidden="true">{paths[name]}</svg>;
}

const FUNCIONES: { icono: IconName; titulo: string; texto: string }[] = [
  { icono: "chart", titulo: "Control diario", texto: "Registra peso, mortalidad, alimento y agua sin perder el historial de la campaña." },
  { icono: "alert", titulo: "Alertas oportunas", texto: "Detecta desviaciones en tus galpones y deja cada aviso disponible para su atención." },
  { icono: "health", titulo: "Sanidad validada", texto: "Ordena vacunas, tratamientos y periodos de carencia con intervención veterinaria." },
  { icono: "climate", titulo: "Clima del galpón", texto: "Relaciona temperatura y humedad con el comportamiento productivo del galpón." },
  { icono: "users", titulo: "Trabajo por roles", texto: "Productor, operario y veterinario ven lo que les corresponde." },
  { icono: "report", titulo: "Cierre con reportes", texto: "Consolida resultados técnicos y económicos en documentos PDF y Excel." },
];

const PASOS = [
  ["01", "Configura tu galpón", "Registra el galpón, la línea genética, la población y la fecha de ingreso."],
  ["02", "Actualiza cada día", "El personal carga los datos del galpón y AviSmart calcula los indicadores."],
  ["03", "Actúa a tiempo", "Las alertas y validaciones ayudan a priorizar decisiones productivas y sanitarias."],
];

export default function Landing() {
  const { usuario } = useAuth();
  const [menu, setMenu] = useState(false);
  const entrar = usuario ? "/panel" : "/login";

  return (
    <div className="pf-page">
      <header className="pf-header">
        <Link className="pf-brand" to="/" aria-label="AviSmart, inicio">
          <img className="pf-brand-mark" src="/images/avismart-logo.png" alt="" />
          <span><strong>AviSmart</strong><small>Gestión avícola</small></span>
        </Link>
        <button className="pf-menu-button" type="button" aria-label="Abrir menú" aria-expanded={menu} onClick={() => setMenu(!menu)}>
          <span/><span/><span/>
        </button>
        <nav className={menu ? "pf-nav open" : "pf-nav"} onClick={() => setMenu(false)}>
          <a href="#solucion">Qué resuelve</a>
          <a href="#funciones">Funcionalidades</a>
          <Link to="/servicios">Servicios</Link>
          <Link to="/contacto">Contacto</Link>
        </nav>
        <div className="pf-header-actions">
          {/* DEMO oculto por ahora: al reactivar, volver a usar el enlace simple y el botón de demo.
          <Link className="pf-link-button" to={entrar}>{usuario ? "Ir al panel" : "Iniciar sesión"}</Link>
          <Link className="pf-button yellow" to="/contacto">Solicitar demo</Link> */}
          <Link className="pf-button yellow" to={entrar}>{usuario ? "Ir al panel" : "Iniciar sesión"}</Link>
        </div>
      </header>

      <main>
        <section className="pf-hero">
          <video
            className="pf-hero-image"
            src="/images/Crear_video_de_pollo_picoteando_20261014142323.mp4"
            poster="/images/avismart-hero-broiler.webp"
            autoPlay
            muted
            loop
            playsInline
            preload="auto"
            aria-label="Pollo de engorde picoteando en un galpón avícola moderno"
          />
          <div className="pf-hero-shade" />
          <div className="pf-container pf-hero-grid">
            <div className="pf-hero-copy">
              <p className="pf-eyebrow light"><span/>Software para pollos de engorde</p>
              <h1>Tus galpones, bajo control.</h1>
              <p className="pf-hero-lead">AviSmart reúne producción, sanidad y ambiente para que cada decisión se tome con información del día.</p>
              <div className="pf-actions">
                {/* DEMO oculto por ahora: <Link className="pf-button yellow large" to="/contacto">Solicitar una demostración</Link> */}
                <Link className="pf-button yellow large" to={entrar}>{usuario ? "Ir al panel" : "Iniciar sesión"}</Link>
                <a className="pf-button glass large" href="#funciones">Conocer el sistema</a>
              </div>
              <div className="pf-trust"><span>Sin registro público</span><span>Acceso por roles</span><span>Datos de cada campaña</span></div>
            </div>
          </div>
          <a className="pf-scroll" href="#solucion"><span/>Descubrir AviSmart</a>
        </section>

        <section className="pf-strip" aria-label="Resumen del sistema">
          <div className="pf-container">
            <div><strong>Un solo registro</strong><span>para todo el galpón</span></div>
            <div><strong>Indicadores diarios</strong><span>sin cálculos manuales</span></div>
            <div><strong>Sanidad trazable</strong><span>con validación veterinaria</span></div>
            <div><strong>Decisiones oportunas</strong><span>con alertas claras</span></div>
          </div>
        </section>

        <section className="pf-section pf-intro" id="solucion">
          <div className="pf-container pf-intro-grid">
            <div className="pf-dashboard-scene">
              <div className="pf-window">
                <div className="pf-window-bar"><i/><i/><i/><span>Panel del galpón</span></div>
                <div className="pf-window-body">
                  <aside><img src="/images/avismart-logo.png" alt="" /><span className="active"/><span/><span/><span/></aside>
                  <div className="pf-window-content">
                    <div className="pf-skeleton-title"><span/><i/></div>
                    <div className="pf-kpi-row"><div><small>Aves vivas</small><b>4 837</b></div><div><small>Mortalidad</small><b>3,26%</b></div><div><small>FCR</small><b>1,18</b></div></div>
                    <div className="pf-ui-grid"><div className="pf-ui-chart"><span/><span/><span/><span/><span/><svg viewBox="0 0 240 80" preserveAspectRatio="none"><path d="M0 68C28 63 42 54 68 57s40-20 66-16 35-23 55-17 26-15 51-19"/></svg></div><div className="pf-ui-side"><b>Estado</b><span>Clima estable</span><span>Peso en rango</span><span>Vacuna pendiente</span></div></div>
                  </div>
                </div>
              </div>
              <div className="pf-floating-note"><Icon name="alert"/><span><small>Nueva alerta</small><strong>Temperatura fuera de rango</strong></span></div>
            </div>
            <div className="pf-intro-copy">
              <p className="pf-eyebrow"><span/>Información que sí ayuda</p>
              <h2>Del cuaderno a una visión completa de la campaña.</h2>
              <p>Los datos del engorde suelen quedar separados entre hojas, mensajes y personas. AviSmart los organiza alrededor de tus galpones para que producción y sanidad trabajen con la misma información.</p>
              <ul className="pf-checks"><li>Historial diario sin registros duplicados.</li><li>Curvas Ross 308, Cobb 500, Hubbard y Arbor Acres para comparar el peso.</li><li>Alertas que conservan su seguimiento.</li><li>Cierre productivo y económico de la campaña.</li></ul>
              {/* DEMO oculto por ahora: <Link className="pf-text-link" to="/contacto">Conocer AviSmart con una demo <span>→</span></Link> */}
              <Link className="pf-text-link" to={entrar}>{usuario ? "Ir al panel" : "Iniciar sesión"} <span>→</span></Link>
            </div>
          </div>
        </section>

        <section className="pf-section pf-features" id="funciones">
          <div className="pf-container">
            <div className="pf-section-heading"><div><p className="pf-eyebrow"><span/>Lo esencial del engorde</p><h2>Una plataforma construida alrededor de tus galpones.</h2></div><p>Funciones concretas para registrar, interpretar y actuar, sin añadir complejidad innecesaria al trabajo diario.</p></div>
            <div className="pf-feature-grid">
              {FUNCIONES.map((item, index) => <article key={item.titulo}><span className="pf-feature-number">0{index + 1}</span><div className="pf-feature-icon"><Icon name={item.icono}/></div><h3>{item.titulo}</h3><p>{item.texto}</p></article>)}
            </div>
          </div>
        </section>

        <section className="pf-process" id="como">
          <div className="pf-container">
            <div className="pf-process-heading"><p className="pf-eyebrow light"><span/>De principio a fin</p><h2>La campaña avanza. La información también.</h2><p>Desde el ingreso de las aves hasta el cierre, cada etapa queda conectada con la siguiente.</p></div>
            <div className="pf-step-grid">{PASOS.map(([numero, titulo, texto]) => <article key={numero}><span>{numero}</span><div/><h3>{titulo}</h3><p>{texto}</p></article>)}</div>
          </div>
        </section>

        <section className="pf-section pf-roles">
          <div className="pf-container pf-roles-grid">
            <div><p className="pf-eyebrow"><span/>Un equipo, una campaña</p><h2>Cada persona ve lo que necesita para trabajar.</h2><p>AviSmart protege las funciones por rol y mantiene a todos dentro del mismo flujo de información.</p></div>
            <div className="pf-role-list"><article><b>01</b><span><strong>Productor</strong><small>Supervisa los galpones y toma decisiones.</small></span></article><article><b>02</b><span><strong>Operario</strong><small>Registra el trabajo diario del galpón.</small></span></article><article><b>03</b><span><strong>Médico veterinario</strong><small>Valida sanidad, tratamientos y alertas.</small></span></article></div>
          </div>
        </section>

        <section className="pf-cta">
          <div className="pf-container pf-cta-inner"><div><p className="pf-eyebrow light"><span/>Conversemos</p><h2>Tus galpones pueden trabajar mejor informados.</h2>{/* DEMO oculto por ahora: <p>Cuéntanos cómo trabaja tu granja avícola y te mostraremos AviSmart con un recorrido adaptado a tu operación.</p> */}<p>Ingresa con la cuenta que te entregó tu organización para revisar tus galpones.</p></div><div className="pf-cta-actions">{/* DEMO oculto por ahora: <Link className="pf-button yellow large" to="/contacto">Solicitar demostración</Link><Link className="pf-button glass large" to={entrar}>{usuario ? "Ir al panel" : "Ya tengo una cuenta"}</Link> */}<Link className="pf-button yellow large" to={entrar}>{usuario ? "Ir al panel" : "Iniciar sesión"}</Link></div></div>
        </section>
      </main>

      <footer className="pf-footer"><div className="pf-container pf-footer-grid"><div><Link className="pf-brand footer" to="/"><img className="pf-brand-mark" src="/images/avismart-logo.png" alt="" /><span><strong>AviSmart</strong><small>Gestión avícola</small></span></Link><p>Software para el seguimiento de pollos de engorde, desde el ingreso de los pollitos hasta la venta, galpón por galpón.</p></div><div><strong>Plataforma</strong><a href="#funciones">Funcionalidades</a><Link to="/servicios">Servicios</Link><Link to="/login">Iniciar sesión</Link></div><div><strong>Contacto</strong>{/* DEMO oculto por ahora: <Link to="/contacto">Solicitar demo</Link> */}<Link to="/contacto">Soporte</Link></div></div><div className="pf-container pf-footer-bottom"><span>© 2026 AviSmart</span><span>Gestión responsable para producción avícola.</span></div></footer>
    </div>
  );
}
