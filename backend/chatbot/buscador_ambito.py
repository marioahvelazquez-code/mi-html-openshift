from rapidfuzz import fuzz, process
from .normalizador import normalizar_texto_completo

class BuscadorAmbito:
    def __init__(self, catalogos):
        self.catalogos = catalogos
        self.lista_geografica = [item["desc_normalizada"] for item in catalogos.catalogo_geografico_unificado]
        self.lista_niveles = [n["desc_normalizada"] for n in catalogos.catalogo_niveles]

        # Estas delegaciones tienen prioridad si no se indica el ámbito.
        self.DELEGACIONES_ESPECIALES = {
            "mexico oriente", "mexico poniente", 
            "ciudad de mexico norte", "ciudad de mexico sur", 
            "veracruz norte", "veracruz sur"
        }

    def buscar(self, pregunta_normalizada):
        def contiene_frase(texto, frase):
            return f" {frase} " in f" {texto} "

        if any(w in pregunta_normalizada for w in ["nacional", "todo el pais", "republica", "todos los hospitales"]):
            return {
                "tipo": "NACIONAL",
                "id": "NACIONAL",
                "desc_original": "Nacional",
                "texto_usado": "nacional",
                "score": 100.0,
            }

        forzar_region = any(w in pregunta_normalizada for w in ["region", "regiones"])
        forzar_delegacion = any(w in pregunta_normalizada for w in ["delegacion", "delegaciones"])
        forzar_entidad = any(w in pregunta_normalizada for w in ["estado", "estados", "entidad", "entidades"])
        forzar_nivel = any(w in pregunta_normalizada for w in ["nivel", "primer nivel", "segundo nivel", "tercer nivel"])

        UMBRAL_GEOGRAFICO = 85.0

        matches_geo = process.extract(
            pregunta_normalizada,
            self.lista_geografica,
            scorer=fuzz.partial_token_set_ratio,
            score_cutoff=UMBRAL_GEOGRAFICO,
            limit=8,
        )

        if not matches_geo:
            return {
                "tipo": "HOSPITAL",
                "id": None,
                "texto_usado": "",
                "score": 0.0,
            }

        candidatos = []

        for texto, score, indice in matches_geo:
            item = self.catalogos.catalogo_geografico_unificado[indice]
            desc = item["desc_normalizada"]

            exacto_en_pregunta = contiene_frase(pregunta_normalizada, desc)

            prioridad_tipo = 0
            if forzar_region and item["tipo"] == "REGION":
                prioridad_tipo = 3
            elif forzar_nivel and item["tipo"] == "NIVEL_ATENCION":
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

        elif forzar_nivel:
            candidatos = [
                c for c in candidatos
                if c["item"]["tipo"] == "NIVEL_ATENCION"
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
            forzar_region or forzar_nivel or forzar_delegacion or forzar_entidad
        ):
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

        if tipo_ganador in {"REGION", "NIVEL_ATENCION"}:
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

        return {
            "tipo": item_final["tipo"],
            "id": item_final["id"],
            "desc_original": item_final.get("desc_original"),
            "texto_usado": item_final["desc_normalizada"],
            "score": score_ganador,
        }
