#Aqui trato de detectar operaciones (max y min)en preguntas del chatbot

from .normalizador import normalizar_texto_completo


class DetectorOperacion:
    TERMINOS_COUNT = {
        "cuanto",
        "cuantos",
        "cuanta",
        "cuantas",
        "numero",
        "cantidad",
        "total",
    }

    TERMINOS_MAX = {
        "mas",
        "mayor",
        "mayores",
        "maximo",
        "maxima",
        "maximos",
        "maximas",
    }

    TERMINOS_MIN = {
        "menos",
        "menor",
        "menores",
        "minimo",
        "minima",
        "minimos",
        "minimas",
    }

    def detectar(self, pregunta):
        pregunta_normalizada = normalizar_texto_completo(pregunta)
        tokens = set(pregunta_normalizada.split())

        coincidencias_max = tokens & self.TERMINOS_MAX
        coincidencias_min = tokens & self.TERMINOS_MIN
        coincidencias_count = tokens & self.TERMINOS_COUNT

        if coincidencias_max:
            operacion = "MAX"
            termino_detectado = sorted(coincidencias_max)[0]
        elif coincidencias_min:
            operacion = "MIN"
            termino_detectado = sorted(coincidencias_min)[0]
        elif coincidencias_count:
            operacion = "COUNT"
            termino_detectado = sorted(coincidencias_count)[0]
        else:
            operacion = "SIN_OPERACION_ANALITICA"
            termino_detectado = None

        return {
            "operacion": operacion,
            "termino_detectado": termino_detectado,
            "pregunta_normalizada": pregunta_normalizada,
            "confianza": 1.0 if termino_detectado else 0.0,
        }
