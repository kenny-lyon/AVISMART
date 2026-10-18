import { useEffect, useState } from "react";
import { api, fecha } from "../api";
import { Estado, Icon, Panel, mensajeError, useToast } from "./ui";

type EstadoTelegram = {
  bot_configurado: boolean;
  bot_usuario: string | null;
  vinculado: boolean;
  chat_nombre: string | null;
  vinculado_en: string | null;
};
type Codigo = { codigo: string; minutos: number; bot_usuario: string | null; enlace: string | null };

/** Vincula el chat de Telegram del cliente: solo ahí llegan las alertas de sus lotes. */
export default function TelegramCliente() {
  const avisar = useToast();
  const [estado, setEstado] = useState<EstadoTelegram | null>(null);
  const [codigo, setCodigo] = useState<Codigo | null>(null);
  const [ocupado, setOcupado] = useState(false);

  useEffect(() => {
    api<EstadoTelegram>("/organizacion/telegram").then(setEstado).catch((err) => avisar(mensajeError(err), "riesgo"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function accion(fn: () => Promise<void>) {
    setOcupado(true);
    try {
      await fn();
    } catch (err) {
      avisar(mensajeError(err), "riesgo");
    } finally {
      setOcupado(false);
    }
  }

  const generar = () => accion(async () => setCodigo(await api<Codigo>("/organizacion/telegram/vincular", { method: "POST" })));
  const verificar = () =>
    accion(async () => {
      setEstado(await api<EstadoTelegram>("/organizacion/telegram/verificar", { method: "POST" }));
      setCodigo(null);
      avisar("Chat vinculado. Las alertas de tus lotes llegarán ahí.");
    });
  const probar = () =>
    accion(async () => {
      await api("/organizacion/telegram/probar", { method: "POST" });
      avisar("Telegram recibió el mensaje de prueba.");
    });
  const desvincular = () =>
    accion(async () => {
      if (!window.confirm("Las alertas dejarán de llegar a ese chat. ¿Desvincular?")) return;
      setEstado(await api<EstadoTelegram>("/organizacion/telegram", { method: "DELETE" }));
      avisar("Chat desvinculado.");
    });

  if (!estado) return <p className="muted">Cargando…</p>;

  return (
    <Panel
      titulo="Alertas por Telegram"
      descripcion="Las alertas siempre quedan en AviSmart. Si vinculas un chat (personal o un grupo de tu granja avícola), también llegan ahí. Cada cliente recibe solo las alertas de sus propios lotes."
      acciones={<Estado valor={estado.vinculado ? "ACTIVO" : "INACTIVO"} texto={estado.vinculado ? "Vinculado" : "Sin vincular"} />}
    >
      {!estado.bot_configurado ? (
        <div className="aviso info"><Icon name="aviso" /><span>El bot de Telegram de AviSmart todavía no está configurado. Avisa al equipo de AviSmart.</span></div>
      ) : estado.vinculado ? (
        <>
          <dl className="ficha">
            <dt>Chat</dt><dd>{estado.chat_nombre}</dd>
            <dt>Vinculado</dt><dd>{estado.vinculado_en ? fecha(estado.vinculado_en) : "—"}</dd>
          </dl>
          <div className="actions" style={{ marginTop: 16 }}>
            <button className="btn" type="button" disabled={ocupado} onClick={probar}>Enviar mensaje de prueba</button>
            <button className="btn secondary" type="button" disabled={ocupado} onClick={generar}>Cambiar de chat</button>
            <button className="link-button riesgo" type="button" disabled={ocupado} onClick={desvincular}>Desvincular</button>
          </div>
        </>
      ) : !codigo ? (
        <button className="btn" type="button" disabled={ocupado} onClick={generar}><Icon name="mas" /> Vincular Telegram</button>
      ) : null}

      {codigo && (
        <div className="telegram-pasos">
          <ol>
            <li>
              Abre el bot{" "}
              {codigo.enlace ? <a href={codigo.enlace} target="_blank" rel="noreferrer">@{codigo.bot_usuario}</a> : "de AviSmart"} en Telegram y
              pulsa <b>Iniciar</b>. Para un grupo, agrega el bot al grupo.
            </li>
            <li>
              Envía este código al bot (o al grupo): <code className="codigo-telegram">/start {codigo.codigo}</code>
            </li>
            <li>Vuelve aquí y pulsa <b>Ya lo envié</b>. El código vence en {codigo.minutos} minutos.</li>
          </ol>
          <div className="actions">
            <button className="btn" type="button" disabled={ocupado} onClick={verificar}>{ocupado ? "Verificando…" : "Ya lo envié"}</button>
            <button className="btn secondary" type="button" onClick={() => setCodigo(null)}>Cancelar</button>
          </div>
        </div>
      )}
    </Panel>
  );
}
