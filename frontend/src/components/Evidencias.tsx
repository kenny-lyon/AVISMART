import { useEffect, useRef, useState } from "react";
import { api, fecha, leerToken, num, type Lote } from "../api";
import { Ayuda, Drawer, Icon, mensajeError, useToast } from "./ui";

export type Seccion = "GALPON" | "GUIA" | "ORIGEN" | "VACUNAS" | "RECEPCION" | "BAJAS" | "CONSUMO" | "PESAJE" | "REVISION";
// Pertenecen a un registro del día (o a la revisión de sus bajas): se adjuntan allí y aquí solo se ven.
const DEL_REGISTRO: Seccion[] = ["BAJAS", "CONSUMO", "PESAJE", "REVISION"];
export type Adjunto = {
  id: number;
  seccion: Seccion;
  seccion_nombre: string;
  registro_fecha: string | null;
  nombre: string;
  tipo: string;
  tamano: number;
  subido_por: string | null;
  subido_en: string;
};

export const MAX_POR_SECCION = 5;
const MAX_BYTES = 5 * 1024 * 1024;
const ACEPTA = "image/jpeg,image/png,image/webp,application/pdf";
const TITULOS: Record<Seccion, string> = {
  GALPON: "Galpón preparado",
  GUIA: "Guía de remisión",
  ORIGEN: "Factura u otros documentos",
  VACUNAS: "Certificado de vacunación",
  RECEPCION: "Fotos de la recepción",
  BAJAS: "Fotos de las bajas",
  CONSUMO: "Alimento y agua",
  PESAJE: "Pesaje de la muestra",
  REVISION: "Evidencias del veterinario",
};

function peso(bytes: number) {
  return bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

/** Las fotos grandes se reducen en el navegador (máx. 1920 px, JPEG) antes de subirlas. */
async function comprimir(archivo: File): Promise<File> {
  if (!archivo.type.startsWith("image/") || archivo.size < 900 * 1024) return archivo;
  try {
    const imagen = await createImageBitmap(archivo);
    const escala = Math.min(1, 1920 / Math.max(imagen.width, imagen.height));
    const lienzo = document.createElement("canvas");
    lienzo.width = Math.round(imagen.width * escala);
    lienzo.height = Math.round(imagen.height * escala);
    lienzo.getContext("2d")?.drawImage(imagen, 0, 0, lienzo.width, lienzo.height);
    const blob = await new Promise<Blob | null>((ok) => lienzo.toBlob(ok, "image/jpeg", 0.82));
    if (!blob || blob.size >= archivo.size) return archivo;
    return new File([blob], archivo.name.replace(/\.\w+$/, "") + ".jpg", { type: "image/jpeg" });
  } catch {
    return archivo;
  }
}

/** Sube un archivo a la ruta indicada (temporal o de un lote). */
export async function subirEvidencia(ruta: string, seccion: Seccion, original: File): Promise<Adjunto> {
  const archivo = await comprimir(original);
  if (archivo.size > MAX_BYTES) throw new Error(`«${original.name}» pesa más de 5 MB.`);
  const datos = new FormData();
  datos.append("seccion", seccion);
  datos.append("archivo", archivo, archivo.name);
  return api<Adjunto>(ruta, { method: "POST", body: datos });
}

/** Descarga un adjunto con la sesión (los archivos no son públicos) y devuelve una URL local. */
async function urlLocal(id: number): Promise<string> {
  const res = await fetch(`/api/adjuntos/${id}/archivo`, { headers: { Authorization: `Bearer ${leerToken() ?? ""}` } });
  if (!res.ok) throw new Error("No se pudo abrir el archivo");
  return URL.createObjectURL(await res.blob());
}

function Miniatura({ adjunto }: { adjunto: Adjunto }) {
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    if (!adjunto.tipo.startsWith("image/")) return;
    let local: string | null = null;
    urlLocal(adjunto.id).then((u) => { local = u; setUrl(u); }).catch(() => undefined);
    return () => { if (local) URL.revokeObjectURL(local); };
  }, [adjunto.id, adjunto.tipo]);
  if (adjunto.tipo === "application/pdf") return <span className="evid-mini pdf">PDF</span>;
  return url ? <img className="evid-mini" src={url} alt="" /> : <span className="evid-mini" />;
}

async function abrir(adjunto: Adjunto) {
  const url = await urlLocal(adjunto.id);
  window.open(url, "_blank", "noopener");
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

/** Zona para adjuntar evidencias de una sección (se usa dentro de «Abrir lote»). */
export function ZonaEvidencia({ seccion, ayuda, obligatoria = false, archivos, ruta, onCambio }: {
  seccion: Seccion;
  ayuda: string;
  obligatoria?: boolean;
  archivos: Adjunto[];
  ruta: string;
  onCambio: (archivos: Adjunto[]) => void;
}) {
  const entrada = useRef<HTMLInputElement>(null);
  const [subiendo, setSubiendo] = useState(0);
  const [error, setError] = useState("");
  const [encima, setEncima] = useState(false);
  const lleno = archivos.length >= MAX_POR_SECCION;

  async function agregar(lista: FileList | null) {
    if (!lista?.length) return;
    setError("");
    const elegidos = Array.from(lista).slice(0, MAX_POR_SECCION - archivos.length);
    if (lista.length > elegidos.length) setError(`Como máximo ${MAX_POR_SECCION} archivos en esta sección.`);
    let actuales = archivos;
    setSubiendo(elegidos.length);
    for (const archivo of elegidos) {
      try {
        const nuevo = await subirEvidencia(ruta, seccion, archivo);
        actuales = [...actuales, nuevo];
        onCambio(actuales);
      } catch (err) {
        setError(mensajeError(err, `No se pudo subir «${archivo.name}»`));
      } finally {
        setSubiendo((n) => n - 1);
      }
    }
    if (entrada.current) entrada.current.value = "";
  }

  async function quitar(adjunto: Adjunto) {
    try {
      await api(`/adjuntos/${adjunto.id}`, { method: "DELETE" });
      onCambio(archivos.filter((a) => a.id !== adjunto.id));
    } catch (err) {
      setError(mensajeError(err, "No se pudo quitar el archivo"));
    }
  }

  return (
    <div className="campo ancho evid-campo">
      <span className="campo-label con-info">
        <span>{TITULOS[seccion]}</span>
        {(ayuda || obligatoria) && <Ayuda titulo={obligatoria ? `${TITULOS[seccion]} · obligatoria` : TITULOS[seccion]} nota>{ayuda || "Debe quedar al menos una."}</Ayuda>}
      </span>
      {archivos.length > 0 && (
        <div className="evid-lista">
          {archivos.map((a) => (
            <div key={a.id} className="evid-item">
              <Miniatura adjunto={a} />
              <div className="evid-datos">
                <button type="button" className="link-button evid-nombre" onClick={() => abrir(a).catch(() => undefined)} title="Ver archivo">{a.nombre}</button>
                <small>{peso(a.tamano)}</small>
              </div>
              <button type="button" className="evid-quitar" aria-label={`Quitar ${a.nombre}`} title="Quitar" onClick={() => quitar(a)}>×</button>
            </div>
          ))}
        </div>
      )}
      {!lleno && (
        <button
          type="button"
          className={`evid-zona${encima ? " encima" : ""}${obligatoria && archivos.length === 0 ? " falta" : ""}${archivos.length ? " compacta" : ""}`}
          onClick={() => entrada.current?.click()}
          disabled={subiendo > 0}
          onDragOver={(e) => { e.preventDefault(); setEncima(true); }}
          onDragLeave={() => setEncima(false)}
          onDrop={(e) => { e.preventDefault(); setEncima(false); agregar(e.dataTransfer.files); }}
        >
          <span className="evid-icono"><Icon name="subir" size={18} /></span>
          <span className="evid-texto">
            <b>{subiendo > 0 ? "Subiendo…" : archivos.length ? "Agregar otro archivo" : "Toca para subir o arrastra aquí"}</b>
            <small>Foto o PDF · hasta 5 MB</small>
          </span>
        </button>
      )}
      <input ref={entrada} type="file" accept={ACEPTA} multiple hidden onChange={(e) => agregar(e.target.files)} />
      {error && <p className="error-clave">{error}</p>}
    </div>
  );
}

// Mismo orden y nombres que las secciones de «Abrir lote».
const GRUPOS: { titulo: string; secciones: Seccion[] }[] = [
  { titulo: "1. Galpón y línea", secciones: ["GALPON"] },
  { titulo: "2. Origen de los pollitos", secciones: ["GUIA", "ORIGEN"] },
  { titulo: "3. Vacunas de la incubadora", secciones: ["VACUNAS"] },
  { titulo: "4. Recepción", secciones: ["RECEPCION"] },
  { titulo: "5. Registros del día", secciones: DEL_REGISTRO },
];

/** Archivos de una sección, solo para ver (lote cerrado o cuenta sin permiso para editar). */
export function ListaEvidencia({ seccion, archivos }: { seccion: Seccion; archivos: Adjunto[] }) {
  return (
    <div className="campo ancho evid-campo">
      <span className="campo-label">{TITULOS[seccion]}</span>
      {archivos.length === 0 ? (
        <p className="muted evid-vacio">Sin archivos.</p>
      ) : (
        <div className="evid-lista">
          {archivos.map((a) => (
            <div key={a.id} className="evid-item" title={`Subido${a.subido_por ? ` por ${a.subido_por}` : ""} el ${fecha(a.subido_en)}`}>
              <Miniatura adjunto={a} />
              <div className="evid-datos">
                <button type="button" className="link-button evid-nombre" onClick={() => abrir(a).catch(() => undefined)} title="Ver archivo">{a.nombre}</button>
                <small>{a.registro_fecha ? `Día ${fecha(a.registro_fecha)} · ` : ""}{peso(a.tamano)}</small>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/** Panel con las evidencias de un lote: verlas, descargarlas y, si sigue activo, agregar o quitar. */
export function EvidenciasLote({ lote, puedeEditar, onCerrar }: {
  lote: Lote | null;
  puedeEditar: boolean;
  onCerrar: () => void;
}) {
  const avisar = useToast();
  const [datos, setDatos] = useState<{ editable: boolean; adjuntos: Adjunto[] } | null>(null);

  useEffect(() => {
    setDatos(null);
    if (!lote) return;
    api<{ editable: boolean; adjuntos: Adjunto[] }>(`/lotes/${lote.id}/adjuntos`).then(setDatos).catch((err) => avisar(mensajeError(err), "riesgo"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lote?.id]);

  if (!lote) return null;
  const editable = puedeEditar && !!datos?.editable;
  const activo = lote.estado === "ACTIVO";
  const alojados = lote.poblacion_inicial;

  return (
    <Drawer
      abierto
      titulo="Evidencias del lote"
      descripcion={`${lote.granja} · ${lote.galpon} · ${lote.linea}`}
      onCerrar={onCerrar}
      ancho="amplio"
      pie={<button className="btn secondary" type="button" onClick={onCerrar}>Cerrar</button>}
    >
      <div className="evid-resumen">
        <div><span>Estado</span><b>{activo ? `Activo · día ${lote.dia_vida}` : `Cerrado${lote.fecha_cierre ? ` el ${fecha(lote.fecha_cierre)}` : ""}`}</b></div>
        <div><span>Ingreso</span><b>{fecha(lote.fecha_ingreso)}</b></div>
        <div><span>Incubadora</span><b>{lote.proveedor || "—"}</b></div>
        <div><span>Guía de remisión</span><b>{lote.guia || "—"}</b></div>
        <div><span>Pollitos alojados</span><b>{num(alojados)}{lote.cantidad_recibida ? ` de ${num(lote.cantidad_recibida)}` : ""}</b></div>
        <div><span>Archivos</span><b>{datos ? datos.adjuntos.length : "…"}</b></div>
      </div>
      {!activo && <p className="muted evid-nota">El lote está cerrado: sus evidencias quedaron fijas y solo se pueden ver o descargar.</p>}
      {!datos ? (
        <p className="muted">Cargando…</p>
      ) : (
        GRUPOS.map((g) => (
          <fieldset key={g.titulo} className="form-seccion con-marco">
            <legend>{g.titulo}</legend>
            <div className="form-grid">
              {g.secciones.map((s) => {
                const archivos = datos.adjuntos.filter((a) => a.seccion === s);
                return editable && !DEL_REGISTRO.includes(s) ? (
                  <ZonaEvidencia
                    key={s}
                    seccion={s}
                    obligatoria={s === "GUIA"}
                    ayuda={s === "GUIA" ? "Debe quedar al menos una." : ""}
                    archivos={archivos}
                    ruta={`/lotes/${lote.id}/adjuntos`}
                    onCambio={(lista) => setDatos({ ...datos, adjuntos: [...datos.adjuntos.filter((a) => a.seccion !== s), ...lista] })}
                  />
                ) : (
                  <ListaEvidencia key={s} seccion={s} archivos={archivos} />
                );
              })}
            </div>
          </fieldset>
        ))
      )}
    </Drawer>
  );
}
