import re

from rapidfuzz import fuzz, process
from .normalizador import normalizar_texto_completo

class BuscadorAmbito:
    ALIAS_GEOGRAFICOS = {
        "cdmx": {
            "tipo": "ENTIDAD",
            "id": "09",
        },
    }

    EQUIVALENCIAS_OOAD = {
        "ciudad de mexico": "cdmx",
    }

    CONECTORES_OOAD = {
        "de",
        "del",
        "el",
        "en",
        "la",
        "las",
        "los",
    }

    def __init__(self, catalogos):
        self.catalogos = catalogos
        self.lista_geografica = [item["desc_normalizada"] for item in catalogos.catalogo_geografico_unificado]
        self.lista_niveles = [n["desc_normalizada"] for n in catalogos.catalogo_niveles]
        self.catalogo_geografico_sin_niveles = [
            item
            for item in catalogos.catalogo_geografico_unificado
            if item["tipo"] != "NIVEL_ATENCION"
        ]
        self.lista_geografica_sin_niveles = [
            item["desc_normalizada"]
            for item in self.catalogo_geografico_sin_niveles
        ]
        self.lista_ooad = [
            item["desc_normalizada"]
            for item in catalogos.catalogo_ooad
        ]

        # Estas delegaciones tienen prioridad si no se indica el ámbito.
        self.DELEGACIONES_ESPECIALES = {
            "mexico oriente", "mexico poniente", 
            "ciudad de mexico norte", "ciudad de mexico sur", 
            "veracruz norte", "veracruz sur"
        }

    def buscar(self, pregunta_normalizada):
        def contiene_frase(texto, frase):
            return f" {frase} " in f" {texto} "

        nivel_atencion = next(
            (
                {
                    "tipo": "NIVEL_ATENCION",
                    "id": nivel["id"],
                    "descripcion": nivel["desc_original"],
                }
                for nivel in self.catalogos.catalogo_niveles
                if contiene_frase(
                    pregunta_normalizada,
                    nivel["desc_normalizada"],
                )
            ),
            None,
        )

        if any(w in pregunta_normalizada for w in ["nacional", "todo el pais", "republica", "todos los hospitales"]):
            resultado_nacional = {
                "tipo": "NACIONAL",
                "id": "NACIONAL",
                "desc_original": "Nacional",
                "texto_usado": "nacional",
                "score": 100.0,
            }
            if nivel_atencion:
                resultado_nacional["nivel_atencion"] = nivel_atencion
            return resultado_nacional

        forzar_region = any(w in pregunta_normalizada for w in ["region", "regiones"])
        forzar_delegacion = any(w in pregunta_normalizada for w in ["delegacion", "delegaciones"])
        forzar_entidad = any(w in pregunta_normalizada for w in ["estado", "estados", "entidad", "entidades"])
        forzar_ooad = "ooad" in pregunta_normalizada.split()

        UMBRAL_GEOGRAFICO = 85.0

        if forzar_ooad:
            pregunta_ooad = self._normalizar_texto_ooad(
                pregunta_normalizada
            )
            texto_ooad = self._extraer_texto_ooad(pregunta_ooad)

            coincidencias_exactas = [
                item
                for item in self.catalogos.catalogo_ooad
                if contiene_frase(
                    pregunta_ooad,
                    item["desc_normalizada"],
                )
            ]
            if coincidencias_exactas:
                item_ooad = max(
                    coincidencias_exactas,
                    key=lambda item: len(
                        item["desc_normalizada"].split()
                    ),
                )
                return self._crear_resultado_ooad(
                    item_ooad,
                    100.0,
                    nivel_atencion,
                )

            # Un token direccional aislado (por ejemplo, "sur") no
            # identifica de forma segura una OOAD. Los nombres válidos de
            # un solo token ya se resolvieron arriba por coincidencia exacta.
            if len(texto_ooad.split()) < 2:
                matches_ooad = []
            else:
                matches_ooad = process.extract(
                    texto_ooad,
                    self.lista_ooad,
                    scorer=fuzz.WRatio,
                    score_cutoff=UMBRAL_GEOGRAFICO,
                    limit=2,
                )

            # No elegir arbitrariamente cuando el fuzzy produce un empate.
            if (
                len(matches_ooad) > 1
                and matches_ooad[0][1] == matches_ooad[1][1]
            ):
                matches_ooad = []

            if matches_ooad:
                _, score, indice = matches_ooad[0]
                return self._crear_resultado_ooad(
                    self.catalogos.catalogo_ooad[indice],
                    score,
                    nivel_atencion,
                )

            return {
                "tipo": "HOSPITAL",
                "id": None,
                "texto_usado": "",
                "score": 0.0,
            }

        for alias, referencia in self.ALIAS_GEOGRAFICOS.items():
            if not contiene_frase(pregunta_normalizada, alias):
                continue

            item_alias = next(
                (
                    item
                    for item in self.catalogos.catalogo_geografico_unificado
                    if item["tipo"] == referencia["tipo"]
                    and str(item["id"]) == referencia["id"]
                ),
                None,
            )
            if item_alias:
                resultado_alias = {
                    "tipo": item_alias["tipo"],
                    "id": item_alias["id"],
                    "desc_original": item_alias.get("desc_original"),
                    "texto_usado": alias,
                    "score": 100.0,
                }
                if nivel_atencion:
                    resultado_alias["nivel_atencion"] = nivel_atencion
                return resultado_alias

        matches_geo = process.extract(
            pregunta_normalizada,
            self.lista_geografica_sin_niveles,
            scorer=fuzz.partial_token_set_ratio,
            score_cutoff=UMBRAL_GEOGRAFICO,
            limit=8,
        )

        if not matches_geo:
            if nivel_atencion:
                return {
                    "tipo": "NIVEL_ATENCION",
                    "id": nivel_atencion["id"],
                    "desc_original": nivel_atencion["descripcion"],
                    "texto_usado": str(nivel_atencion["id"]).lower(),
                    "score": 100.0,
                    "nivel_atencion": nivel_atencion,
                }
            return {
                "tipo": "HOSPITAL",
                "id": None,
                "texto_usado": "",
                "score": 0.0,
            }

        candidatos = []

        for texto, score, indice in matches_geo:
            item = self.catalogo_geografico_sin_niveles[indice]
            desc = item["desc_normalizada"]

            exacto_en_pregunta = contiene_frase(pregunta_normalizada, desc)

            prioridad_tipo = 0
            if forzar_region and item["tipo"] == "REGION":
                prioridad_tipo = 3
            elif forzar_delegacion and item["tipo"] == "DELEGACION":
                prioridad_tipo = 3
            elif forzar_entidad and item["tipo"] == "ENTIDAD":
                prioridad_tipo = 3

            candidatos.append({
                "item": item,
                "score": score,
                "texto": texto,
                "exacto_en_pregunta": exacto_en_pregunta,
                "tokens_exactos": item["longitud_tokens"] if exacto_en_pregunta else 0,
                "prioridad_tipo": prioridad_tipo,
            })

        if forzar_region:
            candidatos = [
                c for c in candidatos
                if c["item"]["tipo"] == "REGION"
            ]

        elif forzar_delegacion:
            candidatos = [
                c for c in candidatos
                if c["item"]["tipo"] == "DELEGACION"
            ]

        elif forzar_entidad:
            candidatos = [
                c for c in candidatos
                if c["item"]["tipo"] == "ENTIDAD"
            ]

        if not candidatos:
            return {
                "tipo": "HOSPITAL",
                "id": None,
                "texto_usado": "",
                "score": 0.0,
            }
        candidatos_ordenados = sorted(
            candidatos,
            key=lambda x: (
                x["exacto_en_pregunta"],
                x["tokens_exactos"],
                x["prioridad_tipo"],
                x["score"],
                -x["item"]["longitud_tokens"],
            ),
            reverse=True,
        )

        mejor_candidato = candidatos_ordenados[0]

        if not mejor_candidato["exacto_en_pregunta"] and not (
            forzar_region or forzar_delegacion or forzar_entidad
        ):
            if nivel_atencion:
                return {
                    "tipo": "NIVEL_ATENCION",
                    "id": nivel_atencion["id"],
                    "desc_original": nivel_atencion["descripcion"],
                    "texto_usado": str(nivel_atencion["id"]).lower(),
                    "score": 100.0,
                    "nivel_atencion": nivel_atencion,
                }
            return {
                "tipo": "HOSPITAL",
                "id": None,
                "texto_usado": "",
                "score": 0.0,
            }

        ganador = mejor_candidato["item"]
        score_ganador = mejor_candidato["score"]
        texto_match = ganador["desc_normalizada"]
        tipo_ganador = ganador["tipo"]

        if tipo_ganador == "REGION":
            tipo_final = tipo_ganador
        elif forzar_delegacion:
            tipo_final = "DELEGACION"
        elif forzar_entidad:
            tipo_final = "ENTIDAD"
        elif texto_match in self.DELEGACIONES_ESPECIALES:
            tipo_final = "DELEGACION"
        else:
            tipo_final = "ENTIDAD"

        item_final = ganador

        for item in self.catalogos.catalogo_geografico_unificado:
            if (
                item["desc_normalizada"] == texto_match
                and item["tipo"] == tipo_final
            ):
                item_final = item
                break

        resultado = {
            "tipo": item_final["tipo"],
            "id": item_final["id"],
            "desc_original": item_final.get("desc_original"),
            "texto_usado": item_final["desc_normalizada"],
            "score": score_ganador,
        }
        if nivel_atencion:
            resultado["nivel_atencion"] = nivel_atencion
        return resultado

    def _normalizar_texto_ooad(self, texto):
        texto_normalizado = normalizar_texto_completo(texto)
        for original, reemplazo in self.EQUIVALENCIAS_OOAD.items():
            texto_normalizado = re.sub(
                rf"\b{re.escape(original)}\b",
                reemplazo,
                texto_normalizado,
            )
        return texto_normalizado

    def _extraer_texto_ooad(self, pregunta_normalizada):
        tokens = pregunta_normalizada.split()
        indice_ooad = tokens.index("ooad")

        tokens_posteriores = tokens[indice_ooad + 1 :]
        while (
            tokens_posteriores
            and tokens_posteriores[0] in self.CONECTORES_OOAD
        ):
            tokens_posteriores.pop(0)

        if tokens_posteriores:
            return " ".join(tokens_posteriores)

        # Conserva compatibilidad con formulaciones que colocan el nombre
        # antes del marcador OOAD. Las coincidencias exactas se resolvieron
        # previamente; este fragmento solo alimenta el fallback fuzzy.
        tokens_anteriores = tokens[:indice_ooad]
        while (
            tokens_anteriores
            and tokens_anteriores[-1] in self.CONECTORES_OOAD
        ):
            tokens_anteriores.pop()
        return " ".join(tokens_anteriores[-4:])

    @staticmethod
    def _crear_resultado_ooad(item_ooad, score, nivel_atencion):
        resultado_ooad = {
            "tipo": "OOAD",
            "id": item_ooad["id"],
            "desc_original": item_ooad["desc_original"],
            "texto_usado": item_ooad["desc_normalizada"],
            "score": score,
        }
        if nivel_atencion:
            resultado_ooad["nivel_atencion"] = nivel_atencion
        return resultado_ooad
