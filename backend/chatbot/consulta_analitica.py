#Ejecuta de forma aislada los planes de consultas que voy construyendo

import logging

from django.db import connection


logger = logging.getLogger(__name__)


class ConsultaAnalitica:
    TIPOS_UNIDAD_SOPORTADOS = {"UMF", "HOSPITAL"}

    ORDEN_OPERACION = {
        "MAX": "DESC",
        "MIN": "ASC",
    }

    COLUMNAS_AMBITO = {
        "ENTIDAD": "b.ClaveEntidadFederativa",
        "DELEGACION": "b.NombreDelegacionUMAE",
        "REGION": "b.Region",
        "NIVEL_ATENCION": "b.NivelAtencion",
    }

    def __init__(self, conexion=None):
        self.conexion = connection if conexion is None else conexion

    def ejecutar_plan(self, plan):
        plan = plan if isinstance(plan, dict) else {}
        tipo_consulta = plan.get("tipo_consulta")

        if plan.get("status") != "plan_valido":
            return {
                "status": "plan_invalido",
                "tipo_consulta": tipo_consulta,
                "razon": plan.get("razon") or "plan_no_valido",
            }

        if tipo_consulta == "COUNT_UNIDADES":
            return self.contar_unidades(plan)

        if tipo_consulta == "EXTREMO_POR_UNIDAD":
            return self.obtener_extremo_por_unidad(plan)

        return {
            "status": "tipo_no_soportado",
            "tipo_consulta": tipo_consulta,
            "mensaje": (
                "La consulta analítica todavía no soporta este tipo de plan."
            ),
        }

    def contar_unidades(self, plan):
        tipo_unidad = plan.get("tipo_unidad")
        if tipo_unidad not in self.TIPOS_UNIDAD_SOPORTADOS:
            return {
                "status": "tipo_unidad_no_soportado",
                "tipo_consulta": "COUNT_UNIDADES",
                "tipo_unidad": tipo_unidad,
            }

        niveles_atencion = self._normalizar_niveles(
            plan.get("niveles_atencion")
        )
        if not niveles_atencion:
            return {
                "status": "plan_invalido",
                "tipo_consulta": "COUNT_UNIDADES",
                "razon": "sin_niveles_atencion",
            }

        resultado_ambito = self._construir_filtro_ambito(
            plan.get("ambito"),
            niveles_atencion,
        )
        if resultado_ambito.get("error"):
            return {
                "status": "plan_invalido",
                "tipo_consulta": "COUNT_UNIDADES",
                "razon": resultado_ambito["error"],
            }

        filtros = resultado_ambito["filtros"]
        parametros = resultado_ambito["parametros"]

        placeholders_niveles = ", ".join(
            ["%s"] * len(niveles_atencion)
        )
        filtros.append(
            f"b.NivelAtencion IN ({placeholders_niveles})"
        )
        parametros.extend(niveles_atencion)

        clausula_where = "\n              AND ".join(filtros)
        query = f"""
            SELECT COUNT(DISTINCT b.ClavePresupuestal) AS total_unidades
            FROM [DB_Catalogos].[dbo].[CUMM_ACTUAL] b
            WHERE {clausula_where}
        """

        try:
            with self.conexion.cursor() as cursor:
                cursor.execute(query, parametros)
                fila = cursor.fetchone()
        except Exception as error:
            logger.error(
                "No fue posible contar unidades: %s",
                type(error).__name__,
            )
            return {
                "status": "error_consulta",
                "tipo_consulta": "COUNT_UNIDADES",
                "mensaje": "No fue posible realizar el conteo de unidades.",
            }

        total_unidades = fila[0] if fila else 0

        return {
            "status": "ok",
            "tipo_consulta": "COUNT_UNIDADES",
            "operacion": "COUNT",
            "tipo_unidad": tipo_unidad,
            "descripcion_tipo_unidad": plan.get(
                "descripcion_tipo_unidad"
            ),
            "niveles_atencion": niveles_atencion,
            "ambito": plan.get("ambito"),
            "total_unidades": int(total_unidades or 0),
        }

    def obtener_extremo_por_unidad(self, plan):
        operacion = plan.get("operacion")
        orden = self.ORDEN_OPERACION.get(operacion)
        if orden is None:
            return {
                "status": "operacion_no_soportada",
                "tipo_consulta": "EXTREMO_POR_UNIDAD",
                "operacion": operacion,
            }

        tipo_unidad = plan.get("tipo_unidad")
        if tipo_unidad not in self.TIPOS_UNIDAD_SOPORTADOS:
            return {
                "status": "tipo_unidad_no_soportado",
                "tipo_consulta": "EXTREMO_POR_UNIDAD",
                "tipo_unidad": tipo_unidad,
            }

        niveles_atencion = self._normalizar_niveles(
            plan.get("niveles_atencion")
        )
        if not niveles_atencion:
            return {
                "status": "plan_invalido",
                "tipo_consulta": "EXTREMO_POR_UNIDAD",
                "razon": "sin_niveles_atencion",
            }

        resultado_ambito = self._construir_filtro_ambito(
            plan.get("ambito"),
            niveles_atencion,
        )
        if resultado_ambito.get("error"):
            return {
                "status": "plan_invalido",
                "tipo_consulta": "EXTREMO_POR_UNIDAD",
                "razon": resultado_ambito["error"],
            }

        variable = plan.get("variable")
        if variable is None:
            return {
                "status": "plan_invalido",
                "tipo_consulta": "EXTREMO_POR_UNIDAD",
                "razon": "falta_variable",
            }

        variable_id = self._obtener_id_variable(variable)
        if variable_id is None:
            return {
                "status": "plan_invalido",
                "tipo_consulta": "EXTREMO_POR_UNIDAD",
                "razon": "variable_sin_identificador",
            }

        filtros = ["a.variable_nva = %s"]
        parametros = [variable_id]
        filtros.extend(resultado_ambito["filtros"])
        parametros.extend(resultado_ambito["parametros"])

        placeholders_niveles = ", ".join(
            ["%s"] * len(niveles_atencion)
        )
        filtros.append(
            f"b.NivelAtencion IN ({placeholders_niveles})"
        )
        parametros.extend(niveles_atencion)

        clausula_where = "\n                  AND ".join(filtros)
        query = f"""
            ;WITH valores_por_unidad AS (
                SELECT
                    b.ClavePresupuestal,
                    b.DenominacionUnidad,
                    b.Region,
                    b.NombreDelegacionUMAE,
                    b.ClaveEntidadFederativa,
                    b.NivelAtencion,
                    SUM(
                        TRY_CONVERT(
                            decimal(18, 2),
                            REPLACE(a.valor, ',', '')
                        )
                    ) AS valor_total
                FROM [DB_Catalogos].[dbo].[Cat_IFU_Actual] a
                INNER JOIN [DB_Catalogos].[dbo].[CUMM_ACTUAL] b
                    ON a.CvePresupuestal = b.ClavePresupuestal
                    COLLATE Modern_Spanish_CI_AS
                WHERE {clausula_where}
                GROUP BY
                    b.ClavePresupuestal,
                    b.DenominacionUnidad,
                    b.Region,
                    b.NombreDelegacionUMAE,
                    b.ClaveEntidadFederativa,
                    b.NivelAtencion
            ),
            clasificados AS (
                SELECT
                    *,
                    DENSE_RANK() OVER (
                        ORDER BY valor_total {orden}
                    ) AS ranking
                FROM valores_por_unidad
                WHERE valor_total IS NOT NULL
            )
            SELECT
                ClavePresupuestal,
                DenominacionUnidad,
                Region,
                NombreDelegacionUMAE,
                ClaveEntidadFederativa,
                NivelAtencion,
                valor_total
            FROM clasificados
            WHERE ranking = 1
            ORDER BY
                DenominacionUnidad,
                ClavePresupuestal
        """

        try:
            with self.conexion.cursor() as cursor:
                cursor.execute(query, parametros)
                filas = cursor.fetchall()
        except Exception as error:
            logger.error(
                "No fue posible consultar el extremo por unidad: %s: %s",
                type(error).__name__,
                error,
            )
            return {
                "status": "error_consulta",
                "tipo_consulta": "EXTREMO_POR_UNIDAD",
                "mensaje": "No fue posible consultar el extremo por unidad.",
            }

        resultados = [
            self._fila_a_resultado_extremo(fila)
            for fila in filas
        ]
        if not resultados:
            return {
                "status": "sin_resultados",
                "tipo_consulta": "EXTREMO_POR_UNIDAD",
                "operacion": operacion,
                "tipo_unidad": tipo_unidad,
                "descripcion_tipo_unidad": plan.get(
                    "descripcion_tipo_unidad"
                ),
                "niveles_atencion": niveles_atencion,
                "ambito": plan.get("ambito"),
                "variable": variable,
                "valor_extremo": None,
                "total_empates": 0,
                "resultados": [],
            }

        return {
            "status": "ok",
            "tipo_consulta": "EXTREMO_POR_UNIDAD",
            "operacion": operacion,
            "tipo_unidad": tipo_unidad,
            "descripcion_tipo_unidad": plan.get(
                "descripcion_tipo_unidad"
            ),
            "niveles_atencion": niveles_atencion,
            "ambito": plan.get("ambito"),
            "variable": variable,
            "valor_extremo": resultados[0]["valor"],
            "total_empates": len(resultados),
            "resultados": resultados,
        }

    def _construir_filtro_ambito(self, ambito, niveles_atencion):
        if not isinstance(ambito, dict):
            return {
                "error": "falta_ambito",
                "filtros": [],
                "parametros": [],
            }

        tipo_ambito = str(ambito.get("tipo") or "").strip().upper()
        if tipo_ambito == "NACIONAL":
            return {
                "error": None,
                "filtros": [],
                "parametros": [],
            }

        if tipo_ambito not in self.COLUMNAS_AMBITO:
            return {
                "error": "ambito_no_soportado",
                "filtros": [],
                "parametros": [],
            }

        if tipo_ambito == "ENTIDAD":
            valor_ambito = self._primer_valor(ambito, "id", "descripcion")
        else:
            valor_ambito = self._primer_valor(ambito, "descripcion", "id")

        if valor_ambito is None:
            return {
                "error": "ambito_sin_valor",
                "filtros": [],
                "parametros": [],
            }

        if tipo_ambito == "NIVEL_ATENCION":
            niveles_comparables = {
                nivel.casefold(): nivel
                for nivel in niveles_atencion
            }
            if str(valor_ambito).strip().casefold() not in niveles_comparables:
                return {
                    "error": "nivel_atencion_contradictorio",
                    "filtros": [],
                    "parametros": [],
                }

            return {
                "error": None,
                "filtros": [],
                "parametros": [],
            }

        columna = self.COLUMNAS_AMBITO[tipo_ambito]
        return {
            "error": None,
            "filtros": [f"{columna} = %s"],
            "parametros": [valor_ambito],
        }

    @staticmethod
    def _normalizar_niveles(niveles):
        if not isinstance(niveles, list):
            return []

        niveles_normalizados = []
        niveles_vistos = set()

        for nivel in niveles:
            if not isinstance(nivel, str):
                continue

            nivel_limpio = nivel.strip()
            if not nivel_limpio:
                continue

            clave = nivel_limpio.casefold()
            if clave in niveles_vistos:
                continue

            niveles_vistos.add(clave)
            niveles_normalizados.append(nivel_limpio)

        return niveles_normalizados

    @staticmethod
    def _primer_valor(datos, *campos):
        for campo in campos:
            valor = datos.get(campo)
            if valor is not None and str(valor).strip() != "":
                return valor
        return None

    @classmethod
    def _obtener_id_variable(cls, variable):
        if not isinstance(variable, dict):
            return None
        return cls._primer_valor(variable, "id", "variable_nva", "clave")

    @staticmethod
    def _serializar_numero(valor):
        if valor is None:
            return None

        numero = float(valor)
        if numero.is_integer():
            return int(numero)
        return numero

    def _fila_a_resultado_extremo(self, fila):
        return {
            "clave_presupuestal": fila[0],
            "denominacion_unidad": fila[1],
            "region": fila[2],
            "delegacion": fila[3],
            "clave_entidad": fila[4],
            "nivel_atencion": fila[5],
            "valor": self._serializar_numero(fila[6]),
        }
