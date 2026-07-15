

from .consulta_ifu import ConsultaIFU
from .buscador_hospital import BuscadorHospital
from .buscador_variable import BuscadorVariable
from .catalogos import catalogos
from .normalizador import normalizar_texto_completo
from .buscador_ambito import BuscadorAmbito


class ChatbotEngine:
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

        # Detecta si la consulta usa un hospital o un ámbito general.
        ambito_detectado = self.buscador_ambito.buscar(pregunta_normalizada)
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

        variable_final_usada = (
            resultado_variable["variable"]["id"]
            if resultado_variable["status"] == "ganador_claro"
            and resultado_variable.get("variable")
            else None
        )
        print("[chatbot] variable_final_usada:", variable_final_usada, flush=True)

        hospital_contexto_final = hospital_contexto
        if (
            not es_ambito_macro
            and resultado_hospital["status"] == "ganador_claro"
            and resultado_hospital.get("hospital")
        ):
            hospital_contexto_final = resultado_hospital["hospital"]

        if resultado_variable["status"] == "ganador_claro":
            variable_contexto_final = resultado_variable["variable"]
        elif se_busca_variable_desde_texto and resultado_variable["status"] == "empate_tecnico":
            variable_contexto_final = None
        else:
            variable_contexto_final = variable_contexto

        contexto_final = {
            **contexto,
            "hospital": hospital_contexto_final,
            "ambito": ambito_detectado if es_ambito_macro else contexto.get("ambito"),
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
            and resultado_variable.get("status") == "empate_tecnico"
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
