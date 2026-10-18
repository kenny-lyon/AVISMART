import { useState } from "react";

/** Campo de clave con botón para mostrarla y aviso de Bloq Mayús activado. */
export default function CampoClave({ id, label, value, onChange, autoComplete, minLength, autoFocus }: {
  id: string;
  label: string;
  value: string;
  onChange: (valor: string) => void;
  autoComplete: "current-password" | "new-password";
  minLength?: number;
  autoFocus?: boolean;
}) {
  const [visible, setVisible] = useState(false);
  const [mayusculas, setMayusculas] = useState(false);

  function revisarMayusculas(e: React.KeyboardEvent<HTMLInputElement>) {
    setMayusculas(e.getModifierState?.("CapsLock") ?? false);
  }

  return (
    <>
      <label htmlFor={id}>{label}</label>
      <div className="campo-clave">
        <input
          id={id}
          type={visible ? "text" : "password"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={revisarMayusculas}
          onKeyUp={revisarMayusculas}
          onBlur={() => setMayusculas(false)}
          autoComplete={autoComplete}
          minLength={minLength}
          autoFocus={autoFocus}
          autoCapitalize="none"
          autoCorrect="off"
          spellCheck={false}
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
    </>
  );
}
