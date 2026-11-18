import { useEffect, useState } from "react";
import { api, fecha, haceCuanto, leerToken, type Camara } from "../api";
import { PageHeader } from "../components/ui";
import { EstadoSensor } from "../components/SensorGalpon";
import { useLote } from "../lote";

const MINUTOS_FOTO = 30;

export default function CamaraPage() {
  const { loteId } = useLote();
  const [camara, setCamara] = useState<Camara | null>(null);
  const [ahora, setAhora] = useState(() => new Date());
  const [error, setError] = useState("");
  const [foto, setFoto] = useState<string | null>(null);

  useEffect(() => {
    if (!loteId) return;
    api<Camara>(`/lotes/${loteId}/camara`)
      .then(setCamara)
      .catch((err) => setError(err.message));
  }, [loteId]);

  // La foto se muestra solo si es reciente; si la cámara dejó de enviar, vuelve a OFFLINE.
  const hayFoto = !!camara?.foto && Date.now() - new Date(camara.foto.fecha_hora).getTime() < MINUTOS_FOTO * 60000;
  useEffect(() => {
    if (!hayFoto || !loteId) return;
    let local: string | null = null;
    fetch(`/api/lotes/${loteId}/camara/foto`, { headers: { Authorization: `Bearer ${leerToken() ?? ""}` } })
      .then((r) => (r.ok ? r.blob() : Promise.reject()))
      .then((b) => { local = URL.createObjectURL(b); setFoto(local); })
      .catch(() => setFoto(null));
    return () => { if (local) URL.revokeObjectURL(local); setFoto(null); };
  }, [hayFoto, loteId, camara?.foto?.fecha_hora]);

  useEffect(() => {
    const id = window.setInterval(() => setAhora(new Date()), 1000);
    return () => window.clearInterval(id);
  }, []);

  const reloj = ahora.toLocaleTimeString("es-PE", { hour12: false });

  return (
    <>
      <PageHeader
        titulo="Cámara del galpón"
        descripcion={camara ? `${camara.nombre} · ${camara.galpon}${camara.lote ? ` · ${camara.lote}` : ""}` : "Cargando la vista del galpón…"}
      />
      {error && <div className="aviso riesgo">{error}</div>}
      {camara && (
        <section className="panel"><div className="panel-body">
          <div className="cam-feed">
            <div className="cam-hud">
              <span className="cam-live">{foto ? "FOTO" : "OFFLINE"}</span>
              <span>{camara.nombre}</span>
              <span>{reloj}</span>
            </div>
            {foto ? (
              <img className="cam-foto" src={foto} alt={`Última foto de ${camara.galpon}`} />
            ) : (
              <div className="cam-offline">
                <strong>NO SIGNAL</strong>
                <span>Sin conexión con la cámara</span>
              </div>
            )}
          </div>
          <div className="cam-meta">
            <div>
              <span className="muted">Ubicación</span>
              <strong>{camara.ubicacion ?? "—"} · {camara.galpon}</strong>
            </div>
            <div>
              <span className="muted">Estado</span>
              <strong>{foto && camara.foto ? `Última foto ${haceCuanto(camara.foto.fecha_hora)}` : "Offline · sin señal"}</strong>
            </div>
            <div>
              <span className="muted">Sensor de temperatura y humedad</span>
              <strong><EstadoSensor sensor={camara.sensor} /></strong>
            </div>
            <div>
              <span className="muted">Última lectura ambiental</span>
              <strong>
                {camara.lectura
                  ? `${camara.lectura.temperatura.toFixed(1)} °C · ${camara.lectura.humedad.toFixed(0)}% · ${fecha(camara.lectura.fecha_hora)}`
                  : "Sin lecturas todavía"}
              </strong>
            </div>
          </div>
          {!foto && (
            <p className="muted" style={{ margin: "16px 0 0", fontSize: 14 }}>
              La cámara del galpón no tiene conexión en este momento. Cuando esté disponible, el video aparecerá aquí.
            </p>
          )}
        </div></section>
      )}
    </>
  );
}
