"""Limpia texto y genera tokens."""

import re
import unicodedata

from .constantes import PARCHES_TEXTO


def normalizar_texto_completo(texto):
    if not texto:
        return ""

    texto = str(texto).lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")

    signos_a_quitar = r"[¿?¡!_!\"#=$%&/()\*+\-.,:;–—']"
    texto = re.sub(signos_a_quitar, " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()

    for original, reemplazo in PARCHES_TEXTO.items():
        texto = texto.replace(original, reemplazo)

    return texto.strip()


def quitar_palabras_basura(texto, palabras_basura):
    palabras = texto.split()
    palabras_limpias = [p for p in palabras if p not in palabras_basura]
    return " ".join(palabras_limpias).strip()


def generar_trigramas(texto):
    texto = texto.replace(" ", "")
    if len(texto) < 3:
        return [texto]
    return [texto[i : i + 3] for i in range(len(texto) - 2)]
