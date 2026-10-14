import { createContext, useContext, useEffect, useState } from "react";
import { api, type Resumen } from "./api";

type LoteState = {
  resumen: Resumen | null;
  loteId: number | null;
  elegir: (id: number) => void;
  recargar: () => Promise<void>;
};

const LoteContext = createContext<LoteState | null>(null);

export function LoteProvider({ children }: { children: React.ReactNode }) {
  const [resumen, setResumen] = useState<Resumen | null>(null);
  const [loteId, setLoteId] = useState<number | null>(() => {
    const saved = sessionStorage.getItem("avismart_lote");
    return saved ? Number(saved) : null;
  });

  async function recargar() {
    const data = await api<Resumen>("/resumen");
    setResumen(data);
    const sigue = data.lotes.some((lote) => lote.id === loteId);
    const siguiente = sigue ? loteId : (data.lotes.find((lote) => lote.estado === "ACTIVO") ?? data.lotes[0])?.id ?? null;
    if (siguiente) {
      setLoteId(siguiente);
      sessionStorage.setItem("avismart_lote", String(siguiente));
    }
  }

  useEffect(() => {
    recargar().catch(() => setResumen(null));
    // La carga inicial no depende del lote elegido.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function elegir(id: number) {
    setLoteId(id);
    sessionStorage.setItem("avismart_lote", String(id));
  }

  return (
    <LoteContext.Provider value={{ resumen, loteId, elegir, recargar }}>
      {children}
    </LoteContext.Provider>
  );
}

export function useLote() {
  const ctx = useContext(LoteContext);
  if (!ctx) throw new Error("Lote fuera de contexto");
  return ctx;
}
