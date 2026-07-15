"""Busca variables médicas con BM25 y RapidFuzz."""

import re

import numpy as np
from rapidfuzz import fuzz

from .constantes import (
    DELTA_EMPATE,
    PALABRAS_BASURA_VARIABLE,
    UMBRAL_VARIABLE,
    VARIABLES_CANONICAS,
)
from .normalizador import normalizar_texto_completo, quitar_palabras_basura


class BuscadorVariable:
    def __init__(self, catalogos):
        self.catalogos = catalogos

    def buscar(self, pregunta_usuario, hospital_detectado=None, aplicar_canonica=True):
        texto_variable = self._preparar_texto(pregunta_usuario, hospital_detectado)

        if not texto_variable:
            return {
                "status": "sin_texto",
                "variable": None,
                "score": 0.0,
                "texto_usado": texto_variable,
            }

        if aplicar_canonica:
            variable_canonica = self.buscar_variable_canonica(texto_variable)
            if variable_canonica:
                return {
                    "status": "ganador_claro",
                    "variable": variable_canonica,
                    "score": 1.0,
                    "texto_usado": texto_variable,
                    "regla_aplicada": "variable_canonica",
                }

        tokens_pregunta = texto_variable.split()
        scores_bm25 = self.catalogos.bm25_variables.get_scores(tokens_pregunta)
        max_bm25 = np.max(scores_bm25) if np.max(scores_bm25) > 0 else 1
        scores_bm25_norm = scores_bm25 / max_bm25

        scores_fuzz = np.array([
            fuzz.WRatio(texto_variable, nombre) / 100.0
            for nombre in self.catalogos.nombres_variables_lista
        ])

        scores_finales = (scores_bm25_norm * 0.60) + (scores_fuzz * 0.40)

        # Distingue camas censables de camas no censables.
        pide_censables = "censables" in texto_variable
        pide_no_censables = "no censables" in texto_variable
        especialidades = {
            "medicina",
            "cirugia",
            "urgencias",
            "pediatria",
            "ginecologia",
            "obstetricia",
            "terapia",
            "intensiva",
        }
        tokens_variable = set(texto_variable.split())
        menciona_especialidad = bool(tokens_variable & especialidades)

        if pide_censables:
            for idx, variable in enumerate(self.catalogos.catalogo_variables):
                desc = variable["desc_normalizada"]
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
