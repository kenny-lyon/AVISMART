import { useEffect, useMemo, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { MapContainer, Marker, TileLayer, useMap, useMapEvents } from "react-leaflet";
import { Campo, Icon } from "./ui";

export type Ubicacion = {
  departamento: string;
  provincia: string;
  distrito: string;
  latitud: number | null;
  longitud: number | null;
};

/** [nombre, latitud, longitud] de la capital del distrito (sin coordenadas en algunos distritos nuevos). */
type Distrito = [string, number | null, number | null];
type Ubigeo = { n: string; p: { n: string; d: Distrito[] }[] }[];

let ubigeoCache: Promise<Ubigeo> | null = null;
function cargarUbigeo() {
  ubigeoCache ??= fetch("/data/ubigeo-peru.json").then((r) => {
    if (!r.ok) throw new Error("No se pudo cargar la lista de distritos");
    return r.json();
  });
  return ubigeoCache;
}

const PERU: [number, number] = [-9.19, -75.02];
const PIN = L.divIcon({ className: "pin-granja", html: "<span></span>", iconSize: [30, 40], iconAnchor: [15, 38] });

/** Leaflet necesita recalcular su tamaño cuando el mapa aparece dentro de un panel animado. */
function AjustarTamano() {
  const map = useMap();
  useEffect(() => {
    const t = setTimeout(() => map.invalidateSize(), 320);
    return () => clearTimeout(t);
  }, [map]);
  return null;
}

function IrA({ destino }: { destino: { punto: [number, number]; zoom: number; n: number } | null }) {
  const map = useMap();
  useEffect(() => {
    if (destino) map.flyTo(destino.punto, destino.zoom, { duration: 0.8 });
  }, [destino, map]);
  return null;
}

function AlHacerClic({ onPunto }: { onPunto: (lat: number, lng: number) => void }) {
  useMapEvents({ click: (e) => onPunto(e.latlng.lat, e.latlng.lng) });
  return null;
}

export default function UbicacionGranja({ valor, onCambio }: { valor: Ubicacion; onCambio: (u: Ubicacion) => void }) {
  const [ubigeo, setUbigeo] = useState<Ubigeo | null>(null);
  const [error, setError] = useState("");
  const [buscando, setBuscando] = useState(false);
  const [destino, setDestino] = useState<{ punto: [number, number]; zoom: number; n: number } | null>(null);

  useEffect(() => {
    cargarUbigeo().then(setUbigeo).catch((e) => setError(e.message));
  }, []);

  const provincias = useMemo(() => ubigeo?.find((d) => d.n === valor.departamento)?.p ?? [], [ubigeo, valor.departamento]);
  const distritos = useMemo(() => provincias.find((p) => p.n === valor.provincia)?.d ?? [], [provincias, valor.provincia]);
  const punto: [number, number] | null = valor.latitud !== null && valor.longitud !== null ? [valor.latitud, valor.longitud] : null;

  const ir = (p: [number, number], zoom: number) => setDestino({ punto: p, zoom, n: Date.now() });
  const fijar = (lat: number, lng: number) => onCambio({ ...valor, latitud: Number(lat.toFixed(6)), longitud: Number(lng.toFixed(6)) });

  function elegirDistrito(nombre: string) {
    const d = distritos.find((x) => x[0] === nombre);
    const conCoordenadas = d && d[1] !== null && d[2] !== null;
    // El pin empieza en la capital del distrito; luego se arrastra hasta la granja.
    onCambio({ ...valor, distrito: nombre, ...(conCoordenadas && !punto ? { latitud: d[1], longitud: d[2] } : {}) });
    if (conCoordenadas) ir([d[1] as number, d[2] as number], 14);
  }

  function usarMiUbicacion() {
    setError("");
    if (!navigator.geolocation) {
      setError("Este navegador no permite obtener la ubicación.");
      return;
    }
    setBuscando(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setBuscando(false);
        fijar(pos.coords.latitude, pos.coords.longitude);
        ir([pos.coords.latitude, pos.coords.longitude], 16);
      },
      (err) => {
        setBuscando(false);
        setError(err.code === err.PERMISSION_DENIED
          ? "No diste permiso para usar tu ubicación. Puedes marcar el punto tocando el mapa."
          : "No se pudo obtener tu ubicación. Marca el punto tocando el mapa.");
      },
      { enableHighAccuracy: true, timeout: 15000 },
    );
  }

  return (
    <>
      <Campo label="Departamento">
        <select value={valor.departamento} onChange={(e) => onCambio({ ...valor, departamento: e.target.value, provincia: "", distrito: "" })} required disabled={!ubigeo}>
          <option value="">{ubigeo ? "Seleccionar" : "Cargando…"}</option>
          {ubigeo?.map((d) => <option key={d.n}>{d.n}</option>)}
        </select>
      </Campo>
      <Campo label="Provincia">
        <select value={valor.provincia} onChange={(e) => onCambio({ ...valor, provincia: e.target.value, distrito: "" })} required disabled={!valor.departamento}>
          <option value="">Seleccionar</option>
          {provincias.map((p) => <option key={p.n}>{p.n}</option>)}
        </select>
      </Campo>
      <Campo label="Distrito" ancho>
        <select value={valor.distrito} onChange={(e) => elegirDistrito(e.target.value)} required disabled={!valor.provincia}>
          <option value="">Seleccionar</option>
          {distritos.map((d) => <option key={d[0]}>{d[0]}</option>)}
        </select>
      </Campo>

      <div className="campo ancho">
        <span className="campo-label">Punto exacto en el mapa (opcional)</span>
        <div className="mapa-granja">
          <MapContainer center={punto ?? PERU} zoom={punto ? 15 : 5} scrollWheelZoom style={{ height: "100%", width: "100%" }}>
            <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
            <AjustarTamano />
            <IrA destino={destino} />
            <AlHacerClic onPunto={fijar} />
            {punto && (
              <Marker
                position={punto}
                icon={PIN}
                draggable
                eventHandlers={{ dragend: (e) => { const p = (e.target as L.Marker).getLatLng(); fijar(p.lat, p.lng); } }}
              />
            )}
          </MapContainer>
        </div>
        <div className="mapa-barra">
          <button className="btn small secondary" type="button" onClick={usarMiUbicacion} disabled={buscando}>
            <Icon name="ubicacion" size={15} /> {buscando ? "Buscando…" : "Usar mi ubicación"}
          </button>
          {punto ? (
            <>
              <span className="muted">{punto[0].toFixed(5)}, {punto[1].toFixed(5)}</span>
              <button className="link-button" type="button" onClick={() => onCambio({ ...valor, latitud: null, longitud: null })}>Quitar punto</button>
            </>
          ) : (
            <span className="muted">Toca el mapa para marcar la granja avícola.</span>
          )}
        </div>
        <small className="campo-ayuda">Arrastra el pin o toca el mapa hasta dejarlo sobre la granja avícola. Sirve para llegar a ella y para ubicar el clima de la zona.</small>
        {error && <div className="aviso alerta" style={{ marginTop: 8 }}>{error}</div>}
      </div>
    </>
  );
}
