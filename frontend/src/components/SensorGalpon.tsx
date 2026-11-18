import { useState } from "react";
import { api, fecha, haceCuanto, type Galpon, type SensorEstado } from "../api";
import { Drawer, mensajeError, useToast } from "./ui";

/** Chip con el estado del sensor del galpón. */
export function EstadoSensor({ sensor }: { sensor: SensorEstado }) {
  if (!sensor.activo) return <span className="sensor-chip apagado">Sin sensor</span>;
  if (sensor.en_linea) return <span className="sensor-chip en-linea">En línea{sensor.ultimo_envio ? ` · ${haceCuanto(sensor.ultimo_envio)}` : ""}</span>;
  return <span className="sensor-chip sin-senal">Sin señal{sensor.ultimo_envio ? ` · ${haceCuanto(sensor.ultimo_envio)}` : ""}</span>;
}

/** Panel para activar el sensor del galpón y entregar la clave que se configura en el equipo. */
export function SensorGalpon({ galpon, onCerrar, onCambio }: { galpon: Galpon | null; onCerrar: () => void; onCambio: () => Promise<void> }) {
  const avisar = useToast();
  const [clave, setClave] = useState<string | null>(null);
  const [trabajando, setTrabajando] = useState(false);
  const [error, setError] = useState("");
  if (!galpon) return null;
  const ruta = `${window.location.origin}/api/iot/lecturas`;

  function cerrar() {
    setClave(null);
    setError("");
    onCerrar();
  }

  async function activar() {
    if (galpon!.sensor.activo && !window.confirm("Se generará una clave nueva y el equipo con la clave anterior dejará de enviar datos. ¿Continuar?")) return;
    setError("");
    setTrabajando(true);
    try {
      const r = await api<{ clave: string }>(`/galpones/${galpon!.id}/sensor`, { method: "POST" });
      setClave(r.clave);
      await onCambio();
    } catch (err) {
      setError(mensajeError(err, "No se pudo activar el sensor"));
    } finally {
      setTrabajando(false);
    }
  }

  async function desactivar() {
    if (!window.confirm(`¿Desactivar el sensor de ${galpon!.nombre}? El equipo dejará de enviar lecturas.`)) return;
    setTrabajando(true);
    try {
      await api(`/galpones/${galpon!.id}/sensor`, { method: "DELETE" });
      setClave(null);
      await onCambio();
      avisar("Sensor desactivado.");
    } catch (err) {
      setError(mensajeError(err, "No se pudo desactivar el sensor"));
    } finally {
      setTrabajando(false);
    }
  }

  async function copiar() {
    try {
      await navigator.clipboard.writeText(`Dirección: ${ruta}\nClave: ${clave}`);
      avisar("Datos del sensor copiados.");
    } catch {
      avisar("No se pudo copiar; selecciona el texto manualmente.", "riesgo");
    }
  }

  return (
    <Drawer
      abierto
      titulo={`Sensor de ${galpon.nombre}`}
      descripcion={`${galpon.granja} · temperatura y humedad automáticas`}
      onCerrar={cerrar}
      pie={
        <>
          {galpon.sensor.activo && <button className="btn riesgo-suave" type="button" onClick={desactivar} disabled={trabajando}>Desactivar</button>}
          <button className="btn primario" type="button" onClick={activar} disabled={trabajando}>
            {galpon.sensor.activo ? "Generar nueva clave" : "Activar sensor"}
          </button>
        </>
      }
    >
      <div className="sensor-estado">
        <EstadoSensor sensor={galpon.sensor} />
        {galpon.sensor.ultimo_envio && <span className="muted">Última lectura: {fecha(galpon.sensor.ultimo_envio)} {galpon.sensor.ultimo_envio.slice(11, 16)}</span>}
      </div>
      <p className="muted sensor-texto">
        El sensor del galpón envía la temperatura y la humedad cada minuto. Las lecturas quedan guardadas solas y, si salen del rango de la
        edad del lote, se genera la alerta de ambiente igual que con una lectura manual.
      </p>
      {error && <div className="aviso riesgo">{error}</div>}
      {clave && (
        <div className="temporary-credential">
          <div>
            <strong>Datos para configurar el equipo · se muestran solo esta vez</strong>
            <p>Dirección: <code>{ruta}</code></p>
            <p>Clave: <code>{clave}</code></p>
            <small>Guárdalos en el equipo del galpón. Si se pierden, genera una clave nueva.</small>
          </div>
          <button className="btn secondary" type="button" onClick={copiar}>Copiar</button>
        </div>
      )}
    </Drawer>
  );
}
