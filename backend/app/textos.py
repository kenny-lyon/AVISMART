"""Validación de los textos libres que escribe la gente: nombres de granjas, clientes, personas, proveedores y guías.

Se usan como tipos de Pydantic (`NombreLugar`, `NombrePersona`…): normalizan los espacios y rechazan textos
absurdos (letras repetidas sin fin, solo símbolos, demasiado largos) con un mensaje claro en español.
"""
import re
from typing import Annotated

from pydantic import AfterValidator, Field

LARGO_NOMBRE = 40
LARGO_GUIA = 20

_LUGAR = re.compile(r"[\w .,'&()/°º#-]+")  # letras (con tildes y ñ), números y signos comunes en nombres de empresas
_PERSONA = re.compile(r"[^\W\d_]+(?:[ '.-][^\W\d_]+)*\.?")  # solo letras, con espacios, apóstrofo, guion o punto entre palabras
_GUIA = re.compile(r"[A-Z0-9][A-Z0-9/ -]*")


_VOCALES = set("aeiouáéíóúüy")
_TECLADO = ("qwertyuiop", "asdfghjklñ", "zxcvbnm", "1234567890")
NO_PARECE_REAL = "El nombre no parece real. Escríbelo como figura en sus documentos"


def parece_sin_sentido(valor: str) -> bool:
    """Detecta texto tecleado al azar: «qwdqwdqwd», «asdasdasd», «xkcdfgh», «asdfgh»…"""
    texto = valor.lower()
    if not _VOCALES.intersection(texto):  # un nombre sin ninguna vocal no es real
        return True
    if re.search(r"([^\W_]{2,6}?)\1{2,}", texto):  # el mismo trozo 3 veces seguidas: qwdqwdqwd, jajaja, 123123123
        return True
    if sum(c.isdigit() for c in texto) > 6:  # un nombre no es un número largo
        return True
    if re.search(r"[^\w\s]{3,}", texto) or sum(not c.isalnum() and not c.isspace() for c in texto) > 6:  # símbolos de más
        return True
    for palabra in re.findall(r"[^\W\d_]+", texto):
        if len(palabra) > 20:  # ninguna palabra real de un nombre es tan larga
            return True
        if len(palabra) >= 4 and not _VOCALES.intersection(palabra):  # sin vocales: qwdq, xkcdfg
            return True
        if re.search(r"[^aeiouáéíóúüy\s]{5,}", palabra):  # 5 consonantes seguidas no existen en español
            return True
        if any(fila[i:i + 4] in palabra for fila in _TECLADO for i in range(len(fila) - 3)):  # asdf, qwer, zxcv
            return True
    return False


def _limpiar(valor: str) -> str:
    return re.sub(r"\s+", " ", valor).strip()


def _repite(valor: str, veces: int) -> bool:
    return re.search(r"(.)\1{%d,}" % (veces - 1), valor.lower()) is not None


def _letras(valor: str) -> int:
    return sum(c.isalpha() for c in valor)


def nombre_lugar(valor: str) -> str:
    valor = _limpiar(valor)
    if len(valor) < 3:
        raise ValueError("El nombre debe tener al menos 3 caracteres")
    if len(valor) > LARGO_NOMBRE:
        raise ValueError(f"El nombre puede tener como máximo {LARGO_NOMBRE} caracteres")
    if not _LUGAR.fullmatch(valor):
        raise ValueError("El nombre solo puede tener letras, números, espacios y los signos . , - ' & ( ) /")
    if _letras(valor) < 3:
        raise ValueError("El nombre debe tener al menos 3 letras")
    if _repite(valor, 4):
        raise ValueError("El nombre repite el mismo carácter demasiadas veces seguidas")
    if parece_sin_sentido(valor):
        raise ValueError(NO_PARECE_REAL)
    return valor


def nombre_lugar_opcional(valor: str) -> str:
    return nombre_lugar(valor) if _limpiar(valor) else ""


def nombre_persona(valor: str) -> str:
    valor = _limpiar(valor)
    if len(valor) < 3:
        raise ValueError("El nombre debe tener al menos 3 letras")
    if len(valor) > LARGO_NOMBRE:
        raise ValueError(f"El nombre puede tener como máximo {LARGO_NOMBRE} caracteres")
    if not _PERSONA.fullmatch(valor):
        raise ValueError("El nombre de una persona solo puede tener letras y espacios")
    if _letras(valor) < 3:
        raise ValueError("El nombre debe tener al menos 3 letras")
    if _repite(valor, 3):
        raise ValueError("El nombre repite la misma letra demasiadas veces seguidas")
    if parece_sin_sentido(valor):
        raise ValueError(NO_PARECE_REAL)
    return valor


def guia_remision(valor: str) -> str:
    valor = _limpiar(valor).upper()
    if not valor:
        return ""
    if len(valor) > LARGO_GUIA:
        raise ValueError(f"La guía puede tener como máximo {LARGO_GUIA} caracteres")
    if not _GUIA.fullmatch(valor) or not any(c.isdigit() for c in valor):
        raise ValueError("La guía solo puede tener letras, números y guiones (por ejemplo, T001-004512)")
    return valor


# Largo bruto generoso (antes de limpiar espacios); el límite real lo aplica cada validador.
NombreLugar = Annotated[str, Field(max_length=200), AfterValidator(nombre_lugar)]
NombreLugarOpcional = Annotated[str, Field(default="", max_length=200), AfterValidator(nombre_lugar_opcional)]
NombrePersona = Annotated[str, Field(max_length=200), AfterValidator(nombre_persona)]
GuiaRemision = Annotated[str, Field(default="", max_length=60), AfterValidator(guia_remision)]
