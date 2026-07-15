"""Carga los catálogos y sus índices BM25."""

import json
from pathlib import Path

from rank_bm25 import BM25Okapi

from .normalizador import generar_trigramas


class Catalogos:
    def __init__(self):
        base_dir = Path(__file__).resolve().parent / "catalogos"
        self.catalogo_hospitales = self._cargar_json(base_dir / "catalogo_cuums_abr.json")
        self.catalogo_variables = self._cargar_json(base_dir / "catalogo_variables.json")

        self.catalogo_delegaciones = self._cargar_json(base_dir / "catalogo_delegacion.json")
        self.catalogo_entidades = self._cargar_json(base_dir / "catalogo_entidad.json")
        self.catalogo_niveles = self._cargar_json(base_dir / "catalogo_nivel.json")
        self.catalogo_regiones = self._cargar_json(base_dir / "catalogo_region.json")

        # Mantiene compatibilidad con los nombres anteriores.
        self.catalogo_delegacion = self.catalogo_delegaciones
        self.catalogo_entidad = self.catalogo_entidades
        self.catalogo_nivel = self.catalogo_niveles
        self.catalogo_region = self.catalogo_regiones

        # Permite buscar por delegación o entidad.
        self.catalogo_geografico_unificado = []

        for delegacion in self.catalogo_delegaciones:
            desc_norm = delegacion["desc_normalizada"].lower()
            self.catalogo_geografico_unificado.append({
                "tipo": "DELEGACION",
                "id": delegacion["id"],
                "desc_original": delegacion["desc_original"],
                "desc_normalizada": desc_norm,
                "longitud_tokens": len(desc_norm.split()),
            })

        # Jalisco puede aparecer como entidad y como delegación.
        for entidad in self.catalogo_entidades:
            desc_norm = entidad["desc_normalizada"].lower()
            self.catalogo_geografico_unificado.append({
                "tipo": "ENTIDAD",
                "id": entidad["id"],
                "desc_original": entidad["desc_original"],
                "desc_normalizada": desc_norm,
                "longitud_tokens": len(desc_norm.split()),
            })
        for region in self.catalogo_regiones:
            desc_norm = region["desc_normalizada"].lower()
            self.catalogo_geografico_unificado.append({
                "tipo": "REGION",
                "id": region["id"],
                "desc_original": region["desc_original"],
                "desc_normalizada": desc_norm,
                "longitud_tokens": len(desc_norm.split()),
            })

        for nivel in self.catalogo_niveles:
            desc_norm = nivel["desc_normalizada"].lower()
            self.catalogo_geografico_unificado.append({
                "tipo": "NIVEL_ATENCION",
                "id": nivel["id"],
                "desc_original": nivel["desc_original"],
                "desc_normalizada": desc_norm,
                "longitud_tokens": len(desc_norm.split()),
            })
            
        corpus_hospitales_trigramas = [
            generar_trigramas(hospital["desc_normalizada"])
            for hospital in self.catalogo_hospitales
        ]
        self.bm25_hospitales = BM25Okapi(corpus_hospitales_trigramas)
        self.nombres_hospitales_lista = [
            hospital["desc_normalizada"]
            for hospital in self.catalogo_hospitales
        ]

        corpus_variables = [
            variable["desc_normalizada"].split()
            for variable in self.catalogo_variables
        ]
        self.bm25_variables = BM25Okapi(corpus_variables)
        self.nombres_variables_lista = [
            variable["desc_normalizada"]
            for variable in self.catalogo_variables
        ]

    @staticmethod
    def _cargar_json(ruta):
        with ruta.open("r", encoding="utf-8") as archivo:
            return json.load(archivo)


catalogos = Catalogos()
