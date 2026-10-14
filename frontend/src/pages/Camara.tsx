import { useEffect, useState } from "react";
import { api, fecha, type Camara } from "../api";
import { PageHeader } from "../components/ui";
import { useLote } from "../lote";

export default function CamaraPage() {
  const { loteId } = useLote();
  const [camara, setCamara] = useState<Camara | null>(null);
  const [ahora, setAhora] = useState(() => new Date());
  const [error, setError] = useState("");

  useEffect(() => {
    if (!loteId) return;
    api<Camara>(`/lotes/${loteId}/camara`)
      .then(setCamara)
      .catch((err) => setError(err.message));
  }, [loteId]);

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
              <span className="cam-live">OFFLINE</span>
              <span>{camara.nombre}</span>
              <span>{reloj}</span>
            </div>
            <div className="cam-offline">
              <strong>NO SIGNAL</strong>
              <span>Sin conexión con la cámara</span>
            </div>
          </div>
          <div className="cam-meta">
            <div>
              <span className="muted">Ubicación</span>
              <strong>{camara.ubicacion ?? "—"} · {camara.galpon}</strong>
            </div>
            <div>
              <span className="muted">Estado</span>
              <strong>Offline · sin señal</strong>
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
          <p className="muted" style={{ margin: "16px 0 0", fontSize: 14 }}>
            La cámara del galpón no tiene conexión en este momento. Cuando esté disponible, el video aparecerá aquí.
          </p>
        </div></section>
      )}
    </>
  );
}
