/** Limpieza de nombres mientras se escriben (las mismas reglas que valida el servidor en app/textos.py). */

export const LARGO_NOMBRE = 40;
export const LARGO_GUIA = 20;

type Tipo = "lugar" | "persona" | "guia";

const PERMITIDOS: Record<Tipo, RegExp> = {
  lugar: /[^\p{L}\p{N} .,'&()/°º#-]/gu, // letras, números, espacios y signos comunes de empresas
  persona: /[^\p{L} '.-]/gu, // solo letras, espacios, apóstrofo, punto y guion
  guia: /[^A-Z0-9/ -]/g,
};
const REPETICION_MAX: Record<Tipo, number> = { lugar: 3, persona: 2, guia: 6 };
const LARGO: Record<Tipo, number> = { lugar: LARGO_NOMBRE, persona: LARGO_NOMBRE, guia: LARGO_GUIA };

/** Quita lo que no se puede escribir: caracteres no permitidos, espacios al inicio o dobles,
 *  el mismo carácter repetido de más y lo que pase del largo máximo. */
export function limpiarTexto(valor: string, tipo: Tipo): string {
  let texto = tipo === "guia" ? valor.toUpperCase() : valor;
  // Debe empezar con letra o número (ni espacios ni símbolos al inicio).
  texto = texto.replace(PERMITIDOS[tipo], "").replace(/^[^\p{L}\p{N}]+/u, "").replace(/\s{2,}/g, " ");
  const maximo = REPETICION_MAX[tipo];
  let salida = "";
  let racha = 0;
  for (const c of texto) {
    const anterior = salida.slice(-1);
    racha = anterior && anterior.toLowerCase() === c.toLowerCase() ? racha + 1 : 1;
    if (racha <= maximo) salida += c;
  }
  return Array.from(salida).slice(0, LARGO[tipo]).join("");
}

/** Para inputs no controlados (formulario de contacto): limpia el valor en cada tecla. */
export function alEscribir(tipo: Tipo) {
  return (e: React.FormEvent<HTMLInputElement>) => {
    const campo = e.currentTarget;
    let limpio = limpiarTexto(campo.value, tipo);
    const anterior = campo.dataset.anterior ?? "";
    if (tipo !== "guia" && pareceSinSentido(limpio, true) && !pareceSinSentido(anterior, true)) {
      limpio = anterior;
      avisarBloqueo(campo);
    }
    if (limpio !== campo.value) campo.value = limpio;
    campo.dataset.anterior = limpio;
    if (tipo !== "guia") marcarSinSentido(campo, limpio);
  };
}

/** Números: quita los ceros a la izquierda ("039493" → "39493", "007.5" → "7.5"); deja "0" y "0.5". */
export function sinCerosIzquierda(valor: string): string {
  return valor.replace(/^0+(?=\d)/, "");
}

/** Decimales que admite un campo según su `step` ("0.01" → 2; sin step o "1" → 0). */
function decimalesDe(step: string): number {
  const parte = step && step !== "any" ? step.split(".")[1] : "";
  return parte ? parte.length : 0;
}

/** Valor de un input. En los campos numéricos se respeta en vivo lo que dice el propio campo:
 *  solo dígitos (y el punto si su `step` admite decimales), sin ceros a la izquierda, sin pasar
 *  de su `max` (se queda en el máximo) y sin más decimales de los permitidos. El resto queda igual. */
export function valorCampo(e: { target: { value: string; type?: string; max?: string; min?: string; step?: string } }): string {
  const t = e.target;
  if (t.type !== "number") return t.value;
  const decimales = decimalesDe(t.step ?? "");
  const negativo = t.min !== undefined && t.min !== "" && Number(t.min) < 0 && t.value.trim().startsWith("-");
  let limpio = t.value.replace(decimales ? /[^\d.]/g : /\D/g, "");
  if (decimales) {
    const [entero, ...resto] = limpio.split(".");
    limpio = resto.length ? `${entero}.${resto.join("").slice(0, decimales)}` : entero;
  }
  limpio = sinCerosIzquierda(limpio);
  if (t.max !== undefined && t.max !== "" && limpio !== "" && Number(limpio) > Number(t.max)) limpio = String(Number(t.max));
  if (negativo) limpio = "-" + limpio;
  // React no redibuja un campo numérico si el texto cambia pero el número no: se corrige directo en el campo.
  if (limpio !== t.value) t.value = limpio;
  return limpio;
}

const VOCALES = /[aeiouáéíóúüy]/;
const TECLADO = ["qwertyuiop", "asdfghjklñ", "zxcvbnm", "1234567890"];

/** Texto tecleado al azar («qwdqwdqwd», «asdasdasd», «xkcdfgh»): mismas reglas que el servidor. */
export function pareceSinSentido(valor: string, escribiendo = false): boolean {
  const texto = valor.toLowerCase();
  if (!escribiendo && !VOCALES.test(texto)) return true; // un nombre terminado sin ninguna vocal no es real
  if (/([\p{L}\p{N}]{2,6}?)\1{2,}/u.test(texto)) return true; // el mismo trozo 3 veces seguidas: qwdqwdqwd, 123123123
  if ((texto.match(/\p{N}/gu) ?? []).length > 6) return true; // un nombre no es un número largo
  if (/[^\p{L}\p{N}\s]{3,}/u.test(texto) || (texto.match(/[^\p{L}\p{N}\s]/gu) ?? []).length > 6) return true; // símbolos de más
  for (const palabra of texto.match(/\p{L}+/gu) ?? []) {
    if (palabra.length > 20) return true; // ninguna palabra real de un nombre es tan larga
    if (palabra.length >= (escribiendo ? 5 : 4) && !VOCALES.test(palabra)) return true; // sin vocales (al escribir se espera una letra más: Schm-idt)
    if (/[^aeiouáéíóúüy\s]{5,}/.test(palabra)) return true; // 5 consonantes seguidas
    if (TECLADO.some((fila) => Array.from({ length: fila.length - 3 }, (_, i) => fila.slice(i, i + 4)).some((t) => palabra.includes(t)))) return true;
  }
  return false;
}

export const NO_PARECE_REAL = "El nombre no parece real. Escríbelo como figura en sus documentos.";

/** Marca el campo como inválido si el nombre parece tecleado al azar (el navegador no deja enviar el formulario). */
export function marcarSinSentido(campo: HTMLInputElement, valor: string) {
  campo.setCustomValidity(valor && pareceSinSentido(valor) ? NO_PARECE_REAL : "");
}

/** onChange de un nombre: lo limpia y, si parece tecleado al azar, bloquea el envío con el motivo. */
export function textoDe(e: React.ChangeEvent<HTMLInputElement>, tipo: "lugar" | "persona", anterior: string): string {
  const limpio = limpiarTexto(e.target.value, tipo);
  if (pareceSinSentido(limpio, true) && !pareceSinSentido(anterior, true)) {
    // La tecla convertiría el nombre en texto al azar: no entra y se explica por qué.
    e.target.value = anterior;
    avisarBloqueo(e.target);
    return anterior;
  }
  marcarSinSentido(e.target, limpio);
  return limpio;
}

/** Aviso en rojo debajo del campo cuando se bloquea una tecla. Se queda visible unos segundos aunque se siga
 *  escribiendo (se renueva con cada bloqueo). Va fijo sobre la página para no interferir con React. */
const avisos = new WeakMap<HTMLInputElement, { nodo: HTMLDivElement; timer: number }>();

function avisarBloqueo(campo: HTMLInputElement) {
  const previo = avisos.get(campo);
  const nodo = previo?.nodo ?? document.createElement("div");
  if (previo) window.clearTimeout(previo.timer);
  nodo.className = "aviso-campo";
  nodo.setAttribute("role", "alert");
  nodo.textContent = NO_PARECE_REAL;
  const ubicar = () => {
    const caja = campo.getBoundingClientRect();
    Object.assign(nodo.style, { left: `${caja.left}px`, top: `${caja.bottom + 6}px`, width: `${caja.width}px` });
  };
  ubicar();
  if (!previo) document.body.appendChild(nodo);
  const quitar = () => {
    nodo.remove();
    avisos.delete(campo);
    campo.removeEventListener("blur", quitar);
    window.removeEventListener("scroll", ubicar, true);
  };
  if (!previo) {
    campo.addEventListener("blur", quitar);
    window.addEventListener("scroll", ubicar, true);
  }
  avisos.set(campo, { nodo, timer: window.setTimeout(quitar, 5000) });
}
