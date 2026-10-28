import { useState } from "react";
import { Ayuda } from "./ui";

/** Tope: el largo de las claves que sugiere Google Chrome (las temporales de AviSmart tienen 14). */
export const CLAVE_MIN = 8;
export const CLAVE_MAX = 15;

/** Reglas de una clave nueva (las mismas que valida el servidor), con el mensaje de cada falla.
 *  Las que no tienen `texto` se validan pero no se muestran en el tooltip. */
const REGLAS: { texto: string; falla: (c: string) => boolean; error: string }[] = [
  { texto: `Entre ${CLAVE_MIN} y ${CLAVE_MAX} caracteres`, falla: (c) => c.length < CLAVE_MIN, error: `Te faltan caracteres: usa al menos ${CLAVE_MIN}.` },
  {
    texto: "Letras, números y símbolos (por ejemplo # . - @)",
    falla: (c) => !/\p{L}/u.test(c) || !/\d/.test(c) || !/[^\p{L}\d\s]/u.test(c),
    error: "Combina letras, números y al menos un símbolo (por ejemplo # . - @).",
  },
  { texto: "Al menos 5 caracteres distintos", falla: (c) => new Set(c.toLowerCase()).size < 5, error: "Usa al menos 5 caracteres distintos." },
  { texto: "", falla: (c) => /(.)\1{3}/u.test(c), error: "No repitas el mismo carácter más de 3 veces seguidas." },
  { texto: "", falla: (c) => c !== c.trim(), error: "Quita los espacios del inicio o del final." },
];

/** Primer problema de la clave nueva, o null si cumple todo. */
export function problemaClave(clave: string): string | null {
  return REGLAS.find((r) => r.falla(clave))?.error ?? null;
}

/** Campo de clave con botón para mostrarla y aviso de Bloq Mayús activado.
 *  Con `reglas`, muestra los requisitos en un tooltip y, si la clave no los cumple, el error en rojo debajo. */
export default function CampoClave({ id, label, value, onChange, autoComplete, minLength, autoFocus, reglas = false }: {
  id: string;
  label: string;
  value: string;
  onChange: (valor: string) => void;
  autoComplete: "current-password" | "new-password";
  minLength?: number;
  autoFocus?: boolean;
  reglas?: boolean;
}) {
  const [visible, setVisible] = useState(false);
  const [mayusculas, setMayusculas] = useState(false);
  const [tocado, setTocado] = useState(false);
  const error = reglas && tocado && value ? problemaClave(value) : null;

  function revisarMayusculas(e: React.KeyboardEvent<HTMLInputElement>) {
    setMayusculas(e.getModifierState?.("CapsLock") ?? false);
  }

  return (
    <>
      <label htmlFor={id} className={reglas ? "label-con-ayuda" : undefined}>
        {label}
        {reglas && (
          <Ayuda titulo="Requisitos de la clave" arriba>
            <ul className="requisitos-clave">{REGLAS.filter((r) => r.texto).map((r) => <li key={r.texto}>{r.texto}</li>)}</ul>
          </Ayuda>
        )}
      </label>
      <div className="campo-clave">
        <input
          id={id}
          type={visible ? "text" : "password"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={revisarMayusculas}
          onKeyUp={revisarMayusculas}
          onBlur={() => { setMayusculas(false); setTocado(true); }}
          autoComplete={autoComplete}
          minLength={minLength}
          maxLength={autoComplete === "new-password" ? CLAVE_MAX : 128}
          autoFocus={autoFocus}
          autoCapitalize="none"
          autoCorrect="off"
          spellCheck={false}
          aria-invalid={!!error}
          aria-describedby={error ? `${id}-error` : undefined}
          required
        />
        <button
          type="button"
          className="ver-clave"
          onClick={() => setVisible((v) => !v)}
          aria-label={visible ? "Ocultar clave" : "Mostrar clave"}
          aria-pressed={visible}
          title={visible ? "Ocultar clave" : "Mostrar clave"}
        >
          <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
            {visible ? (
              <path d="M3 3l18 18M10.6 10.6a2 2 0 0 0 2.8 2.8M9.9 5.1A10.4 10.4 0 0 1 12 5c6.5 0 10 7 10 7a17.6 17.6 0 0 1-3.2 4.2M6.6 6.6C3.9 8.4 2 12 2 12s3.5 7 10 7a9.7 9.7 0 0 0 5.4-1.6" />
            ) : (
              <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12zM12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z" />
            )}
          </svg>
        </button>
      </div>
      {mayusculas && <p className="aviso-mayus" role="status">Bloq Mayús está activado</p>}
      {error && <p className="error-clave" id={`${id}-error`} role="alert">{error}</p>}
    </>
  );
}
