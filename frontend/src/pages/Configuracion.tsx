import { useEffect, useState } from "react";
import { api, type Rol } from "../api";
import { useAuth } from "../auth";
import Cuentas from "../components/Cuentas";
import { Campo, PageHeader, Panel, Tabs, mensajeError, useToast } from "../components/ui";
import { useLote } from "../lote";

/** Qué cuentas crea y gestiona cada rol del cliente (lo mismo que valida el backend). */
const PERSONAL: Partial<Record<Rol, { crea: Rol[]; gestiona: Rol[] }>> = {
  ADMIN: { crea: ["PRODUCTOR", "OPERATIVO", "VETERINARIO"], gestiona: ["ADMIN", "PRODUCTOR", "OPERATIVO", "VETERINARIO"] },
  PRODUCTOR: { crea: ["OPERATIVO", "VETERINARIO"], gestiona: ["OPERATIVO", "VETERINARIO"] },
};

export default function Configuracion() {
  const { usuario } = useAuth();
  const { resumen, recargar } = useLote();
  const avisar = useToast();
  const rol = usuario?.rol ?? "OPERATIVO";
  const personal = PERSONAL[rol];
  const veUmbral = rol === "VETERINARIO" || rol === "ADMIN";
  const pestanas = [
    ...(personal ? [{ id: "cuentas", label: "Personal" }] : []),
    ...(veUmbral ? [{ id: "parametros", label: "Parámetros de alerta" }] : []),
  ];
  const [pestana, setPestana] = useState(pestanas[0]?.id ?? "parametros");
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
        titulo={personal ? "Personal y ajustes" : "Parámetros de alerta"}
        descripcion={
          personal
            ? `Cuentas del personal de ${resumen?.organizacion.nombre ?? "la organización"}.`
            : "El valor clínico que dispara las alertas de salud del lote."
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
              ? "Agrega a tus operativos y médicos veterinarios. Cada alta genera una clave temporal."
              : "Cada alta genera una clave temporal que la persona cambia al entrar."
          }
        />
      )}

      {pestana === "parametros" && veUmbral && (
        <Panel titulo="Umbral de mortalidad diaria" descripcion="Lo define el médico veterinario según el estado sanitario del lote.">
          <form onSubmit={guardar} style={{ maxWidth: 420 }}>
            <Campo label="Aves muertas en un día que disparan alerta de salud" ayuda="Se compara con cada registro del día.">
              <input type="number" min="1" max="500" value={umbral} onChange={(e) => setUmbral(e.target.value)} required />
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
