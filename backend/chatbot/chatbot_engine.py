from .consulta_ifu import ConsultaIFU 
from .consulta_analitica import ConsultaAnalitica
from .buscador_hospital import BuscadorHospital
from .buscador_variable import BuscadorVariable
from .catalogos import catalogos
from .constantes import VARIABLES_CANONICAS
from .detector_operacion import DetectorOperacion
from .detector_tipo_unidad import DetectorTipoUnidad
from .normalizador import normalizar_texto_completo
from .buscador_ambito import BuscadorAmbito
from .planificador_consulta import PlanificadorConsulta


class ChatbotEngine:
    MAX_RESULTADOS_EN_MENSAJE = 10
    MENSAJE_CONVERSACION_FINALIZADA = (
        "¡Con gusto! He cerrado la conversación y limpiado el contexto. "
        "Puedes iniciar una nueva consulta cuando quieras."
    )
    DESPEDIDAS_EXACTAS = {
        "gracias",
        "muchas gracias",
        "adios",
        "gracias por la ayuda",
        "muchas gracias por la ayuda",
        "grax",
        "eso es todo",
        "es todo",
        "seria todo",
        "ya es todo",
        "fin",
        "terminar",
        "terminamos",
        "listo gracias",
        "ok gracias",
        "perfecto gracias",
        "eso es todo gracias",
    }

    CONECTORES_SIN_VARIABLE = {
        "y",
        "e",
        "en",
        "de",
        "del",
        "la",
        "el",
        "los",
        "las",
        "por",
        "para",
        "con",
        "ahora",
    }
    TERMINOS_CONSULTA = {
        "cama",
        "camas",
        "censable",
        "censables",
        "consultorio",
        "consultorios",
        "unidad",
        "unidades",
        "variable",
        "variables",
        "total",
        "totales",
        "cuanto",
        "cuantos",
        "cuanta",
        "cuantas",
        "hay",
        "tiene",
        "tienen",
        "dame",
        "muestra",
        "consulta",
        "urgencias",
        "cirugia",
        "medicina",
        "pediatria",
        "ginecologia",
        "obstetricia",
        "terapia",
        "intensiva",
        "no",
    }
    TERMINOS_HOSPITAL = {
        "hospital",
        "hgz",
        "hgr",
        "hgzmf",
        "umf",
        "umae",
        "cmn",
        "hgo",
        "hes",
        "hc",
        "hp",
        "honco",
    }
    INDICADORES_UNIDAD_PUNTUAL = {
        "hgz",
        "hgr",
        "hgzmf",
        "umf",
        "umae",
        "cmn",
        "hgo",
        "hes",
        "hc",
        "hp",
        "honco",
    }
    MENSAJE_SIN_INTENCION = (
        "No entendí tu pregunta. Por favor intenta escribir una unidad médica, "
        "una variable o una consulta del IFU."
    )

    def __init__(self):
        self.buscador_ambito = BuscadorAmbito(catalogos)
        self.buscador_hospital = BuscadorHospital(catalogos)
        self.buscador_variable = BuscadorVariable(catalogos)
        self.consulta_ifu = ConsultaIFU()
        self.detector_operacion = DetectorOperacion()
        self.detector_tipo_unidad = DetectorTipoUnidad()
        self.planificador_consulta = PlanificadorConsulta()
        self.consulta_analitica = ConsultaAnalitica()
        self.tokens_catalogo_variables = self._crear_tokens_catalogo_variables()
        self.tokens_catalogo_hospitales = self._crear_tokens_catalogo_hospitales()

    def procesar(self, pregunta_usuario, contexto=None):
        contexto = contexto if isinstance(contexto, dict) else {}
        hospital_contexto = contexto.get("hospital")
        variable_contexto = contexto.get("variable")
        hospital_confirmado = bool(contexto.get("hospitalConfirmadoPorUsuario"))
        variable_confirmada = bool(contexto.get("variableConfirmadaPorUsuario"))

        print("[chatbot] pregunta recibida:", pregunta_usuario, flush=True)
        print("[chatbot] contexto recibido:", contexto, flush=True)
        print("[chatbot] hospital confirmado por usuario:", hospital_confirmado, flush=True)
        print("[chatbot] variable confirmada por usuario:", variable_confirmada, flush=True)

        pregunta_normalizada = normalizar_texto_completo(pregunta_usuario)
        resultado_operacion = self.detector_operacion.detectar(pregunta_usuario)
        resultado_tipo_unidad = self.detector_tipo_unidad.detectar(
            pregunta_usuario
        )
        if (
            self._es_despedida(pregunta_normalizada)
            and not self._contiene_consulta_relevante(
                pregunta_normalizada,
                resultado_operacion,
                resultado_tipo_unidad,
            )
        ):
            print("[chatbot] conversacion_finalizada: True", flush=True)
            print("[chatbot] se_consulta_sql:", False, flush=True)
            return self._crear_respuesta_conversacion_finalizada(
                pregunta_usuario
            )

        # Detecta si la consulta usa un hospital o un ámbito general.
        ambito_detectado = self.buscador_ambito.buscar(pregunta_normalizada)
        resultado_operacion, resultado_tipo_unidad = (
            self._aplicar_contexto_analitico_pendiente(
                contexto,
                ambito_detectado,
                resultado_operacion,
                resultado_tipo_unidad,
            )
        )
        resultado_operacion, resultado_tipo_unidad = (
            self._aplicar_continuidad_ultima_consulta_analitica(
                contexto,
                ambito_detectado,
                resultado_operacion,
                resultado_tipo_unidad,
            )
        )
        print(
            "[chatbot][analitica] operacion:",
            resultado_operacion,
            flush=True,
        )
        print(
            "[chatbot][analitica] tipo unidad:",
            resultado_tipo_unidad,
            flush=True,
        )
        tiene_indicio_unidad_puntual = bool(
            set(pregunta_normalizada.split()) & self.INDICADORES_UNIDAD_PUNTUAL
        )
        es_ambito_macro = (
            ambito_detectado["tipo"] != "HOSPITAL"
            and not hospital_confirmado
            and not tiene_indicio_unidad_puntual
        )


        tiene_intencion, razon_sin_intencion = self._tiene_intencion_consulta(
            pregunta_normalizada,
            hospital_confirmado=hospital_confirmado,
            variable_confirmada=variable_confirmada,
        )
        es_continuacion_count_valida = (
            self._es_continuacion_count_valida(
                contexto,
                resultado_operacion,
                resultado_tipo_unidad,
            )
        )
        if not tiene_intencion and es_continuacion_count_valida:
            tiene_intencion = True
            razon_sin_intencion = (
                "continuacion analitica COUNT_UNIDADES valida"
            )
        if (
            not tiene_intencion
            and ambito_detectado.get("tipo") != "HOSPITAL"
        ):
            tiene_intencion = True
            razon_sin_intencion = "ambito detectado en pregunta de seguimiento"
        print("[chatbot] pregunta normalizada:", pregunta_normalizada, flush=True)
        print("[chatbot] tiene_intencion_consulta:", tiene_intencion, flush=True)
        print("[chatbot] razon_si_no_hay_intencion:", razon_sin_intencion, flush=True)

        if not tiene_intencion:
            print("[chatbot] contexto_conservado:", contexto, flush=True)
            print("[chatbot] se_consulta_sql:", False, flush=True)
            return {
                "ok": False,
                "status": "sin_intencion",
                "mensaje": self.MENSAJE_SIN_INTENCION,
                "pregunta_original": pregunta_usuario,
                "contexto": contexto,
                "hospital": {
                    "status": "sin_intencion",
                    "hospital": hospital_contexto,
                    "score": 0.0,
                    "texto_usado": pregunta_normalizada,
                },
                "variable": {
                    "status": "sin_intencion",
                    "variable": variable_contexto,
                    "score": 0.0,
                    "texto_usado": pregunta_normalizada,
                },
                "datos": [],
            }

        hospital_detectado = None
        resultado_hospital_texto = {
            "status": "sin_texto",
            "hospital": None,
            "score": 0.0,
            "texto_usado": "",
        }

        if es_ambito_macro:
            resultado_hospital = {
                "status": "ganador_claro",
                "hospital": None,
                "ambito_macro": ambito_detectado,
                "score": 1.0,
                "texto_usado": ambito_detectado.get("texto_usado", ""),
            }
        else:
            resultado_hospital_texto = self.buscador_hospital.buscar(pregunta_usuario)

            if hospital_confirmado and hospital_contexto:
                hospital_detectado = self._normalizar_hospital_contexto(hospital_contexto)
                resultado_hospital = {
                    "status": "ganador_claro",
                    "hospital": hospital_detectado,
                    "score": 1.0,
                    "texto_usado": hospital_detectado.get("nombre_original", ""),
                }
            elif resultado_hospital_texto["status"] == "ganador_claro":
                hospital_detectado = resultado_hospital_texto["hospital"]
                resultado_hospital = resultado_hospital_texto
            elif resultado_hospital_texto["status"] == "empate_tecnico":
                resultado_hospital = resultado_hospital_texto
            elif hospital_contexto:
                hospital_detectado = self._normalizar_hospital_contexto(hospital_contexto)
                resultado_hospital = {
                    "status": "ganador_claro",
                    "hospital": hospital_detectado,
                    "score": 1.0,
                    "texto_usado": hospital_detectado.get("nombre_original", ""),
                }
            else:
                resultado_hospital = resultado_hospital_texto

        texto_variable_limpio = self.buscador_variable._preparar_texto(
            pregunta_usuario,
            hospital_detectado,
        )
        se_busca_variable_desde_texto, razon_no_buscar_variable = (
            self._debe_buscar_variable_desde_texto(texto_variable_limpio)
        )
        if variable_confirmada:
            se_busca_variable_desde_texto = False
            razon_no_buscar_variable = "variable confirmada por usuario"

        print("[chatbot] texto_variable_limpio:", texto_variable_limpio, flush=True)
        print(
            "[chatbot] se_busca_variable_desde_texto:",
            se_busca_variable_desde_texto,
            flush=True,
        )
        print(
            "[chatbot] razon_si_no_se_busca_variable:",
            razon_no_buscar_variable,
            flush=True,
        )

        resultado_variable_texto = {
            "status": "sin_texto",
            "variable": None,
            "score": 0.0,
            "texto_usado": texto_variable_limpio,
        }

        if se_busca_variable_desde_texto:
            resultado_variable_texto = self.buscador_variable.buscar(
                pregunta_usuario,
                hospital_detectado,
            )

        if variable_confirmada and variable_contexto:
            variable_detectada = self._normalizar_variable_contexto(variable_contexto)
            resultado_variable = {
                "status": "ganador_claro",
                "variable": variable_detectada,
                "score": 1.0,
                "texto_usado": variable_detectada.get("descripcion", ""),
            }
        elif resultado_variable_texto["status"] == "ganador_claro":
            resultado_variable = resultado_variable_texto
        elif resultado_variable_texto["status"] == "empate_tecnico":
            resultado_variable = resultado_variable_texto
        elif variable_contexto:
            variable_detectada = self._normalizar_variable_contexto(variable_contexto)
            resultado_variable = {
                "status": "ganador_claro",
                "variable": variable_detectada,
                "score": 1.0,
                "texto_usado": variable_detectada.get("descripcion", ""),
            }
        else:
            resultado_variable = resultado_variable_texto

        ambito_para_plan = self._preparar_ambito_para_planificador(
            ambito_detectado
        )
        if not ambito_para_plan:
            ambito_para_plan = self._preparar_ambito_para_planificador(
                contexto.get("ambito")
            )

        variable_para_plan = None
        if variable_confirmada and variable_contexto:
            variable_para_plan = self._normalizar_variable_contexto(
                variable_contexto
            )
        elif resultado_variable_texto.get("status") == "ganador_claro":
            variable_para_plan = resultado_variable_texto.get("variable")
        else:
            pendiente = contexto.get("consultaAnaliticaPendiente")
            if isinstance(pendiente, dict):
                variable_para_plan = pendiente.get("variable")

        hospital_para_plan = None
        if hospital_confirmado and hospital_contexto:
            hospital_para_plan = self._normalizar_hospital_contexto(
                hospital_contexto
            )
        elif resultado_hospital_texto.get("status") == "ganador_claro":
            hospital_para_plan = resultado_hospital_texto.get("hospital")

        plan_consulta = self.planificador_consulta.construir(
            resultado_operacion=resultado_operacion,
            resultado_tipo_unidad=resultado_tipo_unidad,
            ambito=ambito_para_plan,
            variable=variable_para_plan,
            hospital=hospital_para_plan,
        )
        print(
            "[chatbot][analitica] plan:",
            plan_consulta,
            flush=True,
        )
        print(
            "[chatbot][analitica] tipo_consulta/operacion:",
            plan_consulta.get("tipo_consulta"),
            plan_consulta.get("operacion"),
            flush=True,
        )

        es_count_unidades = (
            plan_consulta.get("status") == "plan_valido"
            and plan_consulta.get("tipo_consulta") == "COUNT_UNIDADES"
        )
        if es_count_unidades:
            resultado_analitico = self.consulta_analitica.ejecutar_plan(
                plan_consulta
            )
            contexto_analitico = self._crear_contexto_analitico(
                contexto,
                plan_consulta,
                completada=resultado_analitico.get("status") == "ok",
            )
            if resultado_analitico.get("status") == "ok":
                return self._crear_respuesta_count_unidades(
                    pregunta_usuario,
                    contexto_analitico,
                    resultado_analitico,
                )

            return self._crear_respuesta_analitica_base(
                pregunta_usuario=pregunta_usuario,
                contexto=contexto_analitico,
                status="error_consulta",
                mensaje=(
                    "No fue posible realizar el conteo de unidades en este momento."
                ),
                ok=False,
                tipo_consulta="COUNT_UNIDADES",
                tipo_unidad=plan_consulta.get("tipo_unidad"),
                ambito=plan_consulta.get("ambito"),
            )

        es_extremo_por_unidad = (
            plan_consulta.get("status") == "plan_valido"
            and plan_consulta.get("tipo_consulta")
            == "EXTREMO_POR_UNIDAD"
            and plan_consulta.get("operacion") in {"MAX", "MIN"}
            and bool(plan_consulta.get("tipo_unidad"))
            and bool(plan_consulta.get("niveles_atencion"))
            and bool(plan_consulta.get("variable"))
            and bool(plan_consulta.get("ambito"))
        )
        if es_extremo_por_unidad:
            print(
                "[chatbot][analitica] ejecutando extremo:",
                {
                    "tipo_unidad": plan_consulta.get("tipo_unidad"),
                    "ambito": plan_consulta.get("ambito"),
                    "variable_id": (
                        plan_consulta.get("variable") or {}
                    ).get("id"),
                },
                flush=True,
            )
            resultado_analitico = self.consulta_analitica.ejecutar_plan(
                plan_consulta
            )
            print(
                "[chatbot][analitica] resultado extremo:",
                {
                    "status": resultado_analitico.get("status"),
                    "valor_extremo": resultado_analitico.get(
                        "valor_extremo"
                    ),
                    "total_empates": resultado_analitico.get(
                        "total_empates"
                    ),
                },
                flush=True,
            )
            contexto_analitico = self._crear_contexto_analitico(
                contexto,
                plan_consulta,
                completada=resultado_analitico.get("status")
                in {"ok", "sin_resultados"},
            )
            if resultado_analitico.get("status") in {
                "ok",
                "sin_resultados",
            }:
                return self._crear_respuesta_extremo_por_unidad(
                    pregunta_usuario,
                    contexto_analitico,
                    resultado_analitico,
                )

            return self._crear_respuesta_analitica_base(
                pregunta_usuario=pregunta_usuario,
                contexto=contexto_analitico,
                status="error_consulta",
                mensaje=(
                    "No fue posible realizar la consulta de máximo o mínimo "
                    "en este momento."
                ),
                ok=False,
                tipo_consulta="EXTREMO_POR_UNIDAD",
                tipo_unidad=plan_consulta.get("tipo_unidad"),
                ambito=plan_consulta.get("ambito"),
            )

        if (
            plan_consulta.get("tipo_consulta") == "EXTREMO_POR_UNIDAD"
            and plan_consulta.get("status") == "plan_incompleto"
        ):
            razon_plan = plan_consulta.get("razon")
            contexto_analitico = self._crear_contexto_analitico(
                contexto,
                plan_consulta,
                pendiente=True,
            )
            variable_ambigua = (
                razon_plan == "falta_variable"
                and resultado_variable.get("status")
                in {"empate_tecnico", "baja_confianza"}
                and bool(resultado_variable.get("candidatos"))
            )
            if variable_ambigua:
                contexto = contexto_analitico
            elif razon_plan == "falta_variable":
                return self._crear_respuesta_analitica_base(
                    pregunta_usuario=pregunta_usuario,
                    contexto=contexto_analitico,
                    status="falta_variable",
                    mensaje=self._crear_mensaje_falta_variable_extremo(
                        plan_consulta
                    ),
                    tipo_consulta="EXTREMO_POR_UNIDAD",
                    tipo_unidad=plan_consulta.get("tipo_unidad"),
                    ambito=plan_consulta.get("ambito"),
                )
            elif razon_plan == "falta_ambito":
                return self._crear_respuesta_analitica_base(
                    pregunta_usuario=pregunta_usuario,
                    contexto=contexto_analitico,
                    status="falta_ambito",
                    mensaje=self._crear_mensaje_falta_ambito_extremo(
                        plan_consulta
                    ),
                    tipo_consulta="EXTREMO_POR_UNIDAD",
                    tipo_unidad=plan_consulta.get("tipo_unidad"),
                    ambito=None,
                )

        if (
            plan_consulta.get("tipo_consulta") == "COUNT_UNIDADES"
            and plan_consulta.get("status") == "plan_incompleto"
            and plan_consulta.get("razon") == "falta_ambito"
        ):
            contexto_analitico = self._crear_contexto_analitico(
                contexto,
                plan_consulta,
                pendiente=True,
            )
            return self._crear_respuesta_analitica_base(
                pregunta_usuario=pregunta_usuario,
                contexto=contexto_analitico,
                status="falta_ambito",
                mensaje=self._crear_mensaje_falta_ambito_count_unidades(
                    plan_consulta.get("tipo_unidad")
                ),
                tipo_consulta="COUNT_UNIDADES",
                tipo_unidad=plan_consulta.get("tipo_unidad"),
                ambito=None,
            )

        if (
            resultado_operacion.get("operacion") == "COUNT"
            and plan_consulta.get("status") == "requiere_aclaracion"
            and plan_consulta.get("razon") == "multiple_tipo_unidad"
        ):
            contexto_analitico = self._crear_contexto_analitico(
                contexto,
                plan_consulta,
            )
            return self._crear_respuesta_analitica_base(
                pregunta_usuario=pregunta_usuario,
                contexto=contexto_analitico,
                status="requiere_aclaracion",
                mensaje=(
                    "Detecté dos tipos de unidad. ¿Deseas contar unidades de "
                    "medicina familiar o hospitales?"
                ),
                tipo_consulta="COUNT_UNIDADES",
                tipo_unidad=None,
                ambito=plan_consulta.get("ambito"),
            )

        if (
            resultado_operacion.get("operacion") in {"MAX", "MIN"}
            and plan_consulta.get("status") == "requiere_aclaracion"
            and plan_consulta.get("razon") == "multiple_tipo_unidad"
        ):
            plan_pendiente = {
                **plan_consulta,
                "tipo_consulta": "EXTREMO_POR_UNIDAD",
            }
            contexto_analitico = self._crear_contexto_analitico(
                contexto,
                plan_pendiente,
                pendiente=True,
            )
            return self._crear_respuesta_analitica_base(
                pregunta_usuario=pregunta_usuario,
                contexto=contexto_analitico,
                status="requiere_aclaracion",
                mensaje=(
                    "Detecté unidades de medicina familiar y hospitales. "
                    "¿Qué tipo de unidad deseas comparar?"
                ),
                tipo_consulta="EXTREMO_POR_UNIDAD",
                tipo_unidad=None,
                ambito=plan_consulta.get("ambito"),
            )

        variable_final_usada = (
            resultado_variable["variable"]["id"]
            if resultado_variable["status"] == "ganador_claro"
            and resultado_variable.get("variable")
            else None
        )
        print("[chatbot] variable_final_usada:", variable_final_usada, flush=True)

        hospital_contexto_final = hospital_contexto
        ambito_contexto_final = (
            ambito_detectado
            if es_ambito_macro
            else contexto.get("ambito")
        )
        if es_ambito_macro:
            hospital_contexto_final = None
        elif (
            resultado_hospital["status"] == "ganador_claro"
            and resultado_hospital.get("hospital")
        ):
            hospital_contexto_final = resultado_hospital["hospital"]
            ambito_contexto_final = None

        if resultado_variable["status"] == "ganador_claro":
            variable_contexto_final = resultado_variable["variable"]
        elif se_busca_variable_desde_texto and resultado_variable["status"] == "empate_tecnico":
            variable_contexto_final = None
        else:
            variable_contexto_final = variable_contexto

        contexto_final = {
            **contexto,
            "hospital": hospital_contexto_final,
            "ambito": ambito_contexto_final,
            "variable": variable_contexto_final,
            "hospitalConfirmadoPorUsuario": False,
            "variableConfirmadaPorUsuario": False,
        }

        print("[chatbot] hospital detectado desde texto:", resultado_hospital_texto, flush=True)
        print("[chatbot] variable detectada desde texto:", resultado_variable_texto, flush=True)
        print("[chatbot] contexto final fusionado:", contexto_final, flush=True)

        datos = []
        se_consulta_sql = False
        hospital_final = contexto_final.get("hospital")
        ambito_final = contexto_final.get("ambito")
        variable_final = contexto_final.get("variable")

        print("[chatbot] ambito_detectado_desde_texto:", ambito_detectado, flush=True)
        print("[chatbot] variable_previa_contexto:", variable_contexto, flush=True)
        print("[chatbot] variable_final_resuelta:", variable_final, flush=True)
        print("[chatbot] ambito_final_resuelto:", ambito_final, flush=True)
        print("[chatbot] hospital_final_resuelto:", hospital_final, flush=True)

        hay_candidatos_variable = bool(
            resultado_variable
            and resultado_variable.get("status")
            in {"empate_tecnico", "baja_confianza"}
            and resultado_variable.get("candidatos")
        )
        hay_candidatos_hospital = bool(
            resultado_hospital
            and resultado_hospital.get("status") in {"empate_tecnico", "varias_opciones"}
            and resultado_hospital.get("candidatos")
        )
        print("[chatbot] status_busqueda_variable:", resultado_variable.get("status"), flush=True)
        print("[chatbot] candidatos_variable:", resultado_variable.get("candidatos", []), flush=True)
        print("[chatbot] hay_candidatos_variable:", hay_candidatos_variable, flush=True)
        print("[chatbot] hay_candidatos_hospital:", hay_candidatos_hospital, flush=True)
        print("[chatbot] texto_variable_actual_tiene_prioridad:", se_busca_variable_desde_texto, flush=True)

        if hay_candidatos_variable or hay_candidatos_hospital:
            mensaje = self._mensaje_varias_opciones(
                hay_candidatos_variable=hay_candidatos_variable,
                hay_candidatos_hospital=hay_candidatos_hospital,
                ambito=ambito_final,
                hospital=hospital_final,
            )
            print("[chatbot] status_respuesta:", "varias_opciones", flush=True)
            print("[chatbot] requiere_confirmacion:", True, flush=True)
            print("[chatbot] se_consulta_sql:", False, flush=True)
            return {
                "status": "varias_opciones",
                "mensaje": mensaje,
                "requiereConfirmacion": True,
                "pregunta_original": pregunta_usuario,
                "contexto": contexto_final,
                "hospital": resultado_hospital,
                "variable": resultado_variable,
                "datos": datos,
            }

        if ambito_final and not variable_final:
            mensaje = (
                f"Detecté {self._descripcion_ambito(ambito_final)}, "
                "pero necesito saber qué variable quieres consultar."
            )
            print("[chatbot] status_respuesta:", "falta_variable", flush=True)
            print("[chatbot] requiere_confirmacion:", False, flush=True)
            print("[chatbot] se_consulta_sql:", False, flush=True)
            return {
                "status": "falta_variable",
                "mensaje": mensaje,
                "requiereConfirmacion": False,
                "pregunta_original": pregunta_usuario,
                "contexto": contexto_final,
                "hospital": resultado_hospital,
                "variable": resultado_variable,
                "datos": datos,
            }

        if variable_final and not hospital_final and not ambito_final:
            mensaje = (
                f"Detecté la variable {self._descripcion_variable(variable_final)}, "
                "pero necesito saber para qué hospital, entidad, región, delegación o nivel quieres consultar."
            )
            print("[chatbot] status_respuesta:", "falta_ambito", flush=True)
            print("[chatbot] requiere_confirmacion:", False, flush=True)
            print("[chatbot] se_consulta_sql:", False, flush=True)
            return {
                "status": "falta_ambito",
                "mensaje": mensaje,
                "requiereConfirmacion": False,
                "pregunta_original": pregunta_usuario,
                "contexto": contexto_final,
                "hospital": resultado_hospital,
                "variable": resultado_variable,
                "datos": datos,
            }

        puede_consultar_hospital = (
            resultado_variable["status"] == "ganador_claro"
            and variable_final
            and hospital_final
            and not ambito_final
        )
        puede_consultar_ambito = (
            resultado_variable["status"] == "ganador_claro"
            and variable_final
            and ambito_final
            and not hospital_final
        )
        if (
            puede_consultar_hospital or puede_consultar_ambito
        ):
            clave_unidad = hospital_final["id"] if puede_consultar_hospital else None
            variable_id = variable_final["id"]
            print("[chatbot] variable final usada para SQL:", variable_id, flush=True)
            se_consulta_sql = True

            if puede_consultar_ambito:
                datos = self.consulta_ifu.obtener_valor_dinamico(
                    tipo_ambito=ambito_final["tipo"],
                    filtro_id=ambito_final["id"],
                    variable_id=variable_id,
                )
            else:
                datos = self.consulta_ifu.obtener_valor(
                    clave_unidad=clave_unidad,
                    variable_id=variable_id
                )
                   
        print("[chatbot] status_respuesta:", "ok", flush=True)
        print("[chatbot] requiere_confirmacion:", self._requiere_confirmacion(resultado_hospital, resultado_variable), flush=True)
        print("[chatbot] se_consulta_sql:", se_consulta_sql, flush=True)
        return {
            "pregunta_original": pregunta_usuario,
            "contexto": contexto_final,
            "hospital": resultado_hospital,
            "variable": resultado_variable,
            "datos": datos,
            "requiereConfirmacion": self._requiere_confirmacion(resultado_hospital, resultado_variable),
        }

    def _preparar_ambito_para_planificador(self, resultado_ambito):
        if not isinstance(resultado_ambito, dict):
            return None

        tipo = resultado_ambito.get("tipo") or resultado_ambito.get(
            "tipo_ambito"
        )
        identificador = resultado_ambito.get("id")
        if identificador is None:
            identificador = resultado_ambito.get("filtro_id")

        if not tipo or str(tipo).upper() == "HOSPITAL":
            return None
        if identificador is None:
            return None

        descripcion = (
            resultado_ambito.get("descripcion")
            or resultado_ambito.get("nombre")
            or resultado_ambito.get("desc_original")
            or resultado_ambito.get("desc_normalizada")
            or resultado_ambito.get("texto_usado")
        )
        return {
            "tipo": str(tipo).upper(),
            "id": identificador,
            "descripcion": descripcion,
        }

    def _aplicar_contexto_analitico_pendiente(
        self,
        contexto,
        ambito_detectado,
        resultado_operacion,
        resultado_tipo_unidad,
    ):
        pendiente = contexto.get("consultaAnaliticaPendiente")
        if (
            not isinstance(pendiente, dict)
            or pendiente.get("tipoConsulta")
            not in {"COUNT_UNIDADES", "EXTREMO_POR_UNIDAD"}
        ):
            return resultado_operacion, resultado_tipo_unidad

        if resultado_operacion.get("operacion") == "SIN_OPERACION_ANALITICA":
            operacion_pendiente = pendiente.get("operacion")
            if pendiente.get("tipoConsulta") == "COUNT_UNIDADES":
                operacion_pendiente = "COUNT"
            resultado_operacion = {
                **resultado_operacion,
                "operacion": operacion_pendiente,
                "termino_detectado": None,
                "confianza": 1.0,
            }

        if resultado_tipo_unidad.get("status") == "sin_tipo_unidad":
            tipo_unidad = pendiente.get("tipoUnidad")
            if tipo_unidad:
                resultado_tipo_unidad = {
                    **resultado_tipo_unidad,
                    "status": "ganador_claro",
                    "tipo_unidad": tipo_unidad,
                    "descripcion": pendiente.get("descripcionTipoUnidad"),
                    "niveles_atencion": list(
                        pendiente.get("nivelesAtencion") or []
                    ),
                    "termino_detectado": None,
                    "confianza": 1.0,
                }

        return resultado_operacion, resultado_tipo_unidad

    def _aplicar_continuidad_ultima_consulta_analitica(
        self,
        contexto,
        ambito_detectado,
        resultado_operacion,
        resultado_tipo_unidad,
    ):
        if isinstance(contexto.get("consultaAnaliticaPendiente"), dict):
            return resultado_operacion, resultado_tipo_unidad

        ultima_consulta = contexto.get("ultimaConsultaAnalitica")
        if (
            not isinstance(ultima_consulta, dict)
            or ultima_consulta.get("tipoConsulta") != "COUNT_UNIDADES"
        ):
            return resultado_operacion, resultado_tipo_unidad

        ambito_explicito = (
            isinstance(ambito_detectado, dict)
            and ambito_detectado.get("tipo") != "HOSPITAL"
        )
        tipo_unidad_explicito = (
            resultado_tipo_unidad.get("status") == "ganador_claro"
            and bool(resultado_tipo_unidad.get("tipo_unidad"))
        )
        if not ambito_explicito and not tipo_unidad_explicito:
            return resultado_operacion, resultado_tipo_unidad

        if (
            resultado_operacion.get("operacion")
            == "SIN_OPERACION_ANALITICA"
        ):
            resultado_operacion = {
                **resultado_operacion,
                "operacion": "COUNT",
                "termino_detectado": None,
                "confianza": 1.0,
            }

        if (
            resultado_operacion.get("operacion") == "COUNT"
            and resultado_tipo_unidad.get("status") == "sin_tipo_unidad"
        ):
            tipo_unidad = ultima_consulta.get("tipoUnidad")
            if tipo_unidad:
                resultado_tipo_unidad = {
                    **resultado_tipo_unidad,
                    "status": "ganador_claro",
                    "tipo_unidad": tipo_unidad,
                    "descripcion": (
                        ultima_consulta.get("descripcionTipoUnidad")
                        or tipo_unidad
                    ),
                    "niveles_atencion": list(
                        ultima_consulta.get("nivelesAtencion") or []
                    ),
                    "termino_detectado": None,
                    "confianza": 1.0,
                }

        return resultado_operacion, resultado_tipo_unidad

    def _es_continuacion_count_valida(
        self,
        contexto,
        resultado_operacion,
        resultado_tipo_unidad,
    ):
        ultima_consulta = contexto.get("ultimaConsultaAnalitica")
        return bool(
            isinstance(ultima_consulta, dict)
            and ultima_consulta.get("tipoConsulta") == "COUNT_UNIDADES"
            and resultado_operacion.get("operacion") == "COUNT"
            and resultado_tipo_unidad.get("status") == "ganador_claro"
            and resultado_tipo_unidad.get("tipo_unidad")
            and resultado_tipo_unidad.get("termino_detectado")
        )

    def _es_despedida(self, pregunta_normalizada):
        texto = (pregunta_normalizada or "").strip()
        if texto in self.DESPEDIDAS_EXACTAS:
            return True

        tokens = texto.split()
        if not ({"gracias", "grax"} & set(tokens)):
            return False

        tokens_cortesia = {
            "gracias",
            "grax",
            "muchas",
            "por",
            "la",
            "ayuda",
            "eso",
            "es",
            "todo",
            "ya",
            "seria",
            "listo",
            "ok",
            "perfecto",
        }
        return not any(token not in tokens_cortesia for token in tokens)

    def _contiene_consulta_relevante(
        self,
        pregunta_normalizada,
        resultado_operacion,
        resultado_tipo_unidad,
    ):
        tiene_intencion_textual, _ = self._tiene_intencion_consulta(
            pregunta_normalizada
        )
        return bool(
            tiene_intencion_textual
            or resultado_operacion.get("operacion")
            != "SIN_OPERACION_ANALITICA"
            or resultado_tipo_unidad.get("status") == "ganador_claro"
        )

    def _crear_respuesta_conversacion_finalizada(self, pregunta_usuario):
        contexto_limpio = {
            "hospital": None,
            "variable": None,
            "ambito": None,
            "hospitalConfirmadoPorUsuario": False,
            "variableConfirmadaPorUsuario": False,
            "ultimaConsultaAnalitica": None,
            "consultaAnaliticaPendiente": None,
            "operacion": None,
            "tipoUnidad": None,
            "resultadoAnalitico": None,
            "candidatos": None,
            "seleccionesPendientes": None,
        }
        return {
            "ok": True,
            "status": "conversacion_finalizada",
            "mensaje": self.MENSAJE_CONVERSACION_FINALIZADA,
            "pregunta_original": pregunta_usuario,
            "resetConversacion": True,
            "contexto": contexto_limpio,
            "hospital": {
                "status": "sin_texto",
                "hospital": None,
                "score": 0.0,
                "texto_usado": "",
            },
            "variable": {
                "status": "sin_texto",
                "variable": None,
                "score": 0.0,
                "texto_usado": "",
            },
            "datos": [],
            "requiereConfirmacion": False,
        }

    def _crear_contexto_analitico(
        self,
        contexto,
        plan,
        pendiente=False,
        completada=False,
    ):
        contexto_analitico = {
            **contexto,
            "hospital": contexto.get("hospital"),
            "variable": contexto.get("variable"),
            "hospitalConfirmadoPorUsuario": False,
            "variableConfirmadaPorUsuario": False,
        }

        es_count_unidades = plan.get("tipo_consulta") == "COUNT_UNIDADES"
        if es_count_unidades:
            contexto_analitico["hospital"] = None
            contexto_analitico["variable"] = None

        if plan.get("ambito"):
            contexto_analitico["ambito"] = plan["ambito"]

        if pendiente:
            contexto_analitico["consultaAnaliticaPendiente"] = {
                "tipoConsulta": plan.get("tipo_consulta"),
                "operacion": plan.get("operacion"),
                "tipoUnidad": plan.get("tipo_unidad"),
                "descripcionTipoUnidad": plan.get(
                    "descripcion_tipo_unidad"
                ),
                "nivelesAtencion": list(
                    plan.get("niveles_atencion") or []
                ),
                "variable": plan.get("variable"),
                "ambito": plan.get("ambito"),
            }
        else:
            contexto_analitico.pop("consultaAnaliticaPendiente", None)

        if completada:
            contexto_analitico["ultimaConsultaAnalitica"] = {
                "tipoConsulta": plan.get("tipo_consulta"),
                "operacion": plan.get("operacion"),
                "tipoUnidad": plan.get("tipo_unidad"),
                "descripcionTipoUnidad": plan.get(
                    "descripcion_tipo_unidad"
                ),
                "nivelesAtencion": list(
                    plan.get("niveles_atencion") or []
                ),
                "ambito": plan.get("ambito"),
                "variable": (
                    None if es_count_unidades else plan.get("variable")
                ),
            }

        return contexto_analitico

    def _crear_respuesta_analitica_base(
        self,
        pregunta_usuario,
        contexto,
        status,
        mensaje,
        tipo_consulta,
        tipo_unidad,
        ambito,
        ok=True,
    ):
        return {
            "ok": ok,
            "status": status,
            "mensaje": mensaje,
            "pregunta_original": pregunta_usuario,
            "contexto": contexto,
            "hospital": {
                "status": "sin_texto",
                "hospital": None,
                "score": 0.0,
                "texto_usado": "",
            },
            "variable": {
                "status": "sin_texto",
                "variable": None,
                "score": 0.0,
                "texto_usado": "",
            },
            "datos": [],
            "requiereConfirmacion": False,
            "tipoConsulta": tipo_consulta,
            "tipoUnidad": tipo_unidad,
            "ambito": ambito,
        }

    def _crear_respuesta_count_unidades(
        self,
        pregunta_usuario,
        contexto,
        resultado,
    ):
        respuesta = self._crear_respuesta_analitica_base(
            pregunta_usuario=pregunta_usuario,
            contexto=contexto,
            status="ok",
            mensaje=self._crear_mensaje_count_unidades(resultado),
            tipo_consulta="COUNT_UNIDADES",
            tipo_unidad=resultado.get("tipo_unidad"),
            ambito=resultado.get("ambito"),
        )
        total = int(resultado.get("total_unidades") or 0)
        respuesta.update(
            {
                "operacion": "COUNT",
                "totalUnidades": total,
                "descripcionTipoUnidad": resultado.get(
                    "descripcion_tipo_unidad"
                ),
                "nivelesAtencion": list(
                    resultado.get("niveles_atencion") or []
                ),
                "resultadoAnalitico": {
                    "total": total,
                    "unidad": resultado.get("tipo_unidad"),
                },
            }
        )
        return respuesta

    def _crear_respuesta_extremo_por_unidad(
        self,
        pregunta_usuario,
        contexto,
        resultado,
    ):
        status = resultado.get("status")
        resultados = [
            {
                "clavePresupuestal": fila.get("clave_presupuestal"),
                "denominacionUnidad": fila.get("denominacion_unidad"),
                "region": fila.get("region"),
                "delegacion": fila.get("delegacion"),
                "claveEntidad": fila.get("clave_entidad"),
                "nivelAtencion": fila.get("nivel_atencion"),
                "valor": fila.get("valor"),
            }
            for fila in resultado.get("resultados") or []
        ]
        respuesta = self._crear_respuesta_analitica_base(
            pregunta_usuario=pregunta_usuario,
            contexto=contexto,
            status=status,
            mensaje=self._crear_mensaje_extremo_por_unidad(resultado),
            tipo_consulta="EXTREMO_POR_UNIDAD",
            tipo_unidad=resultado.get("tipo_unidad"),
            ambito=resultado.get("ambito"),
        )
        respuesta.update(
            {
                "operacion": resultado.get("operacion"),
                "descripcionTipoUnidad": resultado.get(
                    "descripcion_tipo_unidad"
                ),
                "nivelesAtencion": list(
                    resultado.get("niveles_atencion") or []
                ),
                "variableAnalitica": resultado.get("variable"),
                "valorExtremo": resultado.get("valor_extremo"),
                "totalEmpates": int(resultado.get("total_empates") or 0),
                "resultadosAnaliticos": resultados,
                "resultadoAnalitico": {
                    "valorExtremo": resultado.get("valor_extremo"),
                    "totalEmpates": int(
                        resultado.get("total_empates") or 0
                    ),
                    "resultados": resultados,
                },
            }
        )
        return respuesta

    def _crear_mensaje_extremo_por_unidad(self, resultado):
        tipo_unidad = resultado.get("tipo_unidad")
        variable = resultado.get("variable") or {}
        descripcion_variable = self._descripcion_variable_analitica(variable)
        ubicacion = self._descripcion_ambito_analitico(
            resultado.get("ambito")
        )
        resultados = list(resultado.get("resultados") or [])
        total_empates = int(resultado.get("total_empates") or 0)

        if resultado.get("status") == "sin_resultados" or not resultados:
            etiqueta = self._etiqueta_tipo_unidad(tipo_unidad, cantidad=2)
            return (
                f"No encontré {etiqueta} con datos de "
                f"“{descripcion_variable}” {ubicacion}."
            )

        operacion = resultado.get("operacion")
        extremo = "máximo" if operacion == "MAX" else "mínimo"
        valor = self._formatear_numero_analitico(
            resultado.get("valor_extremo")
        )

        if total_empates <= 1:
            etiqueta = self._etiqueta_tipo_unidad(tipo_unidad, cantidad=1)
            articulo = "La" if tipo_unidad == "UMF" else "El"
            nombre = (
                resultados[0].get("denominacion_unidad")
                or resultados[0].get("clave_presupuestal")
                or "la unidad encontrada"
            )
            return (
                f"{articulo} {etiqueta} con el valor {extremo} de "
                f"“{descripcion_variable}” {ubicacion} es {nombre}, "
                f"con {valor}."
            )

        etiqueta = self._etiqueta_tipo_unidad(
            tipo_unidad,
            cantidad=total_empates,
        )
        limite = self.MAX_RESULTADOS_EN_MENSAJE
        mostrados = resultados[:limite]
        pronombre = "Estas" if tipo_unidad == "UMF" else "Estos"
        participio = "empatadas" if tipo_unidad == "UMF" else "empatados"
        if total_empates > limite:
            introduccion = (
                f"Encontré {total_empates} {etiqueta} {participio} con el valor "
                f"{extremo} de {valor} para “{descripcion_variable}” "
                f"{ubicacion}. Te muestro las primeras {limite}:"
            )
        else:
            introduccion = (
                f"Encontré un empate. {pronombre} {total_empates} "
                f"{etiqueta} tienen el valor {extremo} de {valor} para "
                f"“{descripcion_variable}” {ubicacion}:"
            )

        nombres = [
            (
                fila.get("denominacion_unidad")
                or fila.get("clave_presupuestal")
                or "Unidad sin denominación"
            )
            for fila in mostrados
        ]
        listado = "\n".join(
            f"{indice}. {nombre}"
            for indice, nombre in enumerate(nombres, start=1)
        )
        return f"{introduccion}\n\n{listado}"

    def _crear_mensaje_falta_variable_extremo(self, plan):
        etiqueta = self._etiqueta_tipo_unidad(
            plan.get("tipo_unidad"),
            cantidad=2,
        )
        ubicacion = self._descripcion_ambito_analitico(plan.get("ambito"))
        return f"¿Qué dato deseas comparar entre {etiqueta} {ubicacion}?"

    def _crear_mensaje_falta_ambito_extremo(self, plan):
        etiqueta = self._etiqueta_tipo_unidad(
            plan.get("tipo_unidad"),
            cantidad=1,
        )
        operacion = plan.get("operacion")
        comparacion = "valor máximo" if operacion == "MAX" else "valor mínimo"
        descripcion = self._descripcion_variable_analitica(
            plan.get("variable") or {}
        )
        return (
            "¿En qué entidad, delegación o región deseas buscar "
            f"{etiqueta} con el {comparacion} de “{descripcion}”?"
        )

    @staticmethod
    def _etiqueta_tipo_unidad(tipo_unidad, cantidad=1):
        if tipo_unidad == "UMF":
            return (
                "unidad de medicina familiar"
                if cantidad == 1
                else "unidades de medicina familiar"
            )
        if tipo_unidad == "HOSPITAL":
            return "hospital" if cantidad == 1 else "hospitales"
        return "unidad" if cantidad == 1 else "unidades"

    @staticmethod
    def _descripcion_ambito_analitico(ambito):
        ambito = ambito if isinstance(ambito, dict) else {}
        tipo = str(ambito.get("tipo") or "").upper()
        descripcion = ambito.get("descripcion") or ambito.get("id")
        if tipo == "NACIONAL":
            return "a nivel nacional"
        if tipo == "DELEGACION" and descripcion:
            return f"en la delegación {descripcion}"
        if tipo == "REGION" and descripcion:
            return f"en la región {descripcion}"
        if tipo == "NIVEL_ATENCION" and descripcion:
            return f"en {descripcion}"
        if descripcion:
            return f"en {descripcion}"
        return "en el ámbito seleccionado"

    @staticmethod
    def _descripcion_variable_analitica(variable):
        descripcion = (
            variable.get("descripcion")
            or variable.get("desc_original")
            or variable.get("id")
            or "la variable seleccionada"
        )
        return str(descripcion).strip().rstrip(".")

    @staticmethod
    def _formatear_numero_analitico(valor):
        if isinstance(valor, int):
            return f"{valor:,}"
        if isinstance(valor, float):
            return f"{valor:,}"
        return str(valor)

    def _crear_mensaje_count_unidades(self, resultado):
        total = int(resultado.get("total_unidades") or 0)
        tipo_unidad = resultado.get("tipo_unidad")
        if total == 0:
            etiqueta = (
                "unidades de medicina familiar"
                if tipo_unidad == "UMF"
                else "hospitales"
            )
            return f"No encontré {etiqueta} en el ámbito seleccionado."

        if tipo_unidad == "UMF":
            etiqueta = (
                "unidad de medicina familiar"
                if total == 1
                else "unidades de medicina familiar"
            )
        else:
            etiqueta = "hospital" if total == 1 else "hospitales"

        ambito = resultado.get("ambito") or {}
        if str(ambito.get("tipo") or "").upper() == "NACIONAL":
            ubicacion = "a nivel nacional"
        else:
            descripcion = ambito.get("descripcion")
            ubicacion = (
                f"en {descripcion}"
                if descripcion
                else "en el ámbito seleccionado"
            )

        return f"Encontré {total:,} {etiqueta} {ubicacion}."

    def _crear_mensaje_falta_ambito_count_unidades(self, tipo_unidad):
        if tipo_unidad == "UMF":
            etiqueta = "las unidades de medicina familiar"
        else:
            etiqueta = "los hospitales"
        return (
            "¿En qué entidad, delegación o región deseas contar "
            f"{etiqueta}?"
        )

    def _descripcion_ambito(self, ambito):
        return (
            ambito.get("desc_original")
            or ambito.get("descripcion")
            or ambito.get("nombre_original")
            or ambito.get("texto_usado")
            or ambito.get("id")
            or "el ámbito detectado"
        )

    def _descripcion_variable(self, variable):
        return (
            variable.get("descripcion")
            or variable.get("desc_original")
            or variable.get("id")
            or "detectada"
        )

    def _mensaje_varias_opciones(
        self,
        hay_candidatos_variable=False,
        hay_candidatos_hospital=False,
        ambito=None,
        hospital=None,
    ):
        if hay_candidatos_variable:
            destino = self._descripcion_ambito(ambito) if ambito else None
            if not destino and hospital:
                destino = (
                    hospital.get("nombre_original")
                    or hospital.get("desc_original")
                    or hospital.get("descripcion")
                    or hospital.get("id")
                )
            if destino:
                return (
                    "Encontré más de una variable relacionada con tu búsqueda. "
                    f"Selecciona la que deseas consultar para {destino}."
                )
            return (
                "Encontré más de una variable relacionada con tu búsqueda. "
                "Selecciona una para continuar."
            )

        if hay_candidatos_hospital:
            return (
                "Encontré más de una unidad médica relacionada con tu búsqueda. "
                "Selecciona una para continuar."
            )

        return "Encontré más de una opción. Selecciona una para continuar."

    def _requiere_confirmacion(self, resultado_hospital, resultado_variable):
        return bool(
            resultado_hospital.get("candidatos")
            or resultado_variable.get("candidatos")
        )

    def _normalizar_hospital_contexto(self, hospital_contexto):
        hospital = hospital_contexto.copy()
        hospital_id = str(hospital.get("id", "")).strip()

        for item in catalogos.catalogo_hospitales:
            if str(item.get("id", "")).strip() == hospital_id:
                hospital.setdefault("desc_original", item.get("desc_original"))
                hospital.setdefault("desc_normalizada", item.get("desc_normalizada"))
                return hospital

        nombre = hospital.get("nombre_original") or hospital.get("desc_original") or ""
        hospital.setdefault("desc_original", nombre)
        hospital.setdefault("desc_normalizada", nombre)
        return hospital

    def _normalizar_variable_contexto(self, variable_contexto):
        variable = variable_contexto.copy()
        variable_id = str(variable.get("id", "")).strip()

        for item in catalogos.catalogo_variables:
            if str(item.get("id", "")).strip() == variable_id:
                variable.setdefault("descripcion", item.get("descripcion"))
                variable.setdefault("desc_original", item.get("desc_original"))
                variable.setdefault("desc_normalizada", item.get("desc_normalizada"))
                return variable

        descripcion = variable.get("descripcion") or variable.get("desc_original") or ""
        variable.setdefault("descripcion", descripcion)
        variable.setdefault("desc_original", descripcion)
        variable.setdefault("desc_normalizada", descripcion)
        return variable

    def _debe_buscar_variable_desde_texto(self, texto_variable):
        texto = (texto_variable or "").strip()
        if len(texto) < 3:
            return False, "texto útil menor a 3 caracteres"

        tokens = [
            token
            for token in texto.split()
            if token not in self.CONECTORES_SIN_VARIABLE
        ]
        if not tokens:
            return False, "solo contiene conectores"

        if not any(len(token) >= 3 for token in tokens):
            return False, "sin tokens útiles de al menos 3 caracteres"

        if not any(token in self.tokens_catalogo_variables for token in tokens):
            return False, "sin términos reconocibles del catálogo de variables"

        return True, ""

    def _tiene_intencion_consulta(
        self,
        pregunta_normalizada,
        hospital_confirmado=False,
        variable_confirmada=False,
    ):
        if hospital_confirmado or variable_confirmada:
            return True, ""

        texto = (pregunta_normalizada or "").strip()
        if len(texto) < 3:
            return False, "texto demasiado corto"

        tokens = [
            token
            for token in texto.split()
            if token not in self.CONECTORES_SIN_VARIABLE
        ]
        if not tokens:
            return False, "solo contiene conectores"

        if not any(len(token) >= 3 for token in tokens):
            return False, "sin tokens útiles de al menos 3 caracteres"

        tokens_set = set(tokens)
        if tokens_set & self.TERMINOS_CONSULTA:
            return True, ""
        if tokens_set & self.TERMINOS_HOSPITAL:
            return True, ""
        if tokens_set & self.tokens_catalogo_variables:
            return True, ""
        if tokens_set & self.tokens_catalogo_hospitales:
            return True, ""

        return False, "sin términos médicos, hospitalarios, geográficos o de consulta"

    def _crear_tokens_catalogo_variables(self):
        tokens = set()
        for variable in catalogos.catalogo_variables:
            texto = (
                variable.get("desc_normalizada")
                or variable.get("descripcion")
                or variable.get("desc_original")
                or ""
            )
            tokens.update(
                token
                for token in str(texto).split()
                if len(token) >= 3
                and token not in self.CONECTORES_SIN_VARIABLE
            )

        for regla in VARIABLES_CANONICAS.values():
            tokens.update(
                token
                for token in regla.get("tokens_genericos", set())
                if len(token) >= 3
                and token not in self.CONECTORES_SIN_VARIABLE
            )

        return tokens

    def _crear_tokens_catalogo_hospitales(self):
        tokens = set()
        for hospital in catalogos.catalogo_hospitales:
            texto = (
                hospital.get("desc_normalizada")
                or hospital.get("nombre_original")
                or hospital.get("desc_original")
                or ""
            )
            tokens.update(
                token
                for token in str(texto).split()
                if len(token) >= 3
                and token not in self.CONECTORES_SIN_VARIABLE
            )
        return tokens


engine = ChatbotEngine()
