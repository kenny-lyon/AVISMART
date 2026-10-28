import { useEffect, useState } from "react";
import { api, type Rol } from "../api";
import { useAuth } from "../auth";
import Cuentas from "../components/Cuentas";
import MiCuenta from "../components/MiCuenta";
import TelegramCliente from "../components/TelegramCliente";
import { Campo, PageHeader, Panel, Tabs, mensajeError, useToast } from "../components/ui";
import { useLote } from "../lote";
import { valorCampo } from "../textos";

/** Qué cuentas crea y gestiona cada rol del cliente (lo mismo que valida el backend). */
const PERSONAL: Partial<Record<Rol, { crea: Rol[]; gestiona: Rol[] }>> = {
  ADMIN: { crea: ["OPERARIO", "VETERINARIO"], gestiona: ["ADMIN", "PRODUCTOR", "OPERARIO", "VETERINARIO"] },
  PRODUCTOR: { crea: ["OPERARIO", "VETERINARIO"], gestiona: ["OPERARIO", "VETERINARIO"] },
};

export default function Configuracion() {
  const { usuario } = useAuth();
  const { resumen, recargar } = useLote();
  const avisar = useToast();
  const rol = usuario?.rol ?? "OPERARIO";
  const personal = PERSONAL[rol];
  const veUmbral = rol === "VETERINARIO" || rol === "ADMIN";
  const pestanas = [
    ...(personal ? [{ id: "cuentas", label: "Personal" }] : []),
    ...(veUmbral ? [{ id: "parametros", label: "Parámetros de alerta" }] : []),
    ...(personal ? [{ id: "notificaciones", label: "Notificaciones" }] : []),
    { id: "cuenta", label: "Mi cuenta" },
  ];
  const pedida = new URLSearchParams(window.location.search).get("pestana");
  const [pestana, setPestana] = useState(pestanas.some((p) => p.id === pedida) ? pedida! : pestanas[0].id);
  const [umbral, setUmbral] = useState(String(resumen?.umbral_mortalidad ?? 20));
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    if (resumen) setUmbral(String(resumen.umbral_mortalidad));
  }, [resumen]);

  async function guardar(e: React.FormEvent) {
    e.preventDefault();
    setGuardando(true);
    try {
      await api("/umbral", { method: "PUT", body: JSON.stringify({ mortalidad_diaria: Number(umbral) }) });
      await recargar();
      avisar("Umbral actualizado. El próximo registro del día lo va a usar.");
    } catch (err) {
      avisar(mensajeError(err, "No se guardó"), "riesgo");
    } finally {
      setGuardando(false);
    }
  }

  return (
    <>
      <PageHeader
        titulo={personal ? "Personal y ajustes" : veUmbral ? "Parámetros y cuenta" : "Mi cuenta"}
        descripcion={
          personal
            ? `Cuentas del personal de ${resumen?.organizacion.nombre ?? "la organización"}.`
            : veUmbral
              ? "El valor clínico que dispara las alertas de salud y los datos de tu cuenta."
              : "Tus datos de contacto y tus últimos accesos."
        }
      />
      {pestanas.length > 1 && (
        <div style={{ marginBottom: 16 }}>
          <Tabs valor={pestana} onCambio={setPestana} items={pestanas} />
        </div>
      )}

      {pestana === "cuentas" && personal && (
        <Cuentas
          roles={personal.crea}
          gestiona={personal.gestiona}
          titulo="Personal autorizado"
          descripcion={
            rol === "PRODUCTOR"
              ? "Agrega a tus operarios y médicos veterinarios. Cada alta genera una clave temporal."
              : "Cada alta genera una clave temporal que la persona cambia al entrar."
          }
        />
      )}

      {pestana === "notificaciones" && personal && <TelegramCliente />}

      {pestana === "cuenta" && <MiCuenta />}

      {pestana === "parametros" && veUmbral && (
        <Panel titulo="Umbral de mortalidad diaria" descripcion="Lo define el médico veterinario según el estado sanitario del lote.">
          <form onSubmit={guardar} style={{ maxWidth: 420 }}>
            <Campo label="Aves muertas en un día que disparan alerta de salud" ayuda="Se compara con cada registro del día.">
              <input type="number" min="1" max="500" value={umbral} onChange={(e) => setUmbral(valorCampo(e))} required />
            </Campo>
            <button className="btn" type="submit" disabled={guardando} style={{ marginTop: 16 }}>
              {guardando ? "Guardando…" : "Guardar umbral"}
            </button>
          </form>
        </Panel>
      )}
    </>
  );
}
