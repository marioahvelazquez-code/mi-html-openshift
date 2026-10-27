import re

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
        "cmn",
        "hgo",
        "hes",
        "hc",
        "hp",
        "honco",
    }
    TERMINOS_UMAE = {"umae", "umaes"}
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
        modo_turno = self._clasificar_turno(pregunta_usuario, contexto)
        consulta_previa = self._consulta_previa(contexto) if modo_turno != "nueva" else {}
        # Una pregunta independiente no debe recuperar filtros omitidos.
        if modo_turno == "nueva":
            contexto = {}
        pregunta_interpretacion = self._sin_retiradas(pregunta_usuario)
        hospital_contexto = contexto.get("hospital")
        variable_contexto = contexto.get("variable")
        hospital_confirmado = bool(contexto.get("hospitalConfirmadoPorUsuario"))
        variable_confirmada = bool(contexto.get("variableConfirmadaPorUsuario"))

        print("[chatbot] pregunta recibida:", pregunta_usuario, flush=True)
        print("[chatbot] contexto recibido:", contexto, flush=True)
        print("[chatbot] hospital confirmado por usuario:", hospital_confirmado, flush=True)
        print("[chatbot] variable confirmada por usuario:", variable_confirmada, flush=True)

        pregunta_normalizada = normalizar_texto_completo(pregunta_interpretacion)
        filtro_umae = self._detectar_filtro_umae(pregunta_normalizada)
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
        if modo_turno == "seguimiento" and consulta_previa:
            if resultado_operacion.get("operacion") == "SIN_OPERACION_ANALITICA":
                resultado_operacion = {
                    **resultado_operacion,
                    "operacion": consulta_previa.get("operacion") or "SIN_OPERACION_ANALITICA",
                }
            if resultado_tipo_unidad.get("status") == "sin_tipo_unidad" and consulta_previa.get("tipoUnidad"):
                resultado_tipo_unidad = self.detector_tipo_unidad.detectar(consulta_previa["tipoUnidad"])
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
        mencion_umae_generica = self._es_mencion_umae_generica(
            pregunta_normalizada
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
        if modo_turno == "seguimiento" and consulta_previa:
            tiene_intencion = True
            razon_sin_intencion = "seguimiento con consulta previa; validar cambios antes de ejecutar"
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
        elif mencion_umae_generica:
            resultado_hospital = resultado_hospital_texto
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

        pregunta_variable = self._quitar_formula_peticion(pregunta_interpretacion)
        texto_variable_limpio = self.buscador_variable._preparar_texto(
            pregunta_variable,
            hospital_detectado,
        )
        nivel_atencion_para_plan = self._extraer_nivel_atencion(
            ambito_detectado
        )
        es_conteo_generico_por_nivel = (
            self._es_conteo_generico_unidades_por_nivel(
                resultado_operacion,
                resultado_tipo_unidad,
                nivel_atencion_para_plan,
                texto_variable_limpio,
            )
        )
        es_conteo_umae = (
            resultado_operacion.get("operacion") == "COUNT"
            and filtro_umae
            and not texto_variable_limpio
        )
        conteo_sin_variable = self._conteo_solicitado_sin_variable(
            pregunta_variable,
            resultado_operacion,
            resultado_tipo_unidad,
            contexto,
            mencion_umae_generica,
            hospital_detectado,
        )
        es_conteo_tipo_unidad = conteo_sin_variable == "UMF"
        if conteo_sin_variable == "UMAE":
            es_conteo_umae = True
            if resultado_operacion.get("operacion") == "SIN_OPERACION_ANALITICA":
                resultado_operacion = {
                    **resultado_operacion,
                    "operacion": "COUNT",
                    "termino_detectado": None,
                    "confianza": 1.0,
                }
        se_busca_variable_desde_texto, razon_no_buscar_variable = (
            self._debe_buscar_variable_desde_texto(texto_variable_limpio)
        )
        if variable_confirmada:
            se_busca_variable_desde_texto = False
            razon_no_buscar_variable = "variable confirmada por usuario"
        if es_conteo_generico_por_nivel or es_conteo_umae or es_conteo_tipo_unidad:
            se_busca_variable_desde_texto = False
            razon_no_buscar_variable = (
                "conteo explícito de unidades por nivel de atención"
                if es_conteo_generico_por_nivel
                else (
                    "conteo explícito de unidades de medicina familiar"
                    if es_conteo_tipo_unidad
                    else "conteo de unidades UMAE sin variable"
                )
            )

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
                pregunta_variable,
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
        if es_conteo_generico_por_nivel or es_conteo_umae or es_conteo_tipo_unidad:
            variable_para_plan = None
        elif variable_confirmada and variable_contexto:
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

        if (
            not ambito_para_plan
            and filtro_umae
            and mencion_umae_generica
            and not hospital_para_plan
            and (variable_para_plan or es_conteo_umae)
        ):
            ambito_para_plan = {
                "tipo": "NACIONAL",
                "id": "NACIONAL",
                "descripcion": "Nacional",
            }

        consulta_efectiva, conflicto = self._consolidar_consulta(
            pregunta_usuario, modo_turno, consulta_previa, contexto,
            resultado_operacion, resultado_tipo_unidad,
            resultado_variable_texto, variable_para_plan, hospital_para_plan,
            ambito_detectado, nivel_atencion_para_plan, filtro_umae,
        )
        if conflicto:
            return self._respuesta_conflicto(pregunta_usuario, contexto, consulta_efectiva, conflicto)
        plan_consulta = self.planificador_consulta.construir(
            resultado_operacion={"operacion": consulta_efectiva["operacion"]},
            resultado_tipo_unidad=consulta_efectiva["detectorTipoUnidad"],
            ambito=consulta_efectiva["ambito"],
            variable=consulta_efectiva["variable"],
            hospital=consulta_efectiva["hospital"],
            nivel_atencion=consulta_efectiva["nivelAtencion"],
            contar_unidades=consulta_efectiva["contarUnidades"],
            filtro_umae=consulta_efectiva["filtroUmae"],
        )
        if plan_consulta.get("status") == "plan_valido":
            consulta_efectiva = self._consulta_desde_plan(plan_consulta)
        if consulta_efectiva.get("variable"):
            resultado_variable = {
                **resultado_variable, "status": "ganador_claro",
                "variable": consulta_efectiva["variable"],
            }
        if consulta_efectiva.get("hospital"):
            resultado_hospital = {
                **resultado_hospital, "status": "ganador_claro",
                "hospital": consulta_efectiva["hospital"],
            }
        elif consulta_efectiva.get("ambito"):
            resultado_hospital = {"status": "ganador_claro", "hospital": None,
                                  "ambito_macro": self._ambito_publicado(consulta_efectiva),
                                  "score": 1.0, "texto_usado": pregunta_usuario}
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

        candidatos_pendientes = resultado_variable.get("candidatos") or []
        contexto_final = self._publicar_consulta(
            contexto, consulta_efectiva,
            pendiente=bool(candidatos_pendientes) or plan_consulta.get("status") != "plan_valido"
                      or not (consulta_efectiva.get("ambito") or consulta_efectiva.get("hospital")),
            candidatos=candidatos_pendientes,
        )
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
            plan_consulta.get("status") == "plan_valido"
            and plan_consulta.get("tipo_consulta") == "CONSULTA_IFU"
            and (puede_consultar_hospital or puede_consultar_ambito)
        ):
            clave_unidad = hospital_final["id"] if puede_consultar_hospital else None
            variable_id = variable_final["id"]
            print("[chatbot] variable final usada para SQL:", variable_id, flush=True)
            se_consulta_sql = True

            if puede_consultar_ambito:
                argumentos_consulta_ifu = {
                    "tipo_ambito": ambito_final["tipo"],
                    "filtro_id": ambito_final["id"],
                    "variable_id": variable_id,
                }
                nivel_efectivo = consulta_efectiva.get("nivelAtencion")
                if nivel_efectivo:
                    argumentos_consulta_ifu["nivel_atencion"] = nivel_efectivo["id"]
                if consulta_efectiva["filtroUmae"]:
                    argumentos_consulta_ifu["filtro_umae"] = True

                datos = self.consulta_ifu.obtener_valor_dinamico(
                    **argumentos_consulta_ifu
                )
            else:
                datos = self.consulta_ifu.obtener_valor(
                    clave_unidad=clave_unidad,
                    variable_id=variable_id
                )
                   
        if se_consulta_sql:
            contexto_final = self._publicar_consulta(contexto, consulta_efectiva, completada=True)
            if not datos:
                return {
                    "status": "sin_datos",
                    "mensaje": "No existen registros para la variable y los filtros seleccionados.",
                    "pregunta_original": pregunta_usuario, "contexto": contexto_final,
                    "hospital": resultado_hospital, "variable": resultado_variable,
                    "datos": [], "requiereConfirmacion": False,
                    "filtroUmae": consulta_efectiva["filtroUmae"],
                }
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
            "filtroUmae": bool(plan_consulta.get("filtro_umae")),
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

    @staticmethod
    def _sin_retiradas(pregunta):
        texto = normalizar_texto_completo(pregunta)
        limpio = re.sub(r"\b(?:quitar|retirar|eliminar) el filtro umae\b|\b(?:en )?todos los niveles\b", " ", texto)
        return re.sub(r"\s+", " ", limpio).strip() if limpio != texto else pregunta

    def _consulta_previa(self, contexto):
        for campo in ("consultaPendiente", "ultimaConsultaEfectiva"):
            if isinstance(contexto.get(campo), dict):
                return dict(contexto[campo])
        # Compatibilidad con clientes que todavía envían la conversación anterior.
        anterior = contexto.get("consultaAnaliticaPendiente") or contexto.get("ultimaConsultaAnalitica") or {}
        if not isinstance(anterior, dict):
            anterior = {}
        ambito = contexto.get("ambito") or anterior.get("ambito")
        nivel = contexto.get("nivelAtencion") or (ambito or {}).get("nivel_atencion")
        variable = contexto.get("variable") or anterior.get("variable")
        hospital = contexto.get("hospital")
        if not (ambito or variable or hospital or anterior):
            return {}
        return {"tipoConsulta": anterior.get("tipoConsulta", "CONSULTA_IFU"),
                "operacion": anterior.get("operacion", "VALOR" if hospital else "SUM"),
                "variable": variable, "hospital": hospital,
                "ambito": self._preparar_ambito_para_planificador(ambito),
                "nivelAtencion": nivel, "filtroUmae": bool(contexto.get("filtroUmae", anterior.get("filtroUmae", False))),
                "tipoUnidad": anterior.get("tipoUnidad"),
                "nivelesAtencion": anterior.get("nivelesAtencion", [])}

    def _clasificar_turno(self, pregunta, contexto):
        if contexto.get("variableConfirmadaPorUsuario") or contexto.get("hospitalConfirmadoPorUsuario"):
            return "confirmacion"
        if not self._consulta_previa(contexto):
            return "nueva"
        texto = normalizar_texto_completo(pregunta)
        if re.match(r"^y\b", texto):
            return "seguimiento"
        if re.fullmatch(r"(?:quitar|retirar|eliminar) el filtro umae|(?:en )?todos los niveles", texto):
            return "seguimiento"
        # Sin Y solo se aceptan modificadores geográficos completos, sin
        # variable, verbo de petición ni texto adicional desconocido.
        if re.match(r"^en\s+", texto):
            ambito = self.buscador_ambito.buscar(texto)
            if ambito.get("tipo") != "HOSPITAL" and not self.buscador_variable._preparar_texto(texto):
                return "seguimiento"
        return "nueva"

    def _consolidar_consulta(
        self, pregunta, modo, previa, contexto, operacion, tipo,
        variable_texto, variable, hospital, ambito_detectado, nivel, umae,
    ):
        texto = normalizar_texto_completo(pregunta)
        hereda = modo in {"seguimiento", "confirmacion"}
        previa = previa if hereda else {}
        ambito = self._preparar_ambito_para_planificador(ambito_detectado)
        explicito = variable_texto.get("status") == "ganador_claro" or bool(contexto.get("variableConfirmadaPorUsuario"))
        ambigua = variable_texto.get("status") in {"empate_tecnico", "baja_confianza"} and bool(variable_texto.get("candidatos")) and not contexto.get("variableConfirmadaPorUsuario")
        q = {"tipoConsulta": "CONSULTA_IFU", "operacion": operacion.get("operacion"),
             "variable": variable if explicito else (None if ambigua else previa.get("variable")),
             "hospital": hospital or previa.get("hospital"),
             "ambito": ambito or previa.get("ambito"),
             "nivelAtencion": nivel or previa.get("nivelAtencion"),
             "filtroUmae": bool(umae or previa.get("filtroUmae")),
             "tipoUnidad": tipo.get("tipo_unidad") or previa.get("tipoUnidad"),
             "nivelesAtencion": list(tipo.get("niveles_atencion") or previa.get("nivelesAtencion") or []),
             "detectorTipoUnidad": tipo, "contarUnidades": False}
        if modo == "confirmacion" and contexto.get("variableConfirmadaPorUsuario"):
            q["variable"] = self._normalizar_variable_contexto(contexto.get("variable") or {})
        if ambito:
            if ambito["tipo"] == "NIVEL_ATENCION" and previa.get("ambito") and previa["ambito"]["tipo"] != "NIVEL_ATENCION":
                q["ambito"] = previa["ambito"]
            elif ambito["tipo"] != "NIVEL_ATENCION" and not hospital:
                q["hospital"] = None
        if hospital:
            if nivel or umae:
                return q, "Confirma el hospital o el ámbito con filtros; no combinaré restricciones incompatibles."
            q.update(ambito=None, nivelAtencion=None, filtroUmae=False)
        elif q.get("hospital") and nivel:
            return q, "Indica si deseas conservar el hospital o consultar un nivel de atención."
        if re.search(r"\bsin (?:las? )?umaes?\b", texto):
            return q, "¿Deseas excluir las UMAE o quitar el filtro para incluir todas las unidades?"
        retira_umae = bool(re.search(r"\b(?:quitar|retirar|eliminar) el filtro umae\b", texto))
        retira_nivel = "todos los niveles" in texto
        if retira_umae:
            q["filtroUmae"] = False
        if retira_nivel:
            q["nivelAtencion"] = None
            if (q.get("ambito") or {}).get("tipo") == "NIVEL_ATENCION":
                q["ambito"] = {"tipo": "NACIONAL", "id": "NACIONAL", "descripcion": "Nacional"}
        if ambigua:
            q["variable"] = None
            q["operacion"] = "SIN_OPERACION_ANALITICA"
        if q["variable"]:
            # Una variable explícita cambia COUNT a infraestructura. Las
            # restricciones del tipo de unidad se materializan como nivel.
            if explicito and previa.get("operacion") == "COUNT":
                q["operacion"] = "SIN_OPERACION_ANALITICA"
                if not q["nivelAtencion"] and len(q["nivelesAtencion"]) == 1:
                    n = q["nivelesAtencion"][0]
                    q["nivelAtencion"] = {"id": n, "descripcion": n}
                elif not q["nivelAtencion"] and len(q["nivelesAtencion"]) > 1:
                    return q, "El tipo de unidad abarca varios niveles. Indica un nivel antes de consultar infraestructura; no quitaré ese filtro silenciosamente."
        else:
            q["contarUnidades"] = bool(q["operacion"] == "COUNT" and (q["filtroUmae"] or q["nivelAtencion"] or q["tipoUnidad"]))
            if q["contarUnidades"]:
                q["tipoConsulta"] = "COUNT_UNIDADES"
            elif retira_umae and q["operacion"] == "COUNT":
                return q, "¿Qué tipo de unidad deseas contar al retirar el filtro UMAE?"
        if q["tipoUnidad"] == "UMF" and q["nivelAtencion"] and q["nivelAtencion"]["id"] != "Primer Nivel":
            return q, "El tipo UMF y el nivel solicitado son contradictorios. ¿Qué filtro deseas cambiar?"
        if not q["ambito"] and not q["hospital"] and q["filtroUmae"] and (q["variable"] or q["contarUnidades"]):
            q["ambito"] = {"tipo": "NACIONAL", "id": "NACIONAL", "descripcion": "Nacional"}
        if modo == "seguimiento":
            cambio = explicito or ambigua or ambito or hospital or nivel or umae or retira_nivel or retira_umae or tipo.get("termino_detectado")
            if not cambio:
                return q, "Indica qué variable, ámbito o filtro deseas cambiar."
        return q, None

    @staticmethod
    def _consulta_desde_plan(plan):
        return {"tipoConsulta": plan.get("tipo_consulta"), "operacion": plan.get("operacion"),
                "variable": plan.get("variable"), "ambito": plan.get("ambito"),
                "hospital": plan.get("hospital"), "nivelAtencion": plan.get("nivel_atencion"),
                "filtroUmae": bool(plan.get("filtro_umae")), "tipoUnidad": plan.get("tipo_unidad"),
                "descripcionTipoUnidad": plan.get("descripcion_tipo_unidad"),
                "nivelesAtencion": list(plan.get("niveles_atencion") or [])}

    @staticmethod
    def _ambito_publicado(q):
        if not q.get("ambito"):
            return None
        ambito = dict(q["ambito"])
        if q.get("nivelAtencion"):
            ambito["nivel_atencion"] = q["nivelAtencion"]
        return ambito

    def _publicar_consulta(self, contexto, consulta, pendiente=False, completada=False, candidatos=None):
        q = {k: v for k, v in consulta.items() if k not in {"detectorTipoUnidad", "contarUnidades"}}
        q["estado"] = "ejecutada" if completada else "pendiente" if pendiente else "planificada"
        c = {**contexto, "variable": q.get("variable"), "hospital": q.get("hospital"),
             "ambito": self._ambito_publicado(q), "nivelAtencion": q.get("nivelAtencion"),
             "nivel_atencion": q.get("nivelAtencion"), "filtroUmae": bool(q.get("filtroUmae")),
             "tipoUnidad": q.get("tipoUnidad"), "operacion": q.get("operacion"),
             "nivelesAtencion": list(q.get("nivelesAtencion") or []),
             "hospitalConfirmadoPorUsuario": False, "variableConfirmadaPorUsuario": False,
             "consultaEfectiva": q, "consultaPendiente": None,
             "consultaAnaliticaPendiente": None, "ultimaConsultaAnalitica": None,
             "region": None, "entidad": None, "delegacion": None,
             "filtros": {"nivelAtencion": q.get("nivelAtencion"), "umae": bool(q.get("filtroUmae"))}}
        # Nunca sustituir la última consulta ejecutada por una pendiente.
        c["ultimaConsultaEfectiva"] = q if completada else contexto.get("ultimaConsultaEfectiva")
        if pendiente:
            c["consultaPendiente"] = {**q, "candidatos": list(candidatos or [])}
        if q.get("tipoConsulta") in {"COUNT_UNIDADES", "EXTREMO_POR_UNIDAD"}:
            if pendiente:
                c["consultaAnaliticaPendiente"] = q
            elif completada:
                c["ultimaConsultaAnalitica"] = q
        return c

    def _respuesta_conflicto(self, pregunta, contexto, q, mensaje):
        return {"status": "requiere_aclaracion", "mensaje": mensaje,
                "pregunta_original": pregunta, "contexto": self._publicar_consulta(contexto, q, pendiente=True),
                "hospital": {"status": "sin_texto", "hospital": None},
                "variable": {"status": "sin_texto", "variable": None},
                "datos": [], "requiereConfirmacion": False}

    @staticmethod
    def _quitar_formula_peticion(pregunta):
        # Solo prefijos completos: no cambia las palabra del buscador ni
        # elimina palabras de infraestructura, negaciones o especialidades.
        texto = normalizar_texto_completo(pregunta)
        limpio = re.sub(r"^(?:me puedes decir|necesito conocer)\s+", "", texto)
        return limpio if limpio != texto else pregunta

    def _conteo_solicitado_sin_variable(
        self, pregunta, operacion, tipo_unidad, contexto,
        umae_generica, hospital,
    ):
        if hospital or contexto.get("variable") or contexto.get("variableConfirmadaPorUsuario"):
            return None
        for campo in ("consultaAnaliticaPendiente", "ultimaConsultaAnalitica"):
            pendiente = contexto.get(campo)
            if isinstance(pendiente, dict) and pendiente.get("variable"):
                return None
        op = operacion.get("operacion")
        if op not in {"COUNT", "SIN_OPERACION_ANALITICA"}:
            return None
        texto = normalizar_texto_completo(pregunta)
        if umae_generica:
            restante = self.buscador_variable._preparar_texto(texto)
            # Modificador temporal de la solicitud de conteo, no una regla
            # global de limpieza ni una selección de corte SQL.
            if not (set(restante.split()) - {"actualmente"}):
                return "UMAE"
        termino = tipo_unidad.get("termino_detectado") or ""
        if (
            op == "COUNT"
            and tipo_unidad.get("status") == "ganador_claro"
            and tipo_unidad.get("tipo_unidad") == "UMF"
            and len(termino.split()) > 1
        ):
            sin_tipo = re.sub(r"\b" + re.escape(termino) + r"\b", " ", texto)
            if not self.buscador_variable._preparar_texto(sin_tipo):
                return "UMF"
        return None

    @classmethod
    def _detectar_filtro_umae(cls, pregunta_normalizada):
        tokens = set((pregunta_normalizada or "").split())
        return bool(tokens & cls.TERMINOS_UMAE)

    @classmethod
    def _es_mencion_umae_generica(cls, pregunta_normalizada):
        tokens = set((pregunta_normalizada or "").split())
        if not tokens & cls.TERMINOS_UMAE:
            return False

        indicadores_especificos = cls.INDICADORES_UNIDAD_PUNTUAL | {
            "hospital"
        }
        tiene_indicador_especifico = bool(tokens & indicadores_especificos)
        tiene_identificador_numerico = any(
            token.isdigit()
            for token in tokens
        )
        return not tiene_indicador_especifico and not tiene_identificador_numerico

    @staticmethod
    def _extraer_nivel_atencion(resultado_ambito):
        if not isinstance(resultado_ambito, dict):
            return None

        nivel = resultado_ambito.get("nivel_atencion")
        if isinstance(nivel, dict):
            return nivel

        if str(resultado_ambito.get("tipo") or "").upper() != "NIVEL_ATENCION":
            return None

        identificador = resultado_ambito.get("id")
        if not identificador:
            return None

        return {
            "tipo": "NIVEL_ATENCION",
            "id": identificador,
            "descripcion": (
                resultado_ambito.get("desc_original")
                or resultado_ambito.get("descripcion")
                or identificador
            ),
        }

    @staticmethod
    def _es_conteo_generico_unidades_por_nivel(
        resultado_operacion,
        resultado_tipo_unidad,
        nivel_atencion,
        texto_variable,
    ):
        if (resultado_operacion or {}).get("operacion") != "COUNT":
            return False
        if not nivel_atencion:
            return False
        if (resultado_tipo_unidad or {}).get("status") == "ganador_claro":
            return False

        tokens = set((texto_variable or "").split())
        if not tokens & {"unidad", "unidades"}:
            return False

        tokens_especificos = tokens - {"unidad", "unidades", "ooad"}
        return not tokens_especificos

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
        return self._publicar_consulta(
            contexto, self._consulta_desde_plan(plan),
            pendiente=pendiente, completada=completada,
        )

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
                "filtroUmae": bool(resultado.get("filtro_umae")),
                "resultadoAnalitico": {
                    "total": total,
                    "unidad": (
                        "UMAE"
                        if resultado.get("filtro_umae")
                        else resultado.get("tipo_unidad")
                    ),
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
        filtro_umae = bool(resultado.get("filtro_umae"))
        if total == 0:
            if filtro_umae:
                etiqueta = "UMAE"
            elif tipo_unidad == "UMF":
                etiqueta = "unidades de medicina familiar"
            elif tipo_unidad == "HOSPITAL":
                etiqueta = "hospitales"
            else:
                etiqueta = "unidades"
            return f"No encontré {etiqueta} en el ámbito seleccionado."

        if filtro_umae:
            etiqueta = "UMAE"
        elif tipo_unidad == "UMF":
            etiqueta = (
                "unidad de medicina familiar"
                if total == 1
                else "unidades de medicina familiar"
            )
        elif tipo_unidad == "HOSPITAL":
            etiqueta = "hospital" if total == 1 else "hospitales"
        else:
            etiqueta = "unidad" if total == 1 else "unidades"

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
