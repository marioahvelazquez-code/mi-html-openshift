#Valida los elementos de la consulta y construye un plan de acción para la misma, regresa planvalido, plan_incompleto, sin_plan o requiere_aclaracion

class PlanificadorConsulta:
    def construir(
        self,
        resultado_operacion,
        resultado_tipo_unidad,
        ambito=None,
        variable=None,
        hospital=None,
    ):
        operacion_detectada = (resultado_operacion or {}).get(
            "operacion",
            "SIN_OPERACION_ANALITICA",
        )
        estado_tipo = (resultado_tipo_unidad or {}).get(
            "status",
            "sin_tipo_unidad",
        )
        (
            tipo_unidad,
            descripcion_tipo_unidad,
            niveles_atencion,
        ) = self._extraer_tipo_unidad(resultado_tipo_unidad)
        ambito_normalizado = self._normalizar_ambito(ambito)
        variable_normalizada = self._normalizar_variable(variable)

        plan = self._crear_plan_base(
            operacion_detectada=operacion_detectada,
            tipo_unidad=tipo_unidad,
            descripcion_tipo_unidad=descripcion_tipo_unidad,
            niveles_atencion=niveles_atencion,
            ambito=ambito_normalizado,
            variable=variable_normalizada,
            hospital=hospital,
        )

        if estado_tipo == "multiple_tipo_unidad":
            plan.update(
                {
                    "status": "requiere_aclaracion",
                    "tipo_consulta": "NO_RESUELTA",
                    "razon": "multiple_tipo_unidad",
                    "operacion": operacion_detectada,
                }
            )
            return plan

        if (
            operacion_detectada == "COUNT"
            and tipo_unidad
            and not variable_normalizada
        ):
            plan.update(
                {
                    "tipo_consulta": "COUNT_UNIDADES",
                    "operacion": "COUNT",
                }
            )
            if not ambito_normalizado:
                plan.update(
                    {
                        "status": "plan_incompleto",
                        "razon": "falta_ambito",
                    }
                )
                return plan

            plan["status"] = "plan_valido"
            return plan

        if operacion_detectada in {"MAX", "MIN"} and tipo_unidad:
            plan.update(
                {
                    "tipo_consulta": "EXTREMO_POR_UNIDAD",
                    "operacion": operacion_detectada,
                }
            )
            if not variable_normalizada:
                plan.update(
                    {
                        "status": "plan_incompleto",
                        "razon": "falta_variable",
                    }
                )
                return plan

            if not ambito_normalizado:
                plan.update(
                    {
                        "status": "plan_incompleto",
                        "razon": "falta_ambito",
                    }
                )
                return plan

            plan["status"] = "plan_valido"
            return plan

        if (
            operacion_detectada in {"MAX", "MIN"}
            and variable_normalizada
            and not tipo_unidad
        ):
            plan.update(
                {
                    "status": "plan_incompleto",
                    "tipo_consulta": "EXTREMO_POR_UNIDAD",
                    "razon": "falta_tipo_unidad",
                    "operacion": operacion_detectada,
                }
            )
            return plan

        if variable_normalizada:
            plan.update(
                {
                    "status": "plan_valido",
                    "tipo_consulta": "CONSULTA_IFU",
                    "operacion": "VALOR" if hospital else "SUM",
                }
            )
            return plan

        plan.update(
            {
                "status": "sin_plan",
                "tipo_consulta": "NO_RESUELTA",
                "razon": "sin_elementos_suficientes",
            }
        )
        return plan

    @classmethod
    def _normalizar_ambito(cls, ambito):
        if not isinstance(ambito, dict):
            return None

        tipo = cls._primer_valor(ambito, "tipo", "tipo_ambito")
        identificador = cls._primer_valor(ambito, "id", "filtro_id")
        descripcion = cls._primer_valor(
            ambito,
            "descripcion",
            "nombre",
            "desc_original",
            "desc_normalizada",
            "texto_usado",
        )

        if tipo is None or identificador is None:
            return None

        return {
            "tipo": str(tipo).upper(),
            "id": identificador,
            "descripcion": descripcion,
        }

    @classmethod
    def _normalizar_variable(cls, variable):
        if not isinstance(variable, dict):
            return None

        variable_interna = variable.get("variable")
        if isinstance(variable_interna, dict):
            variable = variable_interna

        identificador = cls._primer_valor(variable, "id", "variable_nva")
        if identificador is None:
            return None

        descripcion = cls._primer_valor(
            variable,
            "descripcion",
            "desc_original",
            "desc_normalizada",
        )

        return {
            "id": identificador,
            "descripcion": str(descripcion or ""),
        }

    @staticmethod
    def _extraer_tipo_unidad(resultado_tipo_unidad):
        resultado = resultado_tipo_unidad or {}
        if resultado.get("status") != "ganador_claro":
            return None, None, []

        tipo_unidad = resultado.get("tipo_unidad")
        if not tipo_unidad:
            return None, None, []

        return (
            tipo_unidad,
            resultado.get("descripcion"),
            list(resultado.get("niveles_atencion") or []),
        )

    @staticmethod
    def _crear_plan_base(
        operacion_detectada,
        tipo_unidad,
        descripcion_tipo_unidad,
        niveles_atencion,
        ambito,
        variable,
        hospital,
    ):
        return {
            "status": "sin_plan",
            "tipo_consulta": "NO_RESUELTA",
            "razon": None,
            "operacion": None,
            "operacion_detectada": operacion_detectada,
            "tipo_unidad": tipo_unidad,
            "descripcion_tipo_unidad": descripcion_tipo_unidad,
            "niveles_atencion": list(niveles_atencion),
            "ambito": ambito,
            "variable": variable,
            "hospital": hospital,
        }

    @staticmethod
    def _primer_valor(datos, *campos):
        for campo in campos:
            valor = datos.get(campo)
            if valor is not None and valor != "":
                return valor
        return None
