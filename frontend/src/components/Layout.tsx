import { useEffect, useState, type ReactNode } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { ROL } from "../api";
import { useAuth } from "../auth";
import { Avatar, Icon, type IconName } from "./ui";

export type NavItem = { to: string; label: string; icono: IconName; contador?: number; urgente?: boolean };
export type NavGrupo = { titulo: string; items: NavItem[] };

/** Marco común del sistema interno: barra lateral, barra superior y contenido. */
export default function Layout({ subtitulo, grupos, contexto, derecha, children }: {
  subtitulo: string;
  grupos: NavGrupo[];
  contexto?: ReactNode;
  derecha?: ReactNode;
  children: ReactNode;
}) {
  const { usuario, salir } = useAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [menu, setMenu] = useState(false);

  useEffect(() => setMenu(false), [pathname]);
  if (!usuario) return null;

  return (
    <div className={menu ? "app menu-abierto" : "app"}>
      <aside className="sidebar">
        <Link className="sidebar-brand" to="/">
          <img src="/images/avismart-logo.png" alt="" />
          <span>
            <strong>AviSmart</strong>
            <small>{subtitulo}</small>
          </span>
        </Link>
        {grupos.map((grupo) => (
          <nav className="nav-grupo" key={grupo.titulo} aria-label={grupo.titulo}>
            <p className="nav-titulo">{grupo.titulo}</p>
            {grupo.items.map((item) => (
              <NavLink key={item.to} to={item.to} className={({ isActive }) => (isActive ? "nav-link activo" : "nav-link")}>
                <Icon name={item.icono} />
                <span>{item.label}</span>
                {!!item.contador && <span className={item.urgente ? "nav-contador riesgo" : "nav-contador"}>{item.contador}</span>}
              </NavLink>
            ))}
          </nav>
        ))}
        <div className="sidebar-usuario">
          <Avatar nombre={usuario.nombre} />
          <div>
            <strong>{usuario.nombre}</strong>
            <small>{ROL[usuario.rol]}</small>
          </div>
          <button
            className="icon-btn"
            type="button"
            title="Cerrar sesión"
            aria-label="Cerrar sesión"
            onClick={() => {
              salir();
              navigate("/login");
            }}
          >
            <Icon name="salir" />
          </button>
        </div>
      </aside>
      <div className="capa-menu" onClick={() => setMenu(false)} />
      <div className="contenido">
        <header className="topbar">
          <button className="icon-btn topbar-menu" type="button" aria-label="Abrir menú" onClick={() => setMenu(true)}>
            <Icon name="menu" />
          </button>
          <div className="topbar-contexto">{contexto}</div>
          <div className="topbar-derecha">{derecha}</div>
        </header>
        <main className="pagina">{children}</main>
      </div>
    </div>
  );
}
