"""Busca variables médicas con BM25 y RapidFuzz."""

import re
import unicodedata

import numpy as np
from rapidfuzz import fuzz
from rank_bm25 import BM25Okapi

from .constantes import (
    DELTA_EMPATE,
    PALABRAS_BASURA_VARIABLE,
    UMBRAL_VARIABLE,
    VARIABLES_CANONICAS,
)
from .normalizador import normalizar_texto_completo, quitar_palabras_basura


EQUIVALENCIAS_SINGULAR_PLURAL = {
    "urgencias": "urgencia",
    "camas": "cama",
    "hospitales": "hospital",
    "consultorios": "consultorio",
    "quirofanos": "quirofano",
    "unidades": "unidad",
}

# Política independiente del ranking: solo estas equivalencias explícitas.
EQUIVALENCIAS_TOKENS_EXACTOS = {
    "camas": "cama",
    "consultorios": "consultorio",
}

TOKENS_BASE_URGENCIA = {
    "cama",
    "urgencia",
    "unidad",
}

TOKENS_NEUTROS_DESCRIPCION = {
    "de",
    "del",
    "el",
    "en",
    "la",
    "total",
}


class BuscadorVariable:
    def __init__(self, catalogos):
        self.catalogos = catalogos
        self.nombres_variables_normalizados = [
            self._normalizar_para_similitud(nombre)
            for nombre in self.catalogos.nombres_variables_lista
        ]
        self.bm25_variables_normalizado = BM25Okapi([
            nombre.split()
            for nombre in self.nombres_variables_normalizados
        ])
        self._variables_por_clave = {
            str(variable["id"]): variable
            for variable in self.catalogos.catalogo_variables
        }
        self._indice_tokens = {}
        for clave, variable in self._variables_por_clave.items():
            for token in self._tokens_exactos(variable["desc_original"]):
                self._indice_tokens.setdefault(token, set()).add(clave)

    @staticmethod
    def _tokens_exactos(texto):
        """Palabras completas sin parches, stopwords ni equivalencias implícitas."""
        if not isinstance(texto, str):
            return set()
        texto = unicodedata.normalize("NFD", texto.lower())
        texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
        return {
            EQUIVALENCIAS_TOKENS_EXACTOS.get(token, token)
            for token in re.findall(r"[^\W_]+", texto, flags=re.UNICODE)
        }

    def _resultados_exactos(self, claves):
        return [
            {
                "id": self._variables_por_clave[clave]["id"],
                "descripcion": self._variables_por_clave[clave]["desc_original"],
            }
            for clave in sorted(claves, key=lambda valor: (int(valor), valor))
        ]

    def buscar_por_clave(self, clave):
        """Lista de cero o una variable. No extrae números de preguntas.

        Acepta un entero o una cadena decimal completa (espacios externos
        permitidos). La interpretación de cantidades u hospitales corresponde
        al futuro coordinador; este método solo consulta el catálogo IFU.
        """
        if type(clave) is int:
            clave = str(clave)
        if not isinstance(clave, str):
            return []
        clave = clave.strip()
        if not re.fullmatch(r"[0-9]+", clave):
            return []
        return self._resultados_exactos([clave]) if clave in self._variables_por_clave else []

    def buscar_por_tokens(self, texto):
        """Todas las coincidencias AND, ordenadas por clave numérica ascendente."""
        tokens = self._tokens_exactos(texto)
        if not tokens:
            return []
        conjuntos = [self._indice_tokens.get(token, set()) for token in tokens]
        conjuntos.sort(key=len)
        claves = conjuntos[0].intersection(*conjuntos[1:])
        return self._resultados_exactos(claves)

    def buscar(self, pregunta_usuario, hospital_detectado=None, aplicar_canonica=True):
        texto_variable = self._preparar_texto(pregunta_usuario, hospital_detectado)

        if not texto_variable:
            return {
                "status": "sin_texto",
                "variable": None,
                "score": 0.0,
                "texto_usado": texto_variable,
            }

        texto_variable_similitud = self._normalizar_para_similitud(texto_variable)

        if aplicar_canonica:
            variable_canonica = self.buscar_variable_canonica(
                texto_variable_similitud
            )
            if variable_canonica:
                return {
                    "status": "ganador_claro",
                    "variable": variable_canonica,
                    "score": 1.0,
                    "texto_usado": texto_variable,
                    "regla_aplicada": "variable_canonica",
                }

        tokens_pregunta = texto_variable_similitud.split()
        scores_bm25 = self.bm25_variables_normalizado.get_scores(tokens_pregunta)
        max_bm25 = np.max(scores_bm25) if np.max(scores_bm25) > 0 else 1
        scores_bm25_norm = scores_bm25 / max_bm25

        scores_fuzz = np.array([
            fuzz.WRatio(texto_variable_similitud, nombre) / 100.0
            for nombre in self.nombres_variables_normalizados
        ])

        scores_finales = (scores_bm25_norm * 0.60) + (scores_fuzz * 0.40)

        # Distingue camas censables de camas no censables.
        pide_censables = "censables" in texto_variable_similitud
        pide_no_censables = "no censables" in texto_variable_similitud
        especialidades = {
            "medicina",
            "cirugia",
            "urgencia",
            "pediatria",
            "ginecologia",
            "obstetricia",
            "terapia",
            "intensiva",
        }
        tokens_variable = set(texto_variable_similitud.split())
        menciona_especialidad = bool(tokens_variable & especialidades)

        if pide_censables:
            for idx, variable in enumerate(self.catalogos.catalogo_variables):
                desc = self.nombres_variables_normalizados[idx]
                desc_tiene_no_censables = "no censables" in desc
                desc_tiene_censables = "censables" in desc
                desc_tiene_especialidad = any(
                    especialidad in desc
                    for especialidad in especialidades
                )

                if pide_no_censables:
                    # Baja las opciones que omiten la negación.
                    if desc_tiene_censables and not desc_tiene_no_censables:
                        scores_finales[idx] -= 0.35
                else:
                    # Baja las opciones de camas no censables.
                    if desc_tiene_no_censables:
                        scores_finales[idx] -= 0.35

                    # Prioriza el total de la unidad si no hay especialidad.
                    if not menciona_especialidad:
                        if "unidad" in desc and not desc_tiene_no_censables:
                            scores_finales[idx] += 0.15
                        if desc_tiene_especialidad:
                            scores_finales[idx] -= 0.12

        scores_finales = self._aplicar_prioridad_urgencia(
            scores_finales,
            tokens_variable,
        )

        scores_finales = np.clip(scores_finales, 0, None)
        indices_ordenados = np.argsort(scores_finales)[::-1]

        idx1 = indices_ordenados[0]
        idx2 = indices_ordenados[1]
        mejor_score = scores_finales[idx1]
        segundo_score = scores_finales[idx2]

        if mejor_score < UMBRAL_VARIABLE:
            return {
                "status": "baja_confianza",
                "variable": None,
                "score": float(mejor_score),
                "texto_usado": texto_variable,
                "candidatos": [
                    self._candidato_baja_confianza(idx, scores_finales)
                    for idx in indices_ordenados[:5]
                ],
            }

        if mejor_score - segundo_score <= DELTA_EMPATE:
            candidatos = []
            for idx in indices_ordenados:
                if mejor_score - scores_finales[idx] <= DELTA_EMPATE:
                    candidatos.append(self._candidato_empate(idx, scores_finales))
                else:
                    break

            return {
                "status": "empate_tecnico",
                "variable": None,
                "score": float(mejor_score),
                "texto_usado": texto_variable,
                "candidatos": candidatos,
            }

        return {
            "status": "ganador_claro",
            "variable": self.catalogos.catalogo_variables[idx1],
            "score": float(mejor_score),
            "texto_usado": texto_variable,
        }

    @staticmethod
    def _preparar_texto(pregunta_usuario, hospital_detectado=None):
        texto = normalizar_texto_completo(pregunta_usuario)

        if hospital_detectado:
            desc_hospital = (
                hospital_detectado.get("desc_normalizada")
                or hospital_detectado.get("nombre_original")
                or hospital_detectado.get("desc_original")
                or ""
            )
            desc_hospital = normalizar_texto_completo(desc_hospital)
            for palabra in desc_hospital.split():
                texto = texto.replace(palabra, " ")

        texto = quitar_palabras_basura(texto, PALABRAS_BASURA_VARIABLE)
        return re.sub(r"\s+", " ", texto).strip()

    @staticmethod
    def _normalizar_para_similitud(texto):
        texto_normalizado = normalizar_texto_completo(texto)
        return " ".join(
            EQUIVALENCIAS_SINGULAR_PLURAL.get(token, token)
            for token in texto_normalizado.split()
        )

    def _aplicar_prioridad_urgencia(self, scores, tokens_consulta):
        if "urgencia" not in tokens_consulta:
            return scores

        tokens_especificos_consulta = (
            tokens_consulta
            - TOKENS_BASE_URGENCIA
            - TOKENS_NEUTROS_DESCRIPCION
        )

        for idx, descripcion in enumerate(self.nombres_variables_normalizados):
            tokens_candidato = set(descripcion.split())
            if "urgencia" not in tokens_candidato:
                scores[idx] -= 0.20
                continue

            scores[idx] += 0.08

            if not tokens_especificos_consulta:
                tokens_especificos_candidato = (
                    tokens_candidato
                    - TOKENS_BASE_URGENCIA
                    - TOKENS_NEUTROS_DESCRIPCION
                )
                if tokens_especificos_candidato:
                    scores[idx] -= 0.05
                else:
                    scores[idx] += 0.12

        return scores

    def buscar_variable_canonica(self, texto_variable):
        tokens_consulta = set((texto_variable or "").split())
        if not tokens_consulta:
            return None

        for regla in VARIABLES_CANONICAS.values():
            coincide_solo_con_tokens_genericos = tokens_consulta.issubset(
                regla["tokens_genericos"]
            )
            cumple_grupos_requeridos = all(
                tokens_consulta & grupo
                for grupo in regla["grupos_requeridos"]
            )
            if coincide_solo_con_tokens_genericos and cumple_grupos_requeridos:
                descripcion_objetivo = regla["descripcion_objetivo"]
                for variable in self.catalogos.catalogo_variables:
                    if variable.get("desc_normalizada") == descripcion_objetivo:
                        return variable

        return None

    def _candidato_baja_confianza(self, idx, scores_finales):
        variable = self.catalogos.catalogo_variables[idx]
        return {
            "id": variable["id"],
            "descripcion": variable["desc_original"],
            "score": float(scores_finales[idx]),
        }

    def _candidato_empate(self, idx, scores_finales):
        variable = self.catalogos.catalogo_variables[idx]
        return {
            "id": variable["id"],
            "descripcion": variable["desc_original"],
            "score": float(scores_finales[idx]),
        }
