import { useEffect, useState } from "react";
import { api, type TelegramEstado } from "../../api";
import Cuentas from "../../components/Cuentas";
import { Estado, PageHeader, Panel, mensajeError, useToast } from "../../components/ui";

export default function CuentasPlataforma() {
  const avisar = useToast();
  const [telegram, setTelegram] = useState<TelegramEstado | null>(null);
  const [probando, setProbando] = useState(false);

  useEffect(() => {
    api<TelegramEstado>("/notificaciones/estado").then(setTelegram).catch((err) => avisar(mensajeError(err), "riesgo"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function probarTelegram() {
    setProbando(true);
    try {
      await api("/notificaciones/probar", { method: "POST" });
      avisar("Telegram recibió el mensaje de prueba.");
    } catch (err) {
      avisar(mensajeError(err, "No se pudo probar Telegram"), "riesgo");
    } finally {
      setProbando(false);
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Plataforma"
        titulo="Cuentas de plataforma"
        descripcion="Personas del equipo AviSmart que administran clientes y solicitudes. No ven datos productivos."
      />
      <Cuentas roles={["PLATAFORMA"]} titulo="Equipo AviSmart" descripcion="Tendrán los mismos permisos que tú." />
      <Panel
        titulo="Notificaciones por Telegram"
        descripcion="Canal de la plataforma (TELEGRAM_CHAT_ID): aquí llegan los avisos de solicitudes nuevas confirmadas. Las alertas de los clientes van solo al chat que cada cliente vincula."
        acciones={telegram && <Estado valor={telegram.configurado ? "ACTIVO" : "INACTIVO"} texto={telegram.configurado ? "Configurado" : "No configurado"} />}
      >
        {telegram?.configurado ? (
          <button className="btn secondary" type="button" disabled={probando} onClick={probarTelegram}>
            {probando ? "Enviando…" : "Enviar mensaje de prueba"}
          </button>
        ) : (
          <p className="muted" style={{ margin: 0 }}>Completa TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID en backend/.env y reinicia la API.</p>
        )}
      </Panel>
    </>
  );
}
