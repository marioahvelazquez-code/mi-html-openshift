from django.http import HttpResponse, JsonResponse, FileResponse
from django.db import connection
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from xml.sax.saxutils import escape
from pathlib import Path
from zoneinfo import ZoneInfo
import base64
import binascii
import re
import subprocess
import pandas as pd
import requests
from difflib import SequenceMatcher

try:
    from sentence_transformers import SentenceTransformer, util as st_util
except Exception:
    SentenceTransformer = None
    st_util = None

from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from chatbot.chatbot_engine import engine as chatbot_detector_engine
from chatbot.consulta_ifu import ConsultaIFU
from chatbot.normalizador import normalizar_texto_completo


chatbot_m_consulta_ifu = ConsultaIFU()

SEMANTIC_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
SEMANTIC_SCORE_MIN = 0.45
_semantic_model = None
_semantic_embeddings_cache = {"key": None, "embeddings": None}


def _normalizar_chatbot_m(texto: str) -> str:
    return normalizar_texto_completo(texto)


def _es_consulta_de_estructura(texto_normalizado: str) -> bool:
    palabras_clave = ("columna", "campos", "estructura", "schema", "esquema")
    return any(palabra in texto_normalizado for palabra in palabras_clave)


def _es_consulta_de_conteo(texto_normalizado: str) -> bool:
    frases = (
        "en total",
        "total de registros",
        "cuantos registros hay",
        "cuantas filas hay",
        "cuantos hay",
        "cuantas hay",
        "cantidad de registros",
    )
    if any(frase in texto_normalizado for frase in frases):
        return True

    patrones = (
        r"\bcuant[oa]s?\s+(hospital(?:es)?|unidades?)\s+tienen\b",
        r"\bcuant[oa]s?\s+claves?\s+presupuestales\s+tienen\b",
        r"\bcuant[oa]s?\s+(hospital(?:es)?|unidades?)\s+hay\b",
        r"\bcuant[oa]s?\b.*\bhay\b",
        r"\bcuant[oa]s?\b.*\btienen\b",
    )
    return any(re.search(patron, texto_normalizado) for patron in patrones)


def _es_consulta_comparativa(texto_normalizado: str) -> bool:
    frases = (
        "que hospital tiene mas",
        "cual hospital tiene mas",
        "que hospital tiene menos",
        "cual hospital tiene menos",
        "hospital con mas",
        "hospital con menos",
        "mayor",
        "menor",
        "maximo",
        "minimo",
        "top",
        "lider",
    )
    return any(frase in texto_normalizado for frase in frases)


def _es_conteo_hospitales_general(texto_normalizado: str) -> bool:
    texto = (texto_normalizado or "").strip()
    patrones = (
        r"\bcuant[oa]s?\s+hospital(?:es)?\s+hay\b",
        r"\bcuant[oa]s?\s+hospital(?:es)?\s+tienen\b",
        r"\bcuant[oa]s?\s+unidades?\s+hay\b",
        r"\bcuant[oa]s?\s+unidades?\s+tienen\b",
    )
    if not any(re.search(patron, texto) for patron in patrones):
        return False

    # Si menciona un concepto explícito, no es conteo general.
    if re.search(r"\b(cama|camas|consultorio|consultorios|tomografia|tomografo|variable|descripcion)\b", texto):
        return False
    return True


def _extraer_texto_ambito_desde_pregunta(texto_normalizado: str) -> str:
    texto = str(texto_normalizado or "").strip()
    if not texto:
        return ""
    m = re.search(r"\ben\s+(.+)$", texto)
    if not m:
        return ""
    ambito = m.group(1).strip()
    ambito = re.sub(r"\b(del|de la|de|la|el|los|las)\b", " ", ambito)
    ambito = re.sub(r"\s+", " ", ambito).strip()
    return ambito


def _resolver_ambito_general_desde_cumm(texto_normalizado: str):
    ambito_txt = _extraer_texto_ambito_desde_pregunta(texto_normalizado)
    if not ambito_txt:
        return None

    like_val = f"%{ambito_txt}%"
    with connection.cursor() as cursor:
        # Entidad federativa
        cursor.execute(
            """
            SELECT TOP 1 ClaveEntidadFederativa, EntidadFederativa
            FROM [DB_Catalogos].[dbo].[CUMM_ACTUAL]
            WHERE EntidadFederativa COLLATE Modern_Spanish_CI_AI LIKE %s
            """,
            [like_val],
        )
        row = cursor.fetchone()
        if row:
            return {
                "tipo": "ENTIDAD",
                "id": str(row[0]).strip() if row[0] is not None else "",
                "desc_original": str(row[1]).strip(),
            }

        # Delegación / UMAE
        cursor.execute(
            """
            SELECT TOP 1 Cve_Deleg_UMAE, NombreDelegacionUMAE
            FROM [DB_Catalogos].[dbo].[CUMM_ACTUAL]
            WHERE NombreDelegacionUMAE COLLATE Modern_Spanish_CI_AI LIKE %s
            """,
            [like_val],
        )
        row = cursor.fetchone()
        if row:
            return {
                "tipo": "DELEGACION",
                "id": str(row[0]).strip() if row[0] is not None else "",
                "desc_original": str(row[1]).strip(),
            }

        # Región
        cursor.execute(
            """
            SELECT TOP 1 Region
            FROM [DB_Catalogos].[dbo].[CUMM_ACTUAL]
            WHERE Region COLLATE Modern_Spanish_CI_AI LIKE %s
            """,
            [like_val],
        )
        row = cursor.fetchone()
        if row:
            region = str(row[0]).strip()
            return {
                "tipo": "REGION",
                "id": region,
                "desc_original": region,
            }

        # Nivel de atención
        cursor.execute(
            """
            SELECT TOP 1 NivelAtencion
            FROM [DB_Catalogos].[dbo].[CUMM_ACTUAL]
            WHERE NivelAtencion COLLATE Modern_Spanish_CI_AI LIKE %s
            """,
            [like_val],
        )
        row = cursor.fetchone()
        if row:
            nivel = str(row[0]).strip()
            return {
                "tipo": "NIVEL_ATENCION",
                "id": nivel,
                "desc_original": nivel,
            }

        # Fallback fuzzy para errores ortograficos (ej. "aguscialientes").
        ambito_norm = _normalizar_chatbot_m(ambito_txt)
        mejor = None
        mejor_score = 0.0

        def evaluar(tipo: str, id_val, desc_val):
            nonlocal mejor, mejor_score
            if desc_val is None:
                return
            desc = str(desc_val).strip()
            if not desc:
                return
            desc_norm = _normalizar_chatbot_m(desc)
            score = SequenceMatcher(None, ambito_norm, desc_norm).ratio() * 100
            if score > mejor_score:
                mejor_score = score
                mejor = {
                    "tipo": tipo,
                    "id": str(id_val).strip() if id_val is not None else desc,
                    "desc_original": desc,
                }

        cursor.execute(
            """
            SELECT DISTINCT ClaveEntidadFederativa, EntidadFederativa
            FROM [DB_Catalogos].[dbo].[CUMM_ACTUAL]
            WHERE EntidadFederativa IS NOT NULL AND LTRIM(RTRIM(EntidadFederativa)) <> ''
            """
        )
        for cve, desc in cursor.fetchall() or []:
            evaluar("ENTIDAD", cve, desc)

        cursor.execute(
            """
            SELECT DISTINCT Cve_Deleg_UMAE, NombreDelegacionUMAE
            FROM [DB_Catalogos].[dbo].[CUMM_ACTUAL]
            WHERE NombreDelegacionUMAE IS NOT NULL AND LTRIM(RTRIM(NombreDelegacionUMAE)) <> ''
            """
        )
        for cve, desc in cursor.fetchall() or []:
            evaluar("DELEGACION", cve, desc)

        cursor.execute(
            """
            SELECT DISTINCT Region
            FROM [DB_Catalogos].[dbo].[CUMM_ACTUAL]
            WHERE Region IS NOT NULL AND LTRIM(RTRIM(Region)) <> ''
            """
        )
        for (desc,) in cursor.fetchall() or []:
            evaluar("REGION", desc, desc)

        cursor.execute(
            """
            SELECT DISTINCT NivelAtencion
            FROM [DB_Catalogos].[dbo].[CUMM_ACTUAL]
            WHERE NivelAtencion IS NOT NULL AND LTRIM(RTRIM(NivelAtencion)) <> ''
            """
        )
        for (desc,) in cursor.fetchall() or []:
            evaluar("NIVEL_ATENCION", desc, desc)

        if mejor and mejor_score >= 72:
            return mejor

    return None


def _es_texto_no_consulta(texto_normalizado: str) -> bool:
    texto = (texto_normalizado or "").strip()
    if not texto:
        return True

    saludos = {
        "hola",
        "buen dia",
        "buenos dias",
        "buenas tardes",
        "buenas noches",
        "hey",
        "que tal",
        "ok",
        "gracias",
        "thanks",
    }

    if texto in saludos:
        return True

    tokens = texto.split()
    if len(tokens) == 1 and tokens[0] in saludos:
        return True

    return False


def _debe_intentar_semantica_concepto(texto_busqueda: str) -> bool:
    texto = (texto_busqueda or "").strip()
    if not texto:
        return False
    if _es_texto_no_consulta(texto):
        return False

    tokens = texto.split()
    if len(tokens) < 2:
        return False

    return True


def _detectar_tipo_recurso(texto_normalizado: str):
    texto = (texto_normalizado or "").strip()
    pide_cama = bool(re.search(r"\bcamas?\b", texto))
    pide_consultorio = bool(re.search(r"\bconsultorios?\b", texto))

    if pide_cama and not pide_consultorio:
        return "cama"
    if pide_consultorio and not pide_cama:
        return "consultorio"
    return None


def _descripcion_cumple_tipo_recurso(descripcion_normalizada: str, tipo_recurso: str | None) -> bool:
    if not tipo_recurso:
        return True
    desc = str(descripcion_normalizada or "")
    if tipo_recurso == "cama":
        return "cama" in desc
    if tipo_recurso == "consultorio":
        return "consultorio" in desc
    return True


def _obtener_catalogo_hospitales():
    return chatbot_detector_engine.buscador_hospital.catalogos.catalogo_hospitales


def _obtener_catalogo_variables():
    return chatbot_detector_engine.buscador_variable.catalogos.catalogo_variables


def _resolver_hospital_preciso(pregunta: str):
    texto_hospital = chatbot_detector_engine.buscador_hospital._preparar_texto(pregunta)
    resultado = chatbot_detector_engine.buscador_hospital.buscar(pregunta)

    if resultado.get("status") == "ganador_claro" and resultado.get("hospital"):
        return resultado["hospital"], resultado, texto_hospital

    catalogo = _obtener_catalogo_hospitales()
    texto_limpio = _normalizar_chatbot_m(texto_hospital)
    exactos = []
    for item in catalogo:
        desc = _normalizar_chatbot_m(item.get("desc_normalizada") or item.get("desc_original") or "")
        if not desc:
            continue
        if desc == texto_limpio or desc in texto_limpio or texto_limpio in desc:
            exactos.append(item)

    if len(exactos) == 1:
        return exactos[0], resultado, texto_hospital

    candidatos = resultado.get("candidatos") or []
    if len(candidatos) == 1:
        cand_id = str(candidatos[0].get("id", "")).strip()
        for item in catalogo:
            if str(item.get("id", "")).strip() == cand_id:
                return item, resultado, texto_hospital

    return None, resultado, texto_hospital


def _resolver_variable_precisa(pregunta: str, hospital_detectado=None):
    texto_variable = chatbot_detector_engine.buscador_variable._preparar_texto(
        pregunta,
        hospital_detectado,
    )

    variable_canonica = chatbot_detector_engine.buscador_variable.buscar_variable_canonica(texto_variable)
    if variable_canonica:
        return variable_canonica, {
            "status": "ganador_claro",
            "variable": variable_canonica,
            "score": 1.0,
            "texto_usado": texto_variable,
            "regla_aplicada": "variable_canonica",
        }, texto_variable

    resultado = chatbot_detector_engine.buscador_variable.buscar(
        pregunta,
        hospital_detectado,
        aplicar_canonica=False,
    )

    if resultado.get("status") == "ganador_claro" and resultado.get("variable"):
        return resultado["variable"], resultado, texto_variable

    catalogo = _obtener_catalogo_variables()
    exactos = []
    texto_limpio = _normalizar_chatbot_m(texto_variable)
    for item in catalogo:
        desc = _normalizar_chatbot_m(item.get("desc_normalizada") or item.get("desc_original") or "")
        if not desc:
            continue
        if desc == texto_limpio or desc in texto_limpio or texto_limpio in desc:
            exactos.append(item)

    if len(exactos) == 1:
        return exactos[0], resultado, texto_variable

    candidatos = resultado.get("candidatos") or []
    if len(candidatos) == 1:
        cand_id = str(candidatos[0].get("id", "")).strip()
        for item in catalogo:
            if str(item.get("id", "")).strip() == cand_id:
                return item, resultado, texto_variable

    return None, resultado, texto_variable


def _resolver_variable_camas_censables(texto_normalizado: str):
    texto_normalizado = _normalizar_chatbot_m(texto_normalizado)
    if not texto_normalizado:
        return None

    if "cama" not in texto_normalizado:
        return None

    if not any(
        palabra in texto_normalizado
        for palabra in ("censable", "censables", "sensable", "sensables")
    ):
        return None

    for item in _obtener_catalogo_variables():
        if str(item.get("id", "")).strip() == "50100":
            return item
        if _normalizar_chatbot_m(item.get("desc_normalizada") or item.get("desc_original") or "") == "total de camas censables de la unidad":
            return item

    return None


def _extraer_cve_presupuestal(texto: str):
    texto = str(texto or "")
    coincidencia = re.search(r"\b\d{10,15}\b", texto)
    if not coincidencia:
        return None
    return coincidencia.group(0)


def _limpiar_texto_concepto_ifu(texto: str) -> str:
    texto = _normalizar_chatbot_m(texto)
    texto = re.sub(r"\b\d{10,15}\b", " ", texto)
    palabras_ignorar = {
        "que",
        "cual",
        "cuales",
        "cuanto",
        "cuantos",
        "cuanta",
        "cuantas",
        "valor",
        "valores",
        "dato",
        "datos",
        "concepto",
        "conceptos",
        "descripcion",
        "descripciones",
        "unidad",
        "unidades",
        "cvepresupuestal",
        "cve",
        "presupuestal",
        "de",
        "del",
        "la",
        "el",
        "los",
        "las",
        "en",
        "para",
        "por",
        "hay",
        "tiene",
        "tienen",
        "dame",
        "mostrar",
        "muestrame",
        "consulta",
    }
    tokens = [token for token in texto.split() if token not in palabras_ignorar]
    return " ".join(tokens).strip()


def _obtener_conceptos_ifu():
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT DISTINCT variable_nva, descripcion
            FROM [DB_Catalogos].[dbo].[Cat_IFU_Actual]
            WHERE descripcion IS NOT NULL
              AND LTRIM(RTRIM(descripcion)) <> ''
            """
        )
        filas = cursor.fetchall()

    conceptos = []
    for variable_nva, descripcion in filas:
        descripcion_texto = str(descripcion or "").strip()
        if not descripcion_texto:
            continue
        conceptos.append({
            "id": variable_nva,
            "descripcion": descripcion_texto,
            "desc_original": descripcion_texto,
            "desc_normalizada": _normalizar_chatbot_m(descripcion_texto),
        })
    return conceptos


def _obtener_modelo_semantico():
    global _semantic_model

    if SentenceTransformer is None:
        return None

    if _semantic_model is None:
        _semantic_model = SentenceTransformer(SEMANTIC_MODEL_NAME)

    return _semantic_model


def _crear_llave_conceptos(conceptos: list[dict]) -> int:
    firma = "||".join(
        f"{c.get('id')}::{c.get('desc_normalizada') or c.get('descripcion') or ''}"
        for c in conceptos
    )
    return hash(firma)


def _resolver_concepto_descripcion_ifu_semantico(
    texto_busqueda: str,
    conceptos: list[dict],
    tipo_recurso: str | None = None,
):
    if not texto_busqueda or not conceptos:
        return None

    conceptos_filtrados = [
        c for c in conceptos
        if _descripcion_cumple_tipo_recurso(c.get("desc_normalizada"), tipo_recurso)
    ]
    if not conceptos_filtrados:
        return None

    modelo = _obtener_modelo_semantico()
    if modelo is None or st_util is None:
        return None

    llave = _crear_llave_conceptos(conceptos_filtrados)
    global _semantic_embeddings_cache

    if _semantic_embeddings_cache.get("key") != llave:
        descripciones = [c["desc_normalizada"] for c in conceptos_filtrados]
        embeddings = modelo.encode(
            descripciones,
            convert_to_tensor=True,
            normalize_embeddings=True,
        )
        _semantic_embeddings_cache = {
            "key": llave,
            "embeddings": embeddings,
        }

    embeddings = _semantic_embeddings_cache.get("embeddings")
    if embeddings is None:
        return None

    consulta_embedding = modelo.encode(
        [texto_busqueda],
        convert_to_tensor=True,
        normalize_embeddings=True,
    )
    scores = st_util.cos_sim(consulta_embedding, embeddings)[0]

    if scores is None or len(scores) == 0:
        return None

    mejor_indice = int(scores.argmax().item())
    mejor_score = float(scores[mejor_indice].item())

    if mejor_score < SEMANTIC_SCORE_MIN:
        return None

    return conceptos_filtrados[mejor_indice]


def _resolver_concepto_descripcion_ifu(pregunta: str):
    texto_busqueda = _limpiar_texto_concepto_ifu(pregunta)
    if not texto_busqueda:
        return None

    if not _debe_intentar_semantica_concepto(texto_busqueda):
        return None

    conceptos = _obtener_conceptos_ifu()
    tipo_recurso = _detectar_tipo_recurso(_normalizar_chatbot_m(pregunta))
    concepto_semantico = _resolver_concepto_descripcion_ifu_semantico(
        texto_busqueda,
        conceptos,
        tipo_recurso=tipo_recurso,
    )
    if concepto_semantico:
        return concepto_semantico

    tokens_busqueda = set(texto_busqueda.split())
    if not tokens_busqueda:
        return None

    mejor_concepto = None
    mejor_score = 0.0

    for concepto in conceptos:
        descripcion_normalizada = concepto["desc_normalizada"]
        if not _descripcion_cumple_tipo_recurso(descripcion_normalizada, tipo_recurso):
            continue
        tokens_descripcion = set(descripcion_normalizada.split())
        if not tokens_descripcion:
            continue

        if texto_busqueda in descripcion_normalizada:
            score = 1.0
        else:
            interseccion = len(tokens_busqueda & tokens_descripcion)
            if interseccion == 0:
                continue
            score = interseccion / max(len(tokens_busqueda), 1)
            if tokens_busqueda.issubset(tokens_descripcion):
                score += 0.25

        if score > mejor_score:
            mejor_score = score
            mejor_concepto = concepto

    if mejor_concepto and mejor_score >= 0.6:
        return mejor_concepto

    return None


def _consultar_valor_ifu_por_cve(cve_presupuestal: str, variable_id):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT TOP 1
                CvePresupuestal,
                variable_nva,
                descripcion,
                valor
            FROM [DB_Catalogos].[dbo].[Cat_IFU_Actual]
            WHERE CvePresupuestal = %s
              AND variable_nva = %s
            """,
            [cve_presupuestal, variable_id],
        )
        columnas = [col[0] for col in cursor.description] if cursor.description else []
        fila = cursor.fetchone()

    if not fila or not columnas:
        return []

    return [dict(zip(columnas, fila))]


def _consultar_valor_concepto_por_unidad(cve_presupuestal: str, variable_detectada: dict):
    descripcion_concepto = str(
        variable_detectada.get("descripcion")
        or variable_detectada.get("desc_original")
        or ""
    ).strip()

    with connection.cursor() as cursor:
        if descripcion_concepto:
            cursor.execute(
                """
                SELECT
                    a.CvePresupuestal,
                    MAX(b.DenominacionUnidad) AS DenominacionUnidad,
                    MAX(a.descripcion) AS descripcion,
                    SUM(TRY_CONVERT(decimal(18, 4), REPLACE(a.valor, ',', ''))) AS valor
                FROM [DB_Catalogos].[dbo].[Cat_IFU_Actual] a
                LEFT JOIN [DB_Catalogos].[dbo].[CUMM_ACTUAL] b
                    ON a.CvePresupuestal = b.ClavePresupuestal
                    COLLATE Modern_Spanish_CI_AS
                WHERE a.CvePresupuestal = %s
                  AND (
                        a.variable_nva = %s
                        OR LTRIM(RTRIM(a.descripcion)) COLLATE Modern_Spanish_CI_AI =
                           LTRIM(RTRIM(%s)) COLLATE Modern_Spanish_CI_AI
                  )
                GROUP BY a.CvePresupuestal
                """,
                [cve_presupuestal, variable_detectada.get("id"), descripcion_concepto],
            )
        else:
            cursor.execute(
                """
                SELECT
                    a.CvePresupuestal,
                    MAX(b.DenominacionUnidad) AS DenominacionUnidad,
                    MAX(a.descripcion) AS descripcion,
                    SUM(TRY_CONVERT(decimal(18, 4), REPLACE(a.valor, ',', ''))) AS valor
                FROM [DB_Catalogos].[dbo].[Cat_IFU_Actual] a
                LEFT JOIN [DB_Catalogos].[dbo].[CUMM_ACTUAL] b
                    ON a.CvePresupuestal = b.ClavePresupuestal
                    COLLATE Modern_Spanish_CI_AS
                WHERE a.CvePresupuestal = %s
                  AND a.variable_nva = %s
                GROUP BY a.CvePresupuestal
                """,
                [cve_presupuestal, variable_detectada.get("id")],
            )

        columnas = [col[0] for col in cursor.description] if cursor.description else []
        fila = cursor.fetchone()

    if not fila or not columnas:
        return []

    return [dict(zip(columnas, fila))]


def _formatear_resultado_ifu(datos: list[dict]) -> str:
    if not datos:
        return "No encontré datos para esa consulta."

    if len(datos) == 1:
        fila = datos[0]
        valor = fila.get("valor")
        if valor is not None:
            if fila.get("CvePresupuestal") and fila.get("descripcion"):
                return f"La CvePresupuestal {fila['CvePresupuestal']} tiene {valor} en {fila.get('descripcion', 'el concepto solicitado')}"
            if fila.get("DenominacionUnidad"):
                return f"{fila['DenominacionUnidad']}: {fila.get('descripcion', 'resultado')} = {valor}"
            if fila.get("ambito"):
                return f"{fila['ambito']}: {fila.get('descripcion', 'resultado')} = {valor}"
            return f"Resultado: {valor}"

    lineas = []
    for fila in datos[:10]:
        partes = []
        for campo in (
            "DenominacionUnidad",
            "NombreDelegacionUMAE",
            "Region",
            "NivelAtencion",
            "ambito",
            "descripcion",
            "variable_nva",
            "valor",
            "total_unidades",
        ):
            valor = fila.get(campo)
            if valor is None:
                continue
            texto_valor = str(valor).strip()
            if texto_valor:
                partes.append(f"{campo}: {texto_valor}")
        if partes:
            lineas.append("- " + "; ".join(partes))

    return "\n".join(lineas) if lineas else f"Encontré {len(datos)} registros."


def _normalizar_numero_decimal(valor):
    if valor is None:
        return None
    try:
        texto = str(valor).strip().replace(",", "")
        if texto == "":
            return None
        return float(texto)
    except (TypeError, ValueError):
        return None


def _consultar_ranking_hospitales(variable_id: str, top_n: int = 10, ascendente: bool = False):
    orden = "ASC" if ascendente else "DESC"
    query = f"""
        SELECT TOP ({top_n})
            b.ClavePresupuestal,
            b.DenominacionUnidad,
            b.NivelAtencion,
            b.Region,
            b.NombreDelegacionUMAE,
            a.variable_nva,
            a.descripcion,
            SUM(TRY_CONVERT(decimal(18, 2), REPLACE(a.valor, ',', ''))) AS valor,
            COUNT(*) AS registros
        FROM [DB_Catalogos].[dbo].[Cat_IFU_Actual] a
        JOIN [DB_Catalogos].[dbo].[CUMM_ACTUAL] b
            ON a.CvePresupuestal = b.ClavePresupuestal
            COLLATE Modern_Spanish_CI_AS
        WHERE a.variable_nva = %s
        GROUP BY
            b.ClavePresupuestal,
            b.DenominacionUnidad,
            b.NivelAtencion,
            b.Region,
            b.NombreDelegacionUMAE,
            a.variable_nva,
            a.descripcion
        ORDER BY valor {orden}, b.DenominacionUnidad ASC
    """

    with connection.cursor() as cursor:
        cursor.execute(query, [variable_id])
        columnas = [col[0] for col in cursor.description]
        filas = cursor.fetchall()

    return [dict(zip(columnas, fila)) for fila in filas]


def _construir_filtro_cumm_por_ambito(ambito: dict):
    tipo = str((ambito or {}).get("tipo") or "").upper()
    ambito_id = str((ambito or {}).get("id") or "").strip()
    ambito_desc = str(
        (ambito or {}).get("desc_original")
        or (ambito or {}).get("descripcion")
        or (ambito or {}).get("texto_usado")
        or ""
    ).strip()
    like_desc = f"%{ambito_desc}%" if ambito_desc else None

    if tipo == "NACIONAL":
        return "1=1", []

    if tipo == "ENTIDAD":
        filtros = []
        params = []
        if like_desc:
            filtros.append("c.[RelacionDelegacion-UMAE] COLLATE Modern_Spanish_CI_AI LIKE %s")
            params.append(like_desc)
            filtros.append("c.EntidadFederativa COLLATE Modern_Spanish_CI_AI LIKE %s")
            params.append(like_desc)
        if ambito_id:
            filtros.append("c.ClaveEntidadFederativa = %s")
            params.append(ambito_id)
        if not filtros:
            return "1=0", []
        return "(" + " OR ".join(filtros) + ")", params

    if tipo == "DELEGACION":
        filtros = []
        params = []
        if like_desc:
            filtros.append("c.NombreDelegacionUMAE COLLATE Modern_Spanish_CI_AI LIKE %s")
            params.append(like_desc)
            filtros.append("c.[RelacionDelegacion-UMAE] COLLATE Modern_Spanish_CI_AI LIKE %s")
            params.append(like_desc)
        if ambito_id:
            filtros.append("c.Cve_Deleg_UMAE = %s")
            params.append(ambito_id)
        if not filtros:
            return "1=0", []
        return "(" + " OR ".join(filtros) + ")", params

    if tipo == "REGION":
        filtros = []
        params = []
        if like_desc:
            filtros.append("c.Region COLLATE Modern_Spanish_CI_AI LIKE %s")
            params.append(like_desc)
        if ambito_id:
            filtros.append("c.Region = %s")
            params.append(ambito_id)
        if not filtros:
            return "1=0", []
        return "(" + " OR ".join(filtros) + ")", params

    if tipo == "NIVEL_ATENCION":
        filtros = []
        params = []
        if like_desc:
            filtros.append("c.NivelAtencion COLLATE Modern_Spanish_CI_AI LIKE %s")
            params.append(like_desc)
        if ambito_id:
            filtros.append("c.NivelAtencion = %s")
            params.append(ambito_id)
        if not filtros:
            return "1=0", []
        return "(" + " OR ".join(filtros) + ")", params

    return "1=0", []


def _contar_hospitales_por_ambito_y_concepto(ambito: dict, variable_detectada: dict, top_n: int = 5):
    where_ambito, params_ambito = _construir_filtro_cumm_por_ambito(ambito)
    variable_id = variable_detectada.get("id")
    descripcion = str(
        variable_detectada.get("descripcion")
        or variable_detectada.get("desc_original")
        or ""
    ).strip()
    descripcion_like = f"%{descripcion.replace('.', '')}%" if descripcion else None

    filtros_concepto = ["a.variable_nva = %s"]
    params_concepto = [variable_id]
    if descripcion_like:
        filtros_concepto.append("a.descripcion COLLATE Modern_Spanish_CI_AI LIKE %s")
        params_concepto.append(descripcion_like)
    where_concepto = "(" + " OR ".join(filtros_concepto) + ")"

    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT COUNT(DISTINCT c.ClavePresupuestal)
            FROM [DB_Catalogos].[dbo].[CUMM_ACTUAL] c
            JOIN [DB_Catalogos].[dbo].[Cat_IFU_Actual] a
                ON a.CvePresupuestal = c.ClavePresupuestal
                COLLATE Modern_Spanish_CI_AS
            WHERE {where_ambito}
              AND {where_concepto}
              AND TRY_CONVERT(decimal(18, 4), REPLACE(a.valor, ',', '')) > 0
            """,
            [*params_ambito, *params_concepto],
        )
        total = cursor.fetchone()[0] or 0

        cursor.execute(
            f"""
            SELECT TOP ({top_n})
                c.ClavePresupuestal AS CvePresupuestal,
                MAX(c.DenominacionUnidad) AS DenominacionUnidad,
                SUM(TRY_CONVERT(decimal(18, 4), REPLACE(a.valor, ',', ''))) AS valor_total
            FROM [DB_Catalogos].[dbo].[CUMM_ACTUAL] c
            JOIN [DB_Catalogos].[dbo].[Cat_IFU_Actual] a
                ON a.CvePresupuestal = c.ClavePresupuestal
                COLLATE Modern_Spanish_CI_AS
            WHERE {where_ambito}
              AND {where_concepto}
              AND TRY_CONVERT(decimal(18, 4), REPLACE(a.valor, ',', '')) > 0
            GROUP BY c.ClavePresupuestal
            ORDER BY valor_total DESC, c.ClavePresupuestal ASC
            """,
            [*params_ambito, *params_concepto],
        )
        columnas = [col[0] for col in cursor.description] if cursor.description else []
        filas = cursor.fetchall()

    top = [dict(zip(columnas, fila)) for fila in filas] if columnas else []
    return total, top


def _contar_hospitales_por_ambito_general(ambito: dict, top_n: int = 5):
    where_ambito, params_ambito = _construir_filtro_cumm_por_ambito(ambito)

    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT COUNT(DISTINCT c.ClavePresupuestal)
            FROM [DB_Catalogos].[dbo].[CUMM_ACTUAL] c
            WHERE {where_ambito}
              AND EXISTS (
                    SELECT 1
                    FROM [DB_Catalogos].[dbo].[Cat_IFU_Actual] a
                    WHERE a.CvePresupuestal = c.ClavePresupuestal
                        COLLATE Modern_Spanish_CI_AS
              )
            """,
            params_ambito,
        )
        total = cursor.fetchone()[0] or 0

        cursor.execute(
            f"""
            SELECT TOP ({top_n})
                c.ClavePresupuestal AS CvePresupuestal,
                MAX(c.DenominacionUnidad) AS DenominacionUnidad
            FROM [DB_Catalogos].[dbo].[CUMM_ACTUAL] c
            WHERE {where_ambito}
              AND EXISTS (
                    SELECT 1
                    FROM [DB_Catalogos].[dbo].[Cat_IFU_Actual] a
                    WHERE a.CvePresupuestal = c.ClavePresupuestal
                        COLLATE Modern_Spanish_CI_AS
              )
            GROUP BY c.ClavePresupuestal
            ORDER BY DenominacionUnidad ASC, c.ClavePresupuestal ASC
            """,
            params_ambito,
        )
        columnas = [col[0] for col in cursor.description] if cursor.description else []
        filas = cursor.fetchall()

    top = [dict(zip(columnas, fila)) for fila in filas] if columnas else []
    return total, top


# Mario: Funci+�n para resolver archivos de ficha nacional din+�micamente por prefijo.
def _resolver_archivos_ficha_nacional():
    carpeta_montada = Path('/app/frontend-public/nacional')
    raiz_repo = Path(__file__).resolve().parents[2]
    carpeta_local = raiz_repo / 'frontend-angular' / 'app' / 'public' / 'nacional'
    carpeta_nacional = carpeta_montada if carpeta_montada.exists() else carpeta_local

    if not carpeta_nacional.exists() or not carpeta_nacional.is_dir():
        raise FileNotFoundError(f'No existe la carpeta nacional: {carpeta_nacional}')

    archivos = [archivo for archivo in carpeta_nacional.iterdir() if archivo.is_file()]

    def seleccionar(prefix: str, extensiones: tuple[str, ...]) -> str | None:
        candidatos = [
            archivo for archivo in archivos
            if archivo.name.lower().startswith(prefix.lower())
            and archivo.suffix.lower() in extensiones
        ]
        if not candidatos:
            return None
        candidatos.sort(key=lambda archivo: archivo.stat().st_mtime, reverse=True)
        return candidatos[0].name

    return {
        'pdf': seleccionar('ficha_nacional', ('.pdf',)),
        'pptx': seleccionar('ficha_nacional', ('.pptx', '.ppt')),
    }


# Mario: Funci+�n para resolver archivos de fichas estatales din+�micamente agrupados por prefijo (FE_XX_CLAVE).
def _resolver_archivos_fichas_estatales():
    carpeta_montada = Path('/app/frontend-public/fichas')
    raiz_repo = Path(__file__).resolve().parents[2]
    carpeta_local = raiz_repo / 'frontend-angular' / 'app' / 'public' / 'fichas'
    carpeta_estatales = carpeta_montada if carpeta_montada.exists() else carpeta_local

    if not carpeta_estatales.exists() or not carpeta_estatales.is_dir():
        raise FileNotFoundError(f'No existe la carpeta de fichas estatales: {carpeta_estatales}')

    archivos = [archivo for archivo in carpeta_estatales.iterdir() if archivo.is_file()]
    por_prefijo = {}

    for archivo in archivos:
        nombre = archivo.name
        partes = nombre.split('_')
        if len(partes) < 4:
            continue

        prefijo = '_'.join(partes[:3]).upper()
        if not prefijo.startswith('FE_'):
            continue

        extension = archivo.suffix.lower()
        if extension not in ('.pdf', '.pptx', '.ppt'):
            continue

        registro = por_prefijo.setdefault(
            prefijo,
            {
                'prefix': prefijo,
                'pdf': None,
                'pptx': None,
                '_pdf_mtime': -1,
                '_pptx_mtime': -1,
            },
        )

        mtime = archivo.stat().st_mtime

        if extension == '.pdf' and mtime > registro['_pdf_mtime']:
            registro['pdf'] = nombre
            registro['_pdf_mtime'] = mtime

        if extension in ('.pptx', '.ppt') and mtime > registro['_pptx_mtime']:
            registro['pptx'] = nombre
            registro['_pptx_mtime'] = mtime

    items = []
    for item in por_prefijo.values():
        items.append(
            {
                'prefix': item['prefix'],
                'pdf': item['pdf'],
                'pptx': item['pptx'],
            }
        )

    items.sort(key=lambda x: x['prefix'])
    return items


# ---- Inicia Mario Solicitudes especiales----
def _guardar_oficio_pdf(oficio_nombre_archivo: str, oficio_pdf_base64: str) -> str | None:
    if not oficio_nombre_archivo or not oficio_pdf_base64:
        return None

    nombre_limpio = Path(oficio_nombre_archivo).name
    if not nombre_limpio.lower().endswith('.pdf'):
        raise ValueError('El oficio debe ser un archivo PDF.')

    carpeta_montada = Path('/app/frontend-public/oficios')
    raiz_repo = Path(__file__).resolve().parents[2]
    carpeta_local = raiz_repo / 'frontend-angular' / 'app' / 'public' / 'oficios'
    carpeta_oficios = carpeta_montada if carpeta_montada.exists() else carpeta_local
    carpeta_oficios.mkdir(parents=True, exist_ok=True)

    base_sin_ext = Path(nombre_limpio).stem
    base_sin_ext = re.sub(r'[^A-Za-z0-9_-]+', '_', base_sin_ext).strip('_') or 'oficio'
    marca_tiempo = timezone.now().strftime('%Y%m%d_%H%M%S_%f')
    nombre_final = f"{base_sin_ext}_{marca_tiempo}.pdf"
    destino = carpeta_oficios / nombre_final

    try:
        contenido = base64.b64decode(oficio_pdf_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError('El contenido del oficio no tiene un formato base64 valido.') from exc

    if not contenido.startswith(b'%PDF'):
        raise ValueError('El archivo adjunto no corresponde a un PDF valido.')

    destino.write_bytes(contenido)
    return f"/public/oficios/{nombre_final}"


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def ficha_nacional_archivos(request):
    try:
        archivos = _resolver_archivos_ficha_nacional()
        return Response({"ok": True, **archivos})
    except Exception as exc:
        return Response(
            {"ok": False, "message": "No se pudieron resolver los archivos de ficha nacional.", "detail": str(exc)},
            status=503,
        )


# Mario: Endpoint para consultar din+�micamente los archivos de fichas estatales disponibles.
@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def ficha_estatales_archivos(request):
    try:
        items = _resolver_archivos_fichas_estatales()
        return Response({"ok": True, "items": items})
    except Exception as exc:
        return Response(
            {
                "ok": False,
                "message": "No se pudieron resolver los archivos de fichas estatales.",
                "detail": str(exc),
            },
            status=503,
        )

def autenticar_ad(usuario, password):
    url = "http://serviciosdigitalesinterno-stage.imss.gob.mx/serviciosDigitales-rest/v1/externos/directorioActivo/usuario/autentica"

    payload = {
        "claveUsusaio": usuario,
        "claveUsuario": usuario,
        "dominio": "metro",
        "password": password
    }

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    # print("Payload enviado:", payload, flush=True)

    try:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=50
        )

        # print("Status:", response.status_code, flush=True)
        # print("Respuesta:", response.text, flush=True)

        response.raise_for_status()

        # Normaliza la respuesta del servicio de AD para siempre devolver
        # un objeto de usuario utilizable por el frontend.
        try:
            data = response.json()
        except ValueError:
            data = {}

        if isinstance(data, dict) and isinstance(data.get("data"), dict):
            usuario_ad = data.get("data")
        elif isinstance(data, dict) and isinstance(data.get("usuario"), dict):
            usuario_ad = data.get("usuario")
        elif isinstance(data, dict):
            usuario_ad = data
        else:
            usuario_ad = {}

        # Fallback mínimo para que el formulario de solicitud no quede vacío.
        usuario_ad.setdefault("nomCuenta", usuario)
        if "@" in usuario:
            usuario_ad.setdefault("correo", usuario)

        return usuario_ad, None

    except requests.exceptions.RequestException as e:
        status_code = getattr(getattr(e, "response", None), "status_code", None)
        detail = f"AD auth failed: {type(e).__name__}"
        if status_code:
            detail += f" (status={status_code})"
        return False, detail

    

@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def autenticar_usuario(request):

    payload = request.data if isinstance(request.data, dict) else {}

    usuario = str(payload.get("usuario", "")).strip()
    contrasena = str(payload.get("contrasena", "")).strip()

    

    if not usuario or not contrasena:
        return Response(
            {"ok": False, "message": "Captura usuario y contrase+�a."},
            status=400,
        )

    usuario_ad, detalle_ad = autenticar_ad(usuario, contrasena)
    if not usuario_ad:
        status_code = 503 if detalle_ad and "Connection" in detalle_ad else 401
        return Response(
            {
                "ok": False,
                "message": "No fue posible autenticar al usuario.",
                "detail": detalle_ad or "Usuario y contrase+�a incorrectos.",
            },
            status=status_code,
        )
    # print("Datos regresado:", es_valido, flush=True)
    # correo = es_valido.get('correo')
    # nombre = es_valido.get('nombre')
    # primerApellido = es_valido.get('primerApellido')
    # segundoApellido = es_valido.get('segundoApellido')

    query = """
        SELECT TOP 1 pk_idUsuario, fld_cambio_pwd, fld_statususuario
        FROM [dbo].[cat_usuarios]
        WHERE UPPER(LTRIM(RTRIM(fld_claveUsuario))) = UPPER(LTRIM(RTRIM(%s)))
          
    """

    with connection.cursor() as cursor:
        cursor.execute(query, [usuario])
        row = cursor.fetchone()

    acceso_restringido_solicitud = row is None

    # fld_statususuario = 2 otorga acceso a solicitudes pendientes (admin)
    # fld_statususuario = 3 otorga acceso al chatbot
    es_admin_solicitudes = False
    es_chatbot_usuario = False
    if row and len(row) >= 3:
        try:
            status = int(row[2])
            es_admin_solicitudes = status == 2
            es_chatbot_usuario = status == 3
        except (TypeError, ValueError):
            pass

    #  GENERAR TOKEN
    id_usuario = row[0] if row else None

    user, _ = User.objects.get_or_create(username=usuario)
    refresh = RefreshToken.for_user(user)
    if id_usuario is not None:
        refresh["id_usuario"] = id_usuario  #

    access_token = str(refresh.access_token)
    # 
 

    valor_cambio_pwd = row[1] if row and len(row) >= 2 else None
    valor_cambio_pwd_txt = str(valor_cambio_pwd).strip().upper() if valor_cambio_pwd is not None else ""
    requiere_cambio_pwd = valor_cambio_pwd_txt in {"1", "S", "SI", "TRUE", "T", "Y", "YES"}

    mensaje = "Autenticacion correcta."
    if acceso_restringido_solicitud:
        mensaje = "Autenticacion correcta. Acceso limitado a Solicitud de Acceso a Base de Datos."

    return Response(
        {
            "ok": True,
            "message": mensaje,
            "usuario": usuario_ad,
            "token": access_token,   # 
            "requiere_cambio_pwd": requiere_cambio_pwd,
            "acceso_restringido_solicitud": acceso_restringido_solicitud,
            "es_admin_solicitudes": es_admin_solicitudes,
            "es_chatbot_usuario": es_chatbot_usuario,
        }
    )


@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def areas(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id_area, nombre, descripcion
            FROM cat_area
            WHERE activo = 1
            ORDER BY nombre
        """)
        rows = cursor.fetchall()

    data = [
        {
            "id_area": r[0],
            "nombre": r[1],
            "descripcion": r[2],
        }
        for r in rows
    ]

    return Response(data)

@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def temas(request):
    id_area = request.GET.get("id_area")

    if not id_area:
        return Response([], status=200)

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id_tema, id_area, nombre, descripcion, tabla_destino, modo_carga, sp_carga
            FROM cat_tema
            WHERE activo = 1
              AND id_area = %s
            ORDER BY nombre
        """, [id_area])

        rows = cursor.fetchall()

    data = [
        {
            "id_tema": r[0],
            "id_area": r[1],
            "nombre": r[2],
            "descripcion": r[3],
            "tabla_destino": r[4],
            "modo_carga": r[5],
            "sp_carga": r[6],                 
        }
        for r in rows
    ]

    return Response(data)

@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def diccionario(request):
    id_tema = request.GET.get("id_tema")

    if not id_tema:
        return Response([], status=200)

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT
                id_campo,
                columna_excel,
                columna_bd,
                tipo_dato,
                longitud,
                obligatorio,
                orden
            FROM cat_diccionario_campo
            WHERE activo = 1
              AND id_tema = %s
            ORDER BY orden
        """, [id_tema])

        rows = cursor.fetchall()

    data = [
        {
            "id_campo": r[0],
            "columna_excel": r[1],
            "columna_bd": r[2],
            "tipo_dato": r[3],
            "longitud": r[4],
            "obligatorio": bool(r[5]),
            "orden": r[6],
        }
        for r in rows
    ]

    return Response(data)

    
# Mario: consulta de entidades.
@api_view(["GET"])
def entidades(request):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select distinct cve_edo, desc_edo_NomPropio
            from [dbo].[cat_entidad]
            order by desc_edo_NomPropio
            """
        )
        rows = cursor.fetchall()

    data = [{"cve_edo": r[0], "nombre": r[1]} for r in rows]
    return Response(data)
    # Mario: Termina consulta de entidades.


#Mario: Inicio endpoint guardar/consultar bitacora de revision.
@api_view(["GET", "POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def guardar_bitacora_revision(request):
    #Mario: Inicio consulta de bitacora por presentacion y objeto base.
    if request.method == "GET":
        id_user = str(request.query_params.get("id_user", "")).strip()
        id_presentacion = str(request.query_params.get("id_presentacion", "")).strip()
        id_objeto_base = str(request.query_params.get("id_objeto_base", "")).strip()

        if not id_presentacion or not id_objeto_base:
            return Response(
                {
                    "ok": False,
                    "message": "Par+�metros faltantes",
                    "faltantes": [
                        key
                        for key, value in {
                            "id_presentacion": id_presentacion,
                            "id_objeto_base": id_objeto_base,
                        }.items()
                        if not value
                    ],
                },
                status=400,
            )

        like_pattern = f"{id_objeto_base}_%"

        with connection.cursor() as cursor:
            if id_user:
                cursor.execute(
                    """
                    SELECT [ID_objeto], [Comentario], [Estatus]
                    FROM [dbo].[sistema_bitacora]
                    WHERE [ID_presentacion] = %s
                      AND [ID_objeto] LIKE %s
                      AND [Id_user] = %s
                    ORDER BY [ID_objeto]
                    """,
                    [id_presentacion, like_pattern, id_user],
                )
            else:
                cursor.execute(
                    """
                    SELECT [ID_objeto], [Comentario], [Estatus]
                    FROM [dbo].[sistema_bitacora]
                    WHERE [ID_presentacion] = %s
                      AND [ID_objeto] LIKE %s
                    ORDER BY [ID_objeto]
                    """,
                    [id_presentacion, like_pattern],
                )
            rows = cursor.fetchall()

        por_pagina = {}
        for row in rows:
            id_objeto = str(row[0] or "").strip()
            comentario = str(row[1] or "").strip()
            estatus = str(row[2] or "").strip()

            if "_" not in id_objeto:
                continue

            pagina_txt = id_objeto.rsplit("_", 1)[1]
            if not pagina_txt.isdigit():
                continue

            pagina = int(pagina_txt)
            por_pagina[pagina] = {
                "pagina": pagina,
                "id_objeto": id_objeto,
                "comentario": comentario,
                "estatus": estatus,
            }

        data = [por_pagina[p] for p in sorted(por_pagina.keys())]
        return Response({"ok": True, "items": data})
    #Mario: Fin consulta de bitacora por presentacion y objeto base.

    #Mario: Inicio guardado de bitacora por pagina.
    payload = request.data if isinstance(request.data, dict) else {}

    id_registro = str(payload.get("id", "")).strip()
    id_user = str(payload.get("id_user", "")).strip()
    id_presentacion = str(payload.get("id_presentacion", "")).strip()
    id_objeto = str(payload.get("id_objeto", "")).strip()
    comentario = str(payload.get("comentario", "")).strip()
    estatus = str(payload.get("estatus", "")).strip()

    faltantes = []
    if not id_registro:
        faltantes.append("id")
    if not id_user:
        faltantes.append("id_user")
    if not id_presentacion:
        faltantes.append("id_presentacion")
    if not id_objeto:
        faltantes.append("id_objeto")
    if not estatus:
        faltantes.append("estatus")

    if faltantes:
        return Response(
            {"ok": False, "message": "Campos faltantes", "faltantes": faltantes},
            status=400,
        )

    if not id_registro:
        id_registro = timezone.now().strftime("%Y%m%d%H%M%S%f")[-12:]

    fecha_actual = timezone.localtime(timezone.now(), ZoneInfo("America/Mexico_City")).replace(tzinfo=None)

    accion = "guardada"
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT TOP 1 1
            FROM [dbo].[sistema_bitacora]
            WHERE [Id_user] = %s
              AND [ID_presentacion] = %s
              AND [ID_objeto] = %s
            """,
            [id_user, id_presentacion, id_objeto],
        )
        existe = cursor.fetchone() is not None

        if existe:
            cursor.execute(
                """
                UPDATE [dbo].[sistema_bitacora]
                SET [Comentario] = %s,
                    [Estatus] = %s,
                    [fecha] = %s
                WHERE [Id_user] = %s
                  AND [ID_presentacion] = %s
                  AND [ID_objeto] = %s
                """,
                [comentario, estatus, fecha_actual, id_user, id_presentacion, id_objeto],
            )
            accion = "actualizada"
        else:
            cursor.execute(
                """
                INSERT INTO [dbo].[sistema_bitacora]
                ([ID], [Id_user], [ID_presentacion], [ID_objeto], [Comentario], [Estatus], [fecha])
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                [id_registro, id_user, id_presentacion, id_objeto, comentario, estatus, fecha_actual],
            )

    return Response({"ok": True, "message": f"Revisi+�n {accion}"})
    #Mario: Fin guardado de bitacora por pagina.
#Mario: Fin endpoint guardar/consultar bitacora de revision.


#Mario: Inicio endpoint reporte excel de revision.
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def generar_reporte_excel_revision(request):
    payload = request.data if isinstance(request.data, dict) else {}

    id_user = str(payload.get("id_user", "")).strip()
    id_presentacion = str(payload.get("id_presentacion", "")).strip()
    id_objeto_base = str(payload.get("id_objeto_base", "")).strip()
    revisiones = payload.get("revisiones", [])

    faltantes = []
    if not id_user:
        faltantes.append("id_user")
    if not id_presentacion:
        faltantes.append("id_presentacion")
    if not id_objeto_base:
        faltantes.append("id_objeto_base")
    if not isinstance(revisiones, list) or len(revisiones) == 0:
        faltantes.append("revisiones")

    if faltantes:
        return Response(
            {"ok": False, "message": "Campos faltantes", "faltantes": faltantes},
            status=400,
        )

    filas_xml = []
    for index, item in enumerate(revisiones, start=1):
        revision = item if isinstance(item, dict) else {}
        comentario = escape(str(revision.get("comentario", "") or ""))
        estatus_raw = str(revision.get("estatus", "") or "").strip().lower()
        resultado = "Aprobada" if estatus_raw == "correcta" else "Rechazada"
        id_objeto = escape(f"{id_objeto_base}_{index}")

        filas_xml.append(
            """
            <Row>
              <Cell><Data ss:Type=\"String\">{lamina}</Data></Cell>
              <Cell><Data ss:Type=\"String\">{id_user}</Data></Cell>
              <Cell><Data ss:Type=\"String\">{presentacion}</Data></Cell>
              <Cell><Data ss:Type=\"String\">{id_objeto}</Data></Cell>
              <Cell><Data ss:Type=\"String\">{comentario}</Data></Cell>
              <Cell><Data ss:Type=\"String\">{resultado}</Data></Cell>
            </Row>
            """.format(
                lamina=index,
                id_user=escape(id_user),
                presentacion=escape(id_presentacion),
                id_objeto=id_objeto,
                comentario=comentario,
                resultado=escape(resultado),
            )
        )

    contenido = f"""<?xml version=\"1.0\"?>
<Workbook xmlns=\"urn:schemas-microsoft-com:office:spreadsheet\"
 xmlns:o=\"urn:schemas-microsoft-com:office:office\"
 xmlns:x=\"urn:schemas-microsoft-com:office:excel\"
 xmlns:ss=\"urn:schemas-microsoft-com:office:spreadsheet\">
  <Worksheet ss:Name=\"ReporteRevision\">
    <Table>
      <Row>
        <Cell><Data ss:Type=\"String\">L+�mina</Data></Cell>
        <Cell><Data ss:Type=\"String\">ID usuario</Data></Cell>
        <Cell><Data ss:Type=\"String\">Presentaci+�n</Data></Cell>
        <Cell><Data ss:Type=\"String\">ID objeto</Data></Cell>
        <Cell><Data ss:Type=\"String\">Comentario</Data></Cell>
        <Cell><Data ss:Type=\"String\">Resultado</Data></Cell>
      </Row>
      {''.join(filas_xml)}
    </Table>
  </Worksheet>
</Workbook>"""

    response = HttpResponse(contenido, content_type="application/vnd.ms-excel; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="reporte_revision_{id_objeto_base}.xls"'
    return response
#Mario: Fin endpoint reporte excel de revision.




@api_view(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])

def subir_excel(request):
    
    archivo = request.FILES.get("file")
    id_tema = request.POST.get("id_tema")
    id_area = request.POST.get("id_area")
    hoja = request.POST.get("hoja")


    if not archivo:
        
        return Response({"error": "No se envio el archivo"}, status=400)

    try:
        # print(" Nombre:", archivo.name, flush=True)
        

        # df = pd.read_excel(archivo, engine="openpyxl")
        df = pd.read_excel(archivo, sheet_name=hoja, engine="openpyxl",dtype=str, keep_default_na=False)
 
        df.columns = df.columns.str.strip()
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT columna_excel, columna_bd, obligatorio, tipo_dato, longitud
                FROM cat_diccionario_campo
                WHERE id_tema = %s AND activo = 1
            """, [id_tema])            

            dic = cursor.fetchall()
            columnas_esperadas = [d[0] for d in dic]  # columna_excel
        #
        df.columns = (
            df.columns
            .astype(str)
            .str.strip()
            .str.replace(r"\s+", " ", regex=True)
        )

        df = df.loc[:, ~df.columns.str.contains("^Unnamed", case=False)]
        df = df.loc[:, df.columns != ""]
        df = df.loc[:, df.columns.notna()]        
        #
        columnas_excel = list(df.columns)
        faltantes_estructura  = [c for c in columnas_esperadas if c not in columnas_excel]
        extras = [c for c in columnas_excel if c not in columnas_esperadas]
        
        # usuario = request.auth.get("id_usuario")
        # usuario = request.auth["id_usuario"]
        # print(usuario, flush=True)
        if request.auth:
            usuario = request.auth["id_usuario"]
            
        else:
            # print("Error", flush=True)
            return Response({"error": "No autenticado"}, status=401)
        fecha_captura = timezone.now()
        if faltantes_estructura  or extras:
            
            return Response({
                "error": "Estructura de columnas invalida",
                "faltantes": faltantes_estructura ,
                "extras": extras,
                "columnas_esperadas": columnas_esperadas
            }, status=400)     
               
        dic_tipos = {
            d[1]: {
                "excel": d[0],
                "obligatorio": d[2],
                "tipo": d[3],
                "longitud": d[4]
            }
            for d in dic
        }    
        map_bd = {d[0]: d[1] for d in dic}




        df = df.rename(columns=map_bd)
        filas = df.to_dict(orient="records")
        #
        filas_limpias = []

        for fila in filas:
            # Detectar si TODA la fila esta vacia
            if all(
                (v is None) or (str(v).strip() == "") or (pd.isna(v))
                for v in fila.values()
            ):
                # print("Fila vacia detectada, se detiene la carga", flush=True)
                break

            filas_limpias.append(fila)

        filas = filas_limpias        
        #
        errores = []

        for i, fila in enumerate(filas, start=1):

            for col_bd, value in fila.items():

                config = dic_tipos.get(col_bd)

                if not config:
                    continue

                # ---------------------------------------------------
                # 1. Normalizar vacíos y espacios
                # ---------------------------------------------------
                if value is None or pd.isna(value):
                    value = None

                elif isinstance(value, str):
                    value = value.strip()

                    if value == "":
                        value = None

                fila[col_bd] = value

                # ---------------------------------------------------
                # 2. Campo obligatorio
                # ---------------------------------------------------
                if config["obligatorio"] and value is None:
                    errores.append({
                        "fila": i,
                        "columna": config["excel"],
                        "error": "Campo obligatorio vacío"
                    })
                    continue

                # Si es opcional y está vacío, no hay nada más que validar
                if value is None:
                    continue

                tipo = str(config["tipo"]).strip().lower()

                # ---------------------------------------------------
                # 3. Tipo entero
                # ---------------------------------------------------
                if tipo == "int":
                    try:
                        numero = float(value)

                        if not numero.is_integer():
                            raise ValueError("Contiene decimales")

                        fila[col_bd] = int(numero)

                    except (ValueError, TypeError):
                        errores.append({
                            "fila": i,
                            "columna": config["excel"],
                            "error": f"Debe ser un número entero: {value}"
                        })
                        continue

                # ---------------------------------------------------
                # 4. Tipo decimal
                # ---------------------------------------------------
                elif tipo == "decimal":
                    try:
                        fila[col_bd] = float(value)

                    except (ValueError, TypeError):
                        errores.append({
                            "fila": i,
                            "columna": config["excel"],
                            "error": f"Debe ser numérico: {value}"
                        })
                        continue

                # ---------------------------------------------------
                # 5. Tipo fecha
                # ---------------------------------------------------
                elif tipo in ("date", "datetime"):
                    try:
                        fecha = pd.to_datetime(
                            value,
                            dayfirst=True,
                            errors="raise"
                        )

                        if tipo == "date":
                            fila[col_bd] = fecha.date()
                        else:
                            fila[col_bd] = fecha.to_pydatetime()

                    except (ValueError, TypeError):
                        errores.append({
                            "fila": i,
                            "columna": config["excel"],
                            "error": f"Fecha inválida: {value}"
                        })
                        continue

                # ---------------------------------------------------
                # 6. Validar longitud
                # ---------------------------------------------------
                if (
                    config.get("longitud")
                    and tipo not in ("int", "decimal", "date", "datetime")
                    and len(str(fila[col_bd])) > config["longitud"]
                ):
                    errores.append({
                        "fila": i,
                        "columna": config["excel"],
                        "error": (
                            f"Excede longitud {config['longitud']}. "
                            f"Valor recibido: {fila[col_bd]}"
                        )
                    })
        #
        if errores:
            # print(f"Errores encontrados: {errores[:20]}", flush=True)   
            return Response({
                "error": "Errores de validacion: " + str(errores[:5]),
                "detalle": errores[:20],
                "total_errores": len(errores)
            }, status=400)        
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT tabla_destino, modo_carga, sp_carga
                FROM cat_tema
                WHERE id_tema = %s
            """, [id_tema])

            tabla, modo_carga, sp_carga = cursor.fetchone()
            tabla = f"[{tabla}]"
            # filas = df.to_dict(orient="records")


        # Validar antes de abrir la transacción.
        # Es importante hacerlo antes del DELETE en modo REPLACE.
        if not filas:
            return Response(
                {"error": "El archivo no contiene registros"},
                status=400
            )

        TAMANIO_LOTE = 1000
        total_registros = len(filas)

        # Conservamos el orden original de las columnas.
        columnas_datos = list(filas[0].keys())
        columnas_insert = columnas_datos + [
            "fecha_captura",
            "pk_idUsuario"
        ]

        cols = ", ".join(f"[{columna}]" for columna in columnas_insert)
        vals_sql = ", ".join(["%s"] * len(columnas_insert))

        sql_insert = f"""
            INSERT INTO {tabla} ({cols})
            VALUES ({vals_sql})
        """

        print(
            f"[subir_excel] Iniciando carga de {total_registros} registros "
            f"en lotes de {TAMANIO_LOTE}",
            flush=True
        )

        with transaction.atomic():
            with connection.cursor() as cursor:

                if modo_carga == "REPLACE":
                    print(
                        f"[subir_excel] Eliminando registros de {tabla}",
                        flush=True
                    )
                    cursor.execute(f"DELETE FROM {tabla}")

                # Activar fast_executemany cuando el driver lo permita.
                raw_cursor = getattr(cursor, "cursor", None)

                if raw_cursor is not None and hasattr(
                    raw_cursor,
                    "fast_executemany"
                ):
                    raw_cursor.fast_executemany = True
                    print(
                        "[subir_excel] fast_executemany activado",
                        flush=True
                    )

                for inicio in range(0, total_registros, TAMANIO_LOTE):
                    fin = min(inicio + TAMANIO_LOTE, total_registros)
                    lote_filas = filas[inicio:fin]

                    # Crear solamente los datos del lote actual.
                    data_lote = [
                        [
                            fila.get(columna)
                            for columna in columnas_datos
                        ] + [
                            fecha_captura,
                            usuario
                        ]
                        for fila in lote_filas
                    ]

                    try:
                        cursor.executemany(sql_insert, data_lote)
                    except Exception as error:
                        print(
                            f"[subir_excel] Error en lote "
                            f"{inicio + 1}-{fin}: {error}",
                            flush=True
                        )
                        raise

                    print(
                        f"[subir_excel] Insertados {fin}/"
                        f"{total_registros}",
                        flush=True
                    )

                sql_log = """
                    INSERT INTO log_carga
                    (
                        id_area,
                        id_tema,
                        pk_idUsuario,
                        nombre_archivo,
                        fecha_carga,
                        registros_total
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                """

                valores_log = (
                    id_area,
                    id_tema,
                    usuario,
                    archivo.name,
                    fecha_captura,
                    total_registros
                )

                cursor.execute(sql_log, valores_log)

            if sp_carga and sp_carga.strip():
                print(
                    f"[subir_excel] Ejecutando procedimiento {sp_carga}",
                    flush=True
                )

                with connection.cursor() as cursor:
                    cursor.execute(f"EXEC {sp_carga}")

        print(
            f"[subir_excel] Carga terminada: "
            f"{total_registros} registros",
            flush=True
        )

        return Response({
            "columnas": list(df.columns),
            "filas": filas[:10],
            "total_registros": total_registros
        })
    except Exception as e:
        import traceback
        print(str(e), flush=True)
        traceback.print_exc()

        return Response({"error": str(e)}, status=500)
        
@api_view(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def obtener_hojas_excel(request):
    archivo = request.FILES.get("file")

    if not archivo:
        return Response({"error": "No se envio archivo"}, status=400)

    try:
        xls = pd.ExcelFile(archivo, engine="openpyxl")
        hojas = xls.sheet_names

        return Response({
            "hojas": hojas
        })

    except Exception as e:
        print(str(e), flush=True)   
        return Response({"error": str(e)}, status=500)


@api_view(["GET", "POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def guardar_solicitud_acceso_bd(request):
    """Registra una solicitud de acceso o consulta conteo de pendientes en dbo.solicitudes_acceso_bd."""
    if request.method == "GET":
        estatus = (request.query_params.get("estatus") or "pendiente").strip()
        detalle = (request.query_params.get("detalle") or "").strip().lower()
        correo = (request.query_params.get("correo") or "").strip().lower()
        nom_cuenta = (request.query_params.get("nom_cuenta") or "").strip().lower()

        try:
            with connection.cursor() as cursor:
                if detalle == "mis-solicitudes":
                    filtros = []
                    params = []

                    if correo:
                        filtros.append("LOWER(LTRIM(RTRIM(correo))) = %s")
                        params.append(correo)
                    if nom_cuenta:
                        filtros.append("LOWER(LTRIM(RTRIM(correo))) = %s")
                        params.append(nom_cuenta)

                    if not filtros:
                        return JsonResponse(
                            {"ok": False, "mensaje": "Debes enviar correo o nom_cuenta para consultar solicitudes."},
                            status=400,
                        )

                    where_filtro = " OR ".join(filtros)
                    cursor.execute(
                        f"""
                        SELECT *
                        FROM dbo.solicitudes_acceso_bd
                        WHERE ({where_filtro})
                        ORDER BY id_solicitud DESC
                        """,
                        params,
                    )
                    columns = [col[0] for col in cursor.description] if cursor.description else []
                    rows = cursor.fetchall()
                    items = [dict(zip(columns, row)) for row in rows]
                    return JsonResponse({"ok": True, "items": items, "total": len(items)})

                if detalle == "tabla":
                    cursor.execute(
                        """
                        SELECT *
                        FROM dbo.solicitudes_acceso_bd
                        WHERE estatus = %s
                        """,
                        [estatus],
                    )
                    columns = [col[0] for col in cursor.description] if cursor.description else []
                    rows = cursor.fetchall()
                    items = [dict(zip(columns, row)) for row in rows]
                    return JsonResponse({"ok": True, "estatus": estatus, "items": items, "total": len(items)})

                cursor.execute(
                    """
                    SELECT COUNT(1)
                    FROM dbo.solicitudes_acceso_bd
                    WHERE estatus = %s
                    """,
                    [estatus],
                )
                row = cursor.fetchone()

            total = int(row[0] if row and row[0] is not None else 0)
            return JsonResponse({"ok": True, "estatus": estatus, "total": total})
        except Exception as e:
            return JsonResponse(
                {"ok": False, "mensaje": f"Error al consultar solicitudes pendientes: {str(e)}"},
                status=500,
            )

    data = request.data
    accion = (data.get("accion") or "").strip().lower()

    if accion == "aprobar":
        id_solicitud = data.get("id_solicitud")
        usuario = (data.get("usuario") or "").strip()
        contrasena = (data.get("contrasena") or "").strip()

        if not id_solicitud or not usuario or not contrasena:
            return JsonResponse(
                {"ok": False, "mensaje": "id_solicitud, usuario y contrasena son obligatorios para aprobar."},
                status=400,
            )

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE dbo.solicitudes_acceso_bd
                    SET usuario = %s,
                        contrasena = %s,
                        estatus = 'CONFIRMADO'
                    WHERE id_solicitud = %s
                    """,
                    [usuario, contrasena, id_solicitud],
                )

                if cursor.rowcount == 0:
                    return JsonResponse(
                        {"ok": False, "mensaje": "No se encontro la solicitud para aprobar."},
                        status=404,
                    )

            return JsonResponse({"ok": True, "mensaje": "Solicitud aprobada correctamente."})
        except Exception as e:
            return JsonResponse({"ok": False, "mensaje": f"Error al aprobar la solicitud: {str(e)}"}, status=500)

    nombre_completo = (data.get("nombre_completo") or "").strip()
    correo = (data.get("correo") or "").strip()
    coordinacion = (data.get("coordinacion") or "").strip() or None
    matricula = (data.get("matricula") or "").strip() or None
    rol = (data.get("rol") or "").strip() or None
    oficio_nombre_archivo = (data.get("oficio_nombre_archivo") or "").strip()
    oficio_pdf_base64 = (data.get("oficio_pdf_base64") or "").strip()
    bases_datos_csv = (data.get("bases_datos_csv") or "").strip()

    if not nombre_completo or not correo or not bases_datos_csv:
        return JsonResponse(
            {"ok": False, "mensaje": "nombre_completo, correo y bases_datos_csv son obligatorios."},
            status=400,
        )

    try:
        ruta_oficio_guardado = _guardar_oficio_pdf(oficio_nombre_archivo, oficio_pdf_base64)
    except ValueError as exc:
        return JsonResponse({"ok": False, "mensaje": str(exc)}, status=400)

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO dbo.solicitudes_acceso_bd
                    (nombre_completo, correo, coordinacion, matricula, rol, bases_datos_csv)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                [nombre_completo, correo, coordinacion, matricula, rol, bases_datos_csv],
            )
        respuesta = {"ok": True, "mensaje": "Solicitud registrada correctamente."}
        if ruta_oficio_guardado:
            respuesta["oficio_url"] = ruta_oficio_guardado
        return JsonResponse(respuesta)
    except Exception as e:
        return JsonResponse({"ok": False, "mensaje": f"Error al guardar la solicitud: {str(e)}"}, status=500)


@api_view(["GET", "POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def guardar_solicitud_especial_bd(request):
    """Registra y consulta solicitudes especiales de base de datos con ticket autogenerado."""
    if request.method == "GET":
        estatus = (request.query_params.get("estatus") or "PENDIENTE").strip().upper()
        detalle = (request.query_params.get("detalle") or "").strip().lower()
        correo = (request.query_params.get("correo") or "").strip().lower()
        nom_cuenta = (request.query_params.get("nom_cuenta") or "").strip().lower()

        try:
            with connection.cursor() as cursor:
                if detalle == "mis-solicitudes":
                    filtros = []
                    params = []

                    if correo:
                        filtros.append("LOWER(LTRIM(RTRIM(correo))) = %s")
                        params.append(correo)
                    if nom_cuenta:
                        filtros.append("LOWER(LTRIM(RTRIM(correo))) = %s")
                        params.append(nom_cuenta)

                    if not filtros:
                        return JsonResponse(
                            {"ok": False, "mensaje": "Debes enviar correo o nom_cuenta para consultar solicitudes."},
                            status=400,
                        )

                    where_filtro = " OR ".join(filtros)
                    cursor.execute(
                        f"""
                        SELECT *
                        FROM dbo.sistema_solicitudes_expeciales_bd
                        WHERE ({where_filtro})
                        ORDER BY id_solicitud_especial DESC
                        """,
                        params,
                    )
                    columns = [col[0] for col in cursor.description] if cursor.description else []
                    rows = cursor.fetchall()
                    items = [dict(zip(columns, row)) for row in rows]
                    return JsonResponse({"ok": True, "items": items, "total": len(items)})

                if detalle == "tabla":
                    cursor.execute(
                        """
                        SELECT *
                        FROM dbo.sistema_solicitudes_expeciales_bd
                        WHERE estatus = %s
                        ORDER BY id_solicitud_especial DESC
                        """,
                        [estatus],
                    )
                    columns = [col[0] for col in cursor.description] if cursor.description else []
                    rows = cursor.fetchall()
                    items = [dict(zip(columns, row)) for row in rows]
                    return JsonResponse({"ok": True, "estatus": estatus, "items": items, "total": len(items)})

                cursor.execute(
                    """
                    SELECT COUNT(1)
                    FROM dbo.sistema_solicitudes_expeciales_bd
                    WHERE estatus = %s
                    """,
                    [estatus],
                )
                row = cursor.fetchone()

            total = int(row[0] if row and row[0] is not None else 0)
            return JsonResponse({"ok": True, "estatus": estatus, "total": total})
        except Exception as e:
            return JsonResponse(
                {"ok": False, "mensaje": f"Error al consultar solicitudes especiales: {str(e)}"},
                status=500,
            )

    data = request.data
    nombre_completo = (data.get("nombre_completo") or "").strip()
    correo = (data.get("correo") or "").strip()
    coordinacion = (data.get("coordinacion") or "").strip() or None
    rol = (data.get("rol") or "").strip() or None
    tabla = (data.get("tabla") or "").strip() or None
    cruce = (data.get("cruce") or "").strip().upper() or None
    con_quien_se_cruza = (data.get("con_quien_se_cruza") or "").strip() or None
    oficio_nombre_archivo = (data.get("oficio_nombre_archivo") or "").strip()
    oficio_pdf_base64 = (data.get("oficio_pdf_base64") or "").strip()
    bases_datos_csv = (data.get("bases_datos_csv") or "").strip()

    if not nombre_completo or not correo or not bases_datos_csv:
        return JsonResponse(
            {"ok": False, "mensaje": "nombre_completo, correo y bases_datos_csv son obligatorios."},
            status=400,
        )

    if cruce not in (None, "SI", "NO"):
        return JsonResponse({"ok": False, "mensaje": "El campo cruce solo permite SI o NO."}, status=400)

    if cruce == "SI" and not con_quien_se_cruza:
        return JsonResponse(
            {"ok": False, "mensaje": "Debes indicar con quien se cruza la informacion."},
            status=400,
        )

    if cruce != "SI":
        con_quien_se_cruza = None

    try:
        ruta_oficio_guardado = _guardar_oficio_pdf(oficio_nombre_archivo, oficio_pdf_base64)
    except ValueError as exc:
        return JsonResponse({"ok": False, "mensaje": str(exc)}, status=400)

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO dbo.sistema_solicitudes_expeciales_bd
                    (
                        nombre_completo,
                        correo,
                        coordinacion,
                        rol,
                        bases_datos_csv,
                        tabla,
                        cruce,
                        con_quien_se_cruza,
                        oficio_nombre_archivo,
                        oficio_url
                    )
                OUTPUT inserted.id_solicitud_especial, inserted.ticket
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    nombre_completo,
                    correo,
                    coordinacion,
                    rol,
                    bases_datos_csv,
                    tabla,
                    cruce,
                    con_quien_se_cruza,
                    oficio_nombre_archivo or None,
                    ruta_oficio_guardado,
                ],
            )
            row = cursor.fetchone()

        respuesta = {"ok": True, "mensaje": "Solicitud especial registrada correctamente."}
        if row:
            respuesta["id_solicitud_especial"] = row[0]
            respuesta["ticket"] = row[1]
        if ruta_oficio_guardado:
            respuesta["oficio_url"] = ruta_oficio_guardado
        return JsonResponse(respuesta)
    except Exception as e:
        return JsonResponse(
            {"ok": False, "mensaje": f"Error al guardar la solicitud especial: {str(e)}"},
            status=500,
        )


# --- Termina Mario Solicitudes especiales----


@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def bitacoracarga(request):


    query = """
        SELECT 
            b.nombre AS nombre_area,
            c.nombre AS nombre_tema,
            CONCAT(d.fld_nombreUsuario, ' ', d.fld_primer_ap, ' ', d.fld_segundo_ap) AS usuario,
            a.nombre_archivo,
            a.fecha_carga,
            a.registros_total
        FROM log_carga a
        INNER JOIN cat_area b ON a.id_area = b.id_area
        INNER JOIN cat_tema c ON a.id_tema = c.id_tema
        INNER JOIN cat_usuarios d ON a.pk_idUsuario = d.pk_idUsuario
    """

    query += " ORDER BY a.fecha_carga DESC"
    # print("Query: Check", flush=True)
    #  Ejecutar query
    with connection.cursor() as cursor:
        cursor.execute(query)

        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
    # print("Cursor: Check", flush=True)
    #  Convertir a JSON
    data = [
        dict(zip(columns, row))
        for row in rows
    ]
    print("Converted: Check", flush=True)
    return Response(data)


@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def getRegion(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT distinct [Region] as idRegion, [Region] FROM [DB_Catalogos].[dbo].[CUMM_ACTUAL]
        """)
        rows = cursor.fetchall()

    data = [
        {
            "id_region": r[0],
            "nombre": r[1],
            
        }
        for r in rows
    ]

    return Response(data)

@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def getEntidad(request):
    idRegion = request.GET.get("idRegion")
    if not idRegion:
        return Response([], status=200)
        
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT distinct [ClaveEntidadFederativa] as idEntidad, EntidadFederativa as Entidad FROM [DB_Catalogos].[dbo].[CUMM_ACTUAL] WHERE [Region] = %s
        """, [idRegion])
        rows = cursor.fetchall()

    data = [
        {
            "id_entidad": r[0],
            "Entidad": r[1],
            
        }
        for r in rows
    ]

    return Response(data)

@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def getNivelAtencion(request):
    idEntidad = request.GET.get("idEntidad")
    if not idEntidad:
        return Response([], status=200)
        
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT distinct NivelAtencion as id_NivelAtencion, NivelAtencion as Nombre
            FROM [DB_Catalogos].[dbo].[CUMM_ACTUAL] 
            WHERE [ClaveEntidadFederativa] = %s
            AND NivelAtencion in('Segundo Nivel', 'Tercer Nivel')                       
            order by NivelAtencion
        """, [idEntidad])
        rows = cursor.fetchall()

    data = [
        {
            "id_nivel_atencion": r[0],
            "nombre": r[1],
            
        }
        for r in rows
    ]

    return Response(data)

@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def getUnidad(request):
    idEntidad = request.GET.get("idEntidad")
    id_nivel_atencion = request.GET.get("id_nivel_atencion")


    if not idEntidad and not id_nivel_atencion:
        return Response([], status=200)
    


    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT distinct [ClavePresupuestal] as id_Unidad, [DenominacionUnidad] as Nombre
            FROM [DB_Catalogos].[dbo].[CUMM_ACTUAL] 
            WHERE [ClaveEntidadFederativa] = %s and [NivelAtencion] = %s
                and (es_umae is null or es_umae = 'UMAE')
            order by [DenominacionUnidad]
        """, [idEntidad, id_nivel_atencion])
        rows = cursor.fetchall()

    data = [
        {
            "id_unidad_medica": r[0],
            "nombre": r[1],
            
        }
        for r in rows
    ]

    return Response(data)


def convertir_pptx_a_pdf_local(pptx_path: Path, pdf_path: Path):
    """Convierte un PPTX a PDF usando LibreOffice dentro del contenedor."""
    cmd = [
        "libreoffice",
        "--headless",
        "--convert-to",
        "pdf",
        "--outdir",
        str(pdf_path.parent),
        str(pptx_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"LibreOffice fall+� ({result.returncode}): {result.stderr or result.stdout}"
        )
    if not pdf_path.exists():
        raise RuntimeError("LibreOffice termin+� sin generar el PDF")


@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def getGeneraFicha(request):

    idUnidad = request.GET.get("idUnidad")

    if not idUnidad:
        return JsonResponse({
            "ok": False,
            "mensaje": "idUnidad requerido"
        }, status=400)

    import sys, logging
    sys.path.insert(0, '.')
    from ficha.src.core.engine import FichaEngine


    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    engine = FichaEngine()
    # Genera el pptx
    ruta = engine.generar_ficha(idUnidad)

    # Mario: valida que el motor regrese una ruta v+�lida antes de procesar salida.
    if not ruta:
        return JsonResponse({
            "ok": False,
            "mensaje": "No se pudo generar la ficha en formato PPTX"
        }, status=500)

    # Convierte a objeto Path
    pptx_path = Path(ruta)
    # Ruta del PDF en la misma carpeta
    pdf_path = pptx_path.with_suffix(".pdf")

    nombre_archivo = pptx_path.name
    nombre_pdf = pdf_path.name

    # print(f"Archivo PPTX: {ruta}", flush=True)
    # print(f"Archivo PDF: {pdf_path}", flush=True)

    try:
        convertir_pptx_a_pdf_local(pptx_path, pdf_path)
        # print(f"Conversi+�n local exitosa: {pdf_path}", flush=True)
    except Exception as exc:
        # print(f"Error conversi+�n local: {exc}", flush=True)
        # Si se requiere mantener el fallback a Windows + COM, puedes
        # volver a activar este bloque, pero se recomienda usar LibreOffice.
        raise

    return JsonResponse({
        
        "ok": True,
        "url": f"/media/{nombre_pdf}",
        "pptx_url": f"/media/{nombre_archivo}"
    })


@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([AllowAny])
def getGeneraFichaPresidencial(request):
    cve_ent = (
        request.GET.get("cveEntidad")
        or request.GET.get("idEntidad")
        or request.GET.get("claveEntidad")
    )

    if not cve_ent:
        return JsonResponse({
            "ok": False,
            "mensaje": "cveEntidad requerido"
        }, status=400)

    cve_ent = str(cve_ent).zfill(2)

    import os
    import shutil
    import sys
    import tempfile
    import textwrap

    temp_dir = tempfile.mkdtemp(prefix="ficha_presidencial_")
    script_dir = Path(__file__).resolve().parents[1] / "ficha_presidencial" / "script"

    try:
        script = textwrap.dedent(
            f"""
            import importlib.util
            import sys
            from pathlib import Path

            script_dir = Path({str(script_dir)!r})
            config_path = script_dir / 'config.py'
            engine_path = script_dir / 'engine.py'

            spec_config = importlib.util.spec_from_file_location('ficha_presidencial_config', config_path)
            config_module = importlib.util.module_from_spec(spec_config)
            sys.modules['ficha_presidencial_config'] = config_module
            spec_config.loader.exec_module(config_module)

            sys.modules['config'] = config_module

            spec_engine = importlib.util.spec_from_file_location('ficha_presidencial_engine', engine_path)
            engine_module = importlib.util.module_from_spec(spec_engine)
            sys.modules['ficha_presidencial_engine'] = engine_module
            spec_engine.loader.exec_module(engine_module)

            generador = engine_module.GeneradorFichas()
            ruta = generador.generar({cve_ent!r}, output_dir={temp_dir!r})
            print(ruta)
            """
        )

        resultado = subprocess.run(
            [sys.executable, "-c", script],
            cwd=str(script_dir),
            env={**os.environ},
            capture_output=True,
            text=True,
        )

        if resultado.returncode != 0:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return JsonResponse({
                "ok": False,
                "mensaje": "No se pudo generar la ficha presidencial en formato PPTX",
                "detalle": resultado.stderr.strip() or resultado.stdout.strip(),
            }, status=500)

        ruta = resultado.stdout.strip().splitlines()[-1] if resultado.stdout.strip() else ""

        if not ruta:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return JsonResponse({
                "ok": False,
                "mensaje": "No se pudo generar la ficha presidencial en formato PPTX"
            }, status=500)

        pptx_path = Path(ruta)
        if not pptx_path.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
            return JsonResponse({
                "ok": False,
                "mensaje": "La ficha presidencial no se genero en la ruta esperada"
            }, status=500)

        response = FileResponse(
            open(pptx_path, "rb"),
            as_attachment=True,
            filename=pptx_path.name,
        )
        response["X-Generated-Entity"] = cve_ent

        def _cleanup_temp_file():
            try:
                if hasattr(response, "file_to_stream") and response.file_to_stream:
                    response.file_to_stream.close()
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)

        response._resource_closers.append(_cleanup_temp_file)
        return response
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise


@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([AllowAny])
def getGeneraFichaPresidencialLote(request):
    import os
    import shutil
    import sys
    import tempfile
    import textwrap
    import zipfile

    temp_dir = tempfile.mkdtemp(prefix="ficha_presidencial_lote_")
    script_dir = Path(__file__).resolve().parents[1] / "ficha_presidencial" / "script"

    try:
        script = "\n".join([
            "import importlib.util",
            "import sys",
            "from pathlib import Path",
            "",
            f"script_dir = Path({str(script_dir)!r})",
            "config_path = script_dir / 'config.py'",
            "engine_path = script_dir / 'engine.py'",
            "",
            "spec_config = importlib.util.spec_from_file_location('ficha_presidencial_config', config_path)",
            "config_module = importlib.util.module_from_spec(spec_config)",
            "sys.modules['ficha_presidencial_config'] = config_module",
            "spec_config.loader.exec_module(config_module)",
            "",
            "sys.modules['config'] = config_module",
            "",
            "spec_engine = importlib.util.spec_from_file_location('ficha_presidencial_engine', engine_path)",
            "engine_module = importlib.util.module_from_spec(spec_engine)",
            "sys.modules['ficha_presidencial_engine'] = engine_module",
            "spec_engine.loader.exec_module(engine_module)",
            "",
            "generador = engine_module.GeneradorFichas()",
            f"rutas = generador.generar_lote(output_dir={temp_dir!r})",
            "print('\\n'.join(rutas))",
        ])

        resultado = subprocess.run(
            [sys.executable, "-c", script],
            cwd=str(script_dir),
            env={**os.environ},
            capture_output=True,
            text=True,
        )

        if resultado.returncode != 0:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return JsonResponse({
                "ok": False,
                "mensaje": "No se pudo generar el lote de fichas presidenciales",
                "detalle": resultado.stderr.strip() or resultado.stdout.strip(),
            }, status=500)

        rutas = [linea.strip() for linea in resultado.stdout.splitlines() if linea.strip()]
        rutas = [ruta for ruta in rutas if ruta.lower().endswith(".pptx")]

        if not rutas:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return JsonResponse({
                "ok": False,
                "mensaje": "No se generaron archivos PPTX para el lote"
            }, status=500)

        zip_path = Path(temp_dir) / "fichas_presidenciales.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
            for ruta in rutas:
                ruta_path = Path(ruta)
                if ruta_path.exists():
                    zip_file.write(ruta_path, arcname=ruta_path.name)

        if not zip_path.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
            return JsonResponse({
                "ok": False,
                "mensaje": "No se pudo crear el ZIP del lote de fichas presidenciales"
            }, status=500)

        response = FileResponse(
            open(zip_path, "rb"),
            as_attachment=True,
            filename=zip_path.name,
        )
        response["X-Generated-Count"] = str(len(rutas))

        def _cleanup_temp_file():
            try:
                if hasattr(response, "file_to_stream") and response.file_to_stream:
                    response.file_to_stream.close()
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)

        response._resource_closers.append(_cleanup_temp_file)
        return response
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise


@api_view(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def chatbot_query(request):
    """
    Chatbot local sin IA externa.
    Primero intenta resolver consultas IFU con hospital/variable/ámbito.
    Si no aplica, interpreta preguntas de estructura o estadística sobre
    [DB_Catalogos].[dbo].[Cat_IFU_Actual].
    """
    import re

    def obtener_numero(texto: str, default: int = 10, minimo: int = 1, maximo: int = 100) -> int:
        m = re.search(r'\b(\d{1,3})\b', texto)
        if not m:
            return default
        n = int(m.group(1))
        return max(min(n, maximo), minimo)

    pregunta = str(request.data.get("pregunta", "")).strip()
    if not pregunta:
        return Response({"error": "La pregunta no puede estar vacía."}, status=400)

    pnorm = _normalizar_chatbot_m(pregunta)
    cve_presupuestal = _extraer_cve_presupuestal(pregunta)

    try:
        if _es_texto_no_consulta(pnorm):
            return Response({
                "ok": True,
                "status": "ayuda",
                "respuesta": (
                    "Puedo responder consultas sobre Cat_IFU_Actual usando descripcion, valor y CvePresupuestal. "
                    "Ejemplos: 'camas censables en la cvepresupuestal 010101012151' o 'top 5 camas censables'."
                ),
                "datos": [],
            })

        if _es_consulta_de_conteo(pnorm) and _es_conteo_hospitales_general(pnorm):
            ambito_detectado_general = chatbot_detector_engine.buscador_ambito.buscar(pnorm)
            ambito_general = (
                ambito_detectado_general
                if ambito_detectado_general and ambito_detectado_general.get("tipo") != "HOSPITAL"
                else None
            )
            if not ambito_general:
                ambito_general = _resolver_ambito_general_desde_cumm(pnorm)

            if not ambito_general:
                return Response({
                    "ok": True,
                    "status": "falta_ambito",
                    "respuesta": (
                        "Para contar hospitales primero necesito identificar el ámbito en CUMM "
                        "(entidad, delegación, región o nivel)."
                    ),
                    "datos": [],
                })

            total, top = _contar_hospitales_por_ambito_general(
                ambito=ambito_general,
                top_n=5,
            )
            ambito_texto = (
                ambito_general.get("desc_original")
                or ambito_general.get("descripcion")
                or ambito_general.get("id")
                or "el ámbito solicitado"
            )

            lineas_top = []
            for fila in top:
                nombre = fila.get("DenominacionUnidad") or fila.get("CvePresupuestal")
                lineas_top.append(
                    f"- {nombre} (CvePresupuestal {fila.get('CvePresupuestal')})"
                )

            return Response({
                "ok": True,
                "status": "ok",
                "respuesta": (
                    f"Hay {total} hospitales en {ambito_texto}."
                    + ("\nTop 5 de hospitales:\n" + "\n".join(lineas_top) if lineas_top else "")
                ),
                "pregunta_original": pregunta,
                "datos": [{
                    "total_hospitales": total,
                    "ambito": ambito_general,
                    "top_5": top,
                }],
            })

        if _es_consulta_de_estructura(pnorm):
            with connection.cursor() as cursor:
                cursor.execute("SET LOCK_TIMEOUT 5000")
                cursor.execute("SELECT TOP 1 * FROM [DB_Catalogos].[dbo].[Cat_IFU_Actual]")
                columnas = [col[0] for col in cursor.description]

            if not columnas:
                return Response({"respuesta": "No encontré columnas en la tabla Cat_IFU_Actual."}, status=200)

            if 'columna' in pnorm or 'campos' in pnorm or 'estructura' in pnorm or 'schema' in pnorm or 'esquema' in pnorm:
                return Response({
                    "ok": True,
                    "respuesta": (
                        f"La tabla Cat_IFU_Actual tiene {len(columnas)} columnas: "
                        + ', '.join(columnas)
                    ),
                    "datos": [],
                })

        hospital_detectado, resultado_hospital, texto_hospital = _resolver_hospital_preciso(pregunta)
        variable_detectada, resultado_variable, texto_variable = _resolver_variable_precisa(
            pregunta,
            hospital_detectado,
        )
        tipo_recurso_pregunta = _detectar_tipo_recurso(pnorm)
        if variable_detectada and tipo_recurso_pregunta:
            desc_var = _normalizar_chatbot_m(
                variable_detectada.get("descripcion")
                or variable_detectada.get("desc_original")
                or ""
            )
            if not _descripcion_cumple_tipo_recurso(desc_var, tipo_recurso_pregunta):
                variable_detectada = None

        if not variable_detectada:
            variable_detectada = _resolver_concepto_descripcion_ifu(pregunta)
            if variable_detectada:
                resultado_variable = {
                    "status": "ganador_claro",
                    "variable": variable_detectada,
                    "score": 1.0,
                    "texto_usado": pnorm,
                    "regla_aplicada": "resolver_concepto_descripcion_ifu",
                }

        if not variable_detectada:
            variable_detectada = _resolver_variable_camas_censables(pnorm)
            if variable_detectada:
                resultado_variable = {
                    "status": "ganador_claro",
                    "variable": variable_detectada,
                    "score": 1.0,
                    "texto_usado": pnorm,
                    "regla_aplicada": "resolver_variable_camas_censables",
                }
        ambito_detectado = chatbot_detector_engine.buscador_ambito.buscar(pnorm)

        hospital_ambito = ambito_detectado if ambito_detectado and ambito_detectado.get("tipo") != "HOSPITAL" else None
        # Si ya detectamos una unidad hospitalaria concreta, no debemos desviar
        # la consulta a un ámbito macro como REGION/ENTIDAD.
        if hospital_detectado:
            hospital_ambito = None

        if _es_consulta_de_conteo(pnorm) and hospital_ambito and _es_conteo_hospitales_general(pnorm):
            total, top = _contar_hospitales_por_ambito_general(
                ambito=hospital_ambito,
                top_n=5,
            )
            ambito_texto = (
                hospital_ambito.get("desc_original")
                or hospital_ambito.get("descripcion")
                or hospital_ambito.get("id")
                or "el ámbito solicitado"
            )

            lineas_top = []
            for fila in top:
                nombre = fila.get("DenominacionUnidad") or fila.get("CvePresupuestal")
                lineas_top.append(
                    f"- {nombre} (CvePresupuestal {fila.get('CvePresupuestal')})"
                )

            return Response({
                "ok": True,
                "status": "ok",
                "respuesta": (
                    f"Hay {total} hospitales en {ambito_texto}."
                    + ("\nTop 5 de hospitales:\n" + "\n".join(lineas_top) if lineas_top else "")
                ),
                "pregunta_original": pregunta,
                "datos": [{
                    "total_hospitales": total,
                    "ambito": hospital_ambito,
                    "top_5": top,
                }],
            })

        if _es_consulta_de_conteo(pnorm) and variable_detectada and hospital_ambito:
            total, top = _contar_hospitales_por_ambito_y_concepto(
                ambito=hospital_ambito,
                variable_detectada=variable_detectada,
                top_n=5,
            )
            ambito_texto = (
                hospital_ambito.get("desc_original")
                or hospital_ambito.get("descripcion")
                or hospital_ambito.get("id")
                or "el ámbito solicitado"
            )

            lineas_top = []
            for fila in top:
                nombre = fila.get("DenominacionUnidad") or fila.get("CvePresupuestal")
                valor_total = fila.get("valor_total")
                valor_txt = f"{valor_total:.2f}" if isinstance(valor_total, (int, float)) else str(valor_total)
                lineas_top.append(
                    f"- {nombre} (CvePresupuestal {fila.get('CvePresupuestal')}): {valor_txt}"
                )

            return Response({
                "ok": True,
                "status": "ok",
                "respuesta": (
                    f"{total} hospitales tienen el concepto {variable_detectada.get('descripcion') or variable_detectada.get('desc_original')} en {ambito_texto}."
                    + ("\nTop 5 de hospitales:\n" + "\n".join(lineas_top) if lineas_top else "")
                ),
                "pregunta_original": pregunta,
                "datos": [{
                    "total_hospitales": total,
                    "ambito": hospital_ambito,
                    "top_5": top,
                }],
            })

        if variable_detectada and _es_consulta_comparativa(pnorm):
            ascendente = any(
                palabra in pnorm
                for palabra in ("menos", "menor", "minimo", "mínimo")
            )
            top_n = obtener_numero(pnorm, default=10, minimo=1, maximo=50)
            datos = _consultar_ranking_hospitales(
                variable_id=variable_detectada["id"],
                top_n=top_n,
                ascendente=ascendente,
            )

            if not datos:
                return Response({
                    "ok": True,
                    "status": "sin_datos",
                    "respuesta": "No encontré datos para comparar ese concepto entre unidades.",
                    "datos": [],
                })

            ganador = datos[0]
            valor_ganador = ganador.get("valor")
            if valor_ganador is None:
                return Response({
                    "ok": True,
                    "status": "sin_datos",
                    "respuesta": "Encontré el concepto, pero no pude calcular su valor para compararlo.",
                    "datos": datos,
                })

            valor_texto = f"{valor_ganador:.2f}" if isinstance(valor_ganador, (int, float)) else str(valor_ganador)
            sentido = "menor" if ascendente else "mayor"
            encabezado = (
                f"La unidad con {sentido} valor en {ganador.get('descripcion') or variable_detectada.get('descripcion') or 'el concepto solicitado'} es "
                f"{ganador.get('DenominacionUnidad') or ganador.get('ClavePresupuestal')} "
                f"(CvePresupuestal {ganador.get('ClavePresupuestal')}) con {valor_texto}."
            )

            lineas = []
            for fila in datos:
                valor = fila.get("valor")
                valor_fila = f"{valor:.2f}" if isinstance(valor, (int, float)) else str(valor)
                nombre_unidad = fila.get("DenominacionUnidad") or fila.get("ClavePresupuestal")
                lineas.append(
                    f"- {nombre_unidad} (CvePresupuestal {fila.get('ClavePresupuestal')}): {valor_fila}"
                )

            return Response({
                "ok": True,
                "status": "ok",
                "respuesta": encabezado + "\n" + "\n".join(lineas),
                "pregunta_original": pregunta,
                "datos": datos,
            })

        if cve_presupuestal and variable_detectada:
            datos = _consultar_valor_ifu_por_cve(
                cve_presupuestal=cve_presupuestal,
                variable_id=variable_detectada["id"],
            )
            if not datos:
                return Response({
                    "ok": True,
                    "status": "sin_datos",
                    "respuesta": f"No encontré datos para la CvePresupuestal {cve_presupuestal} y el concepto {variable_detectada.get('descripcion') or variable_detectada.get('desc_original')}.",
                    "datos": [],
                })

            return Response({
                "ok": True,
                "status": "ok",
                "respuesta": _formatear_resultado_ifu(datos),
                "pregunta_original": pregunta,
                "datos": datos,
            })

        if cve_presupuestal and not variable_detectada:
            return Response({
                "ok": True,
                "status": "falta_variable",
                "respuesta": (
                    f"Identifiqué la CvePresupuestal {cve_presupuestal}, pero me falta el concepto a consultar en la columna descripcion."
                ),
                "datos": [],
            })

        if variable_detectada and (hospital_detectado or hospital_ambito):
            if hospital_ambito:
                datos = chatbot_m_consulta_ifu.obtener_valor_dinamico(
                    tipo_ambito=hospital_ambito["tipo"],
                    filtro_id=hospital_ambito["id"],
                    variable_id=variable_detectada["id"],
                )
                if not datos:
                    return Response({
                        "ok": True,
                        "status": "sin_datos",
                        "respuesta": "No encontré datos para esa combinación de ámbito y variable.",
                        "datos": [],
                    })
                return Response({
                    "ok": True,
                    "status": "ok",
                    "respuesta": _formatear_resultado_ifu(datos),
                    "pregunta_original": pregunta,
                    "datos": datos,
                })

            datos = _consultar_valor_concepto_por_unidad(
                cve_presupuestal=hospital_detectado["id"],
                variable_detectada=variable_detectada,
            )
            if not datos:
                return Response({
                    "ok": True,
                    "status": "sin_datos",
                    "respuesta": "No encontré datos para esa unidad y variable.",
                    "datos": [],
                })

            return Response({
                "ok": True,
                "status": "ok",
                "respuesta": _formatear_resultado_ifu(datos),
                "pregunta_original": pregunta,
                "datos": datos,
            })

        if _es_consulta_de_conteo(pnorm) and hospital_detectado and not variable_detectada:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM [DB_Catalogos].[dbo].[Cat_IFU_Actual] a
                    JOIN [DB_Catalogos].[dbo].[CUMM_ACTUAL] b
                        ON a.CvePresupuestal = b.ClavePresupuestal
                        COLLATE Modern_Spanish_CI_AS
                    WHERE b.ClavePresupuestal = %s
                    """,
                    [hospital_detectado["id"]],
                )
                total = cursor.fetchone()[0]

            return Response({
                "ok": True,
                "status": "ok",
                "respuesta": f"La unidad {hospital_detectado.get('desc_original') or hospital_detectado.get('nombre_original')} tiene {total} registros en Cat_IFU_Actual.",
                "datos": [{"total": total}],
            })

        if _es_consulta_de_conteo(pnorm) and variable_detectada and not hospital_detectado and not hospital_ambito:
            descripcion_concepto = (
                str(variable_detectada.get("descripcion") or variable_detectada.get("desc_original") or "")
                .strip()
                .replace(".", "")
            )
            patron_concepto = f"%{descripcion_concepto}%" if descripcion_concepto else None

            with connection.cursor() as cursor:
                if patron_concepto:
                    cursor.execute(
                        """
                        SELECT COUNT(DISTINCT CvePresupuestal)
                        FROM [DB_Catalogos].[dbo].[Cat_IFU_Actual]
                        WHERE (variable_nva = %s
                               OR descripcion COLLATE Modern_Spanish_CI_AI LIKE %s)
                          AND TRY_CONVERT(decimal(18, 4), REPLACE(valor, ',', '')) > 0
                        """,
                        [variable_detectada["id"], patron_concepto],
                    )
                else:
                    cursor.execute(
                        """
                        SELECT COUNT(DISTINCT CvePresupuestal)
                        FROM [DB_Catalogos].[dbo].[Cat_IFU_Actual]
                        WHERE variable_nva = %s
                          AND TRY_CONVERT(decimal(18, 4), REPLACE(valor, ',', '')) > 0
                        """,
                        [variable_detectada["id"]],
                    )
                total = cursor.fetchone()[0]

                if patron_concepto:
                    cursor.execute(
                        """
                        SELECT TOP 5
                            a.CvePresupuestal,
                            MAX(b.DenominacionUnidad) AS DenominacionUnidad,
                            MAX(a.descripcion) AS descripcion,
                            SUM(TRY_CONVERT(decimal(18, 4), REPLACE(a.valor, ',', ''))) AS valor_total
                        FROM [DB_Catalogos].[dbo].[Cat_IFU_Actual] a
                        LEFT JOIN [DB_Catalogos].[dbo].[CUMM_ACTUAL] b
                            ON a.CvePresupuestal = b.ClavePresupuestal
                            COLLATE Modern_Spanish_CI_AS
                        WHERE (a.variable_nva = %s
                               OR a.descripcion COLLATE Modern_Spanish_CI_AI LIKE %s)
                          AND TRY_CONVERT(decimal(18, 4), REPLACE(a.valor, ',', '')) > 0
                        GROUP BY a.CvePresupuestal
                        ORDER BY valor_total DESC, a.CvePresupuestal ASC
                        """,
                        [variable_detectada["id"], patron_concepto],
                    )
                else:
                    cursor.execute(
                        """
                        SELECT TOP 5
                            a.CvePresupuestal,
                            MAX(b.DenominacionUnidad) AS DenominacionUnidad,
                            MAX(a.descripcion) AS descripcion,
                            SUM(TRY_CONVERT(decimal(18, 4), REPLACE(a.valor, ',', ''))) AS valor_total
                        FROM [DB_Catalogos].[dbo].[Cat_IFU_Actual] a
                        LEFT JOIN [DB_Catalogos].[dbo].[CUMM_ACTUAL] b
                            ON a.CvePresupuestal = b.ClavePresupuestal
                            COLLATE Modern_Spanish_CI_AS
                        WHERE a.variable_nva = %s
                          AND TRY_CONVERT(decimal(18, 4), REPLACE(a.valor, ',', '')) > 0
                        GROUP BY a.CvePresupuestal
                        ORDER BY valor_total DESC, a.CvePresupuestal ASC
                        """,
                        [variable_detectada["id"]],
                    )

                columnas_top = [col[0] for col in cursor.description] if cursor.description else []
                filas_top = cursor.fetchall()

            top_5 = [dict(zip(columnas_top, fila)) for fila in filas_top] if columnas_top else []

            lineas_top = []
            for fila in top_5:
                nombre = fila.get("DenominacionUnidad") or fila.get("CvePresupuestal")
                valor_total = fila.get("valor_total")
                valor_texto = f"{valor_total:.2f}" if isinstance(valor_total, (int, float)) else str(valor_total)
                lineas_top.append(
                    f"- {nombre} (CvePresupuestal {fila.get('CvePresupuestal')}): {valor_texto}"
                )

            return Response({
                "ok": True,
                "status": "ok",
                "respuesta": (
                    f"{total} hospitales tienen el concepto "
                    f"{variable_detectada.get('descripcion') or variable_detectada.get('desc_original')}."
                    + ("\nTop 5 de hospitales:\n" + "\n".join(lineas_top) if lineas_top else "")
                ),
                "datos": [{"total_hospitales": total, "top_5": top_5}],
            })

        if hospital_detectado and not variable_detectada and not hospital_ambito:
            return Response({
                "ok": True,
                "status": "falta_variable",
                "respuesta": (
                    f"Identifiqué la unidad {hospital_detectado.get('desc_original') or hospital_detectado.get('nombre_original')}, "
                    "pero me falta la variable a consultar."
                ),
                "datos": [],
            })

        if variable_detectada and not hospital_detectado and not hospital_ambito:
            return Response({
                "ok": True,
                "status": "falta_ambito",
                "respuesta": (
                    f"Identifiqué la variable {variable_detectada.get('descripcion') or variable_detectada.get('desc_original')}, "
                    "pero me falta la unidad o el ámbito a consultar."
                ),
                "datos": [],
            })

        with connection.cursor() as cursor:
            cursor.execute("SET LOCK_TIMEOUT 5000")
            cursor.execute("SELECT TOP 1 * FROM [DB_Catalogos].[dbo].[Cat_IFU_Actual]")
            columnas = [col[0] for col in cursor.description]

            if not columnas:
                return Response({"respuesta": "No encontré columnas en la tabla Cat_IFU_Actual."}, status=200)

            col_norm = {_normalizar_chatbot_m(col): col for col in columnas}

            columna_objetivo = None
            for cnorm, coriginal in col_norm.items():
                if cnorm and cnorm in pnorm:
                    columna_objetivo = coriginal
                    break

            if columna_objetivo and ('distintos' in pnorm or 'diferentes' in pnorm or 'unicos' in pnorm or 'unicos' in pnorm):
                cursor.execute(
                    f"SELECT COUNT(DISTINCT [{columna_objetivo}]) FROM [DB_Catalogos].[dbo].[Cat_IFU_Actual]"
                )
                total_distintos = cursor.fetchone()[0]
                return Response({
                    "ok": True,
                    "status": "ok",
                    "respuesta": f"La columna {columna_objetivo} tiene {total_distintos} valores distintos.",
                    "datos": [{"columna": columna_objetivo, "distintos": total_distintos}],
                })

            if columna_objetivo and ('por ' in pnorm or 'agrupa' in pnorm or 'group by' in pnorm):
                top_n = obtener_numero(pnorm, default=10, minimo=1, maximo=50)
                cursor.execute(
                    f"SELECT TOP ({top_n}) [{columna_objetivo}], COUNT(*) AS total "
                    f"FROM [DB_Catalogos].[dbo].[Cat_IFU_Actual] "
                    f"GROUP BY [{columna_objetivo}] ORDER BY total DESC"
                )
                rows = cursor.fetchall()
                if not rows:
                    return Response({"respuesta": "No encontré datos para agrupar con ese criterio."})

                lineas = [f"- {valor}: {total}" for valor, total in rows]
                return Response({
                    "ok": True,
                    "status": "ok",
                    "respuesta": (
                        f"Top {len(rows)} valores de {columna_objetivo} por cantidad:\n" + '\n'.join(lineas)
                    ),
                    "datos": [{"valor": valor, "total": total} for valor, total in rows],
                })

            pregunta_total = (
                'en total' in pnorm
                or 'total de registros' in pnorm
                or 'cuantos registros hay' in pnorm
                or 'cuantas filas hay' in pnorm
            )

            if pregunta_total:
                cursor.execute("SELECT COUNT(*) FROM [DB_Catalogos].[dbo].[Cat_IFU_Actual]")
                total = cursor.fetchone()[0]
                return Response({
                    "ok": True,
                    "status": "ok",
                    "respuesta": f"La tabla Cat_IFU_Actual tiene {total} registros en total.",
                    "datos": [{"total": total}],
                })

            if ('cuantos' in pnorm or 'cuantas' in pnorm) and not columna_objetivo:
                return Response({
                    "ok": True,
                    "status": "ayuda",
                    "respuesta": (
                        "Puedo ayudarte con el total general, una columna específica o una consulta por unidad y variable. "
                        "Ejemplos: 'cuantos registros hay en total', 'top 10 por EntidadFederativa' o 'camas censables en HGZ 30'."
                    ),
                    "datos": [],
                })

            top_n = obtener_numero(pnorm, default=10, minimo=1, maximo=50)
            cursor.execute(f"SELECT TOP ({top_n}) * FROM [DB_Catalogos].[dbo].[Cat_IFU_Actual]")
            rows = cursor.fetchall()
            if not rows:
                return Response({"respuesta": "La tabla Cat_IFU_Actual no tiene registros."})

            resumen = []
            for i, row in enumerate(rows, start=1):
                pares = []
                for col, val in zip(columnas, row):
                    if val is None:
                        continue
                    texto_val = str(val).strip()
                    if texto_val:
                        pares.append(f"{col}: {texto_val}")
                resumen.append(f"{i}. " + '; '.join(pares[:6]))

            return Response({
                "ok": True,
                "status": "ok",
                "respuesta": (
                    f"Te comparto una muestra de {len(rows)} registros de Cat_IFU_Actual:\n"
                    + '\n'.join(resumen)
                ),
                "datos": [dict(zip(columnas, row)) for row in rows],
            })

    except Exception as e:
        return Response({"error": str(e)}, status=500)

