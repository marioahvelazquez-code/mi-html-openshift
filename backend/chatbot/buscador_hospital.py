"""Busca hospitales con BM25 y RapidFuzz."""

import numpy as np
from rapidfuzz import fuzz

from .constantes import DELTA_EMPATE, PALABRAS_BASURA_HOSPITAL, UMBRAL_HOSPITAL
from .normalizador import generar_trigramas, normalizar_texto_completo, quitar_palabras_basura


class BuscadorHospital:
    def __init__(self, catalogos):
        self.catalogos = catalogos

    def buscar(self, pregunta_usuario):
        texto_hospital = self._preparar_texto(pregunta_usuario)

        if not texto_hospital:
            return {
                "status": "sin_texto",
                "hospital": None,
                "score": 0.0,
                "texto_usado": texto_hospital,
            }

        tokens_pregunta = generar_trigramas(texto_hospital)
        scores_bm25 = self.catalogos.bm25_hospitales.get_scores(tokens_pregunta)
        max_bm25 = np.max(scores_bm25) if np.max(scores_bm25) > 0 else 1
        scores_bm25_norm = scores_bm25 / max_bm25

        scores_fuzz = np.array([
            fuzz.WRatio(texto_hospital, nombre) / 100.0
            for nombre in self.catalogos.nombres_hospitales_lista
        ])

        scores_finales = (scores_bm25_norm * 0.50) + (scores_fuzz * 0.50)
        indices_ordenados = np.argsort(scores_finales)[::-1]

        idx1 = indices_ordenados[0]
        idx2 = indices_ordenados[1]
        mejor_score = scores_finales[idx1]
        segundo_score = scores_finales[idx2]

        if mejor_score < UMBRAL_HOSPITAL:
            return {
                "status": "baja_confianza",
                "hospital": None,
                "score": float(mejor_score),
                "texto_usado": texto_hospital,
                "candidatos": [],
            }

        if mejor_score - segundo_score <= DELTA_EMPATE:
            candidatos = []
            for idx in indices_ordenados:
                if mejor_score - scores_finales[idx] <= DELTA_EMPATE:
                    candidatos.append(self._candidato(idx, scores_finales))
                else:
                    break

            return {
                "status": "empate_tecnico",
                "hospital": None,
                "score": float(mejor_score),
                "texto_usado": texto_hospital,
                "candidatos": candidatos,
            }

        return {
            "status": "ganador_claro",
            "hospital": self.catalogos.catalogo_hospitales[idx1],
            "score": float(mejor_score),
            "texto_usado": texto_hospital,
        }

    @staticmethod
    def _preparar_texto(pregunta_usuario):
        texto = normalizar_texto_completo(pregunta_usuario)
        return quitar_palabras_basura(texto, PALABRAS_BASURA_HOSPITAL)

    def _candidato(self, idx, scores_finales):
        hospital = self.catalogos.catalogo_hospitales[idx]
        return {
            "id": hospital["id"],
            "descripcion": hospital["desc_original"],
            "score": float(scores_finales[idx]),
        }
