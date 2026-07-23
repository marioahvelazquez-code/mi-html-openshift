
#Aqui trato de detectar tipos de unidad en preguntas del chatbot

from .normalizador import normalizar_texto_completo


TIPOS_UNIDAD = {
    "UMF": {
        "descripcion": "Unidad de Medicina Familiar",
        "sinonimos": {
            "umf",
            "umfs",
            "unidad de medicina familiar",
            "unidades de medicina familiar",
        },
        "niveles_atencion": [
            "Primer Nivel",
        ],
    },
    "HOSPITAL": {
        "descripcion": "Hospital",
        "sinonimos": {
            "hospital",
            "hospitales",
        },
        "niveles_atencion": [
            "Segundo Nivel",
            "Tercer Nivel",
            "2do Nivel",
            "3er Nivel",            
            "Nivel dos",
            "Nivel tres",    
            "Nivel 2",
            "Nivel 3",                        
        ],
    },
}


class DetectorTipoUnidad:
    def detectar(self, pregunta):
        pregunta_normalizada = normalizar_texto_completo(pregunta)
        tipos_detectados = []

        for tipo_unidad, configuracion in TIPOS_UNIDAD.items():
            sinonimos_ordenados = sorted(
                configuracion["sinonimos"],
                key=lambda sinonimo: (
                    len(sinonimo.split()),
                    len(sinonimo),
                ),
                reverse=True,
            )

            termino_detectado = next(
                (
                    sinonimo
                    for sinonimo in sinonimos_ordenados
                    if self._contiene_sinonimo(
                        pregunta_normalizada,
                        sinonimo,
                    )
                ),
                None,
            )

            if termino_detectado:
                tipos_detectados.append(
                    {
                        "tipo_unidad": tipo_unidad,
                        "descripcion": configuracion["descripcion"],
                        "niveles_atencion": list(
                            configuracion["niveles_atencion"]
                        ),
                        "termino_detectado": termino_detectado,
                    }
                )

        if not tipos_detectados:
            return {
                "status": "sin_tipo_unidad",
                "tipo_unidad": None,
                "descripcion": None,
                "niveles_atencion": [],
                "termino_detectado": None,
                "tipos_detectados": [],
                "pregunta_normalizada": pregunta_normalizada,
                "confianza": 0.0,
            }

        if len(tipos_detectados) > 1:
            return {
                "status": "multiple_tipo_unidad",
                "tipo_unidad": None,
                "descripcion": None,
                "niveles_atencion": [],
                "termino_detectado": None,
                "tipos_detectados": tipos_detectados,
                "pregunta_normalizada": pregunta_normalizada,
                "confianza": 0.0,
            }

        ganador = tipos_detectados[0]

        return {
            "status": "ganador_claro",
            "tipo_unidad": ganador["tipo_unidad"],
            "descripcion": ganador["descripcion"],
            "niveles_atencion": ganador["niveles_atencion"],
            "termino_detectado": ganador["termino_detectado"],
            "tipos_detectados": tipos_detectados,
            "pregunta_normalizada": pregunta_normalizada,
            "confianza": 1.0,
        }

    @staticmethod
    def _contiene_sinonimo(pregunta_normalizada, sinonimo):
        tokens_pregunta = pregunta_normalizada.split()
        tokens_sinonimo = sinonimo.split()

        if len(tokens_sinonimo) == 1:
            return tokens_sinonimo[0] in tokens_pregunta

        cantidad_tokens = len(tokens_sinonimo)
        return any(
            tokens_pregunta[indice : indice + cantidad_tokens] == tokens_sinonimo
            for indice in range(len(tokens_pregunta) - cantidad_tokens + 1)
        )
