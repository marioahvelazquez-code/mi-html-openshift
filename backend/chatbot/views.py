from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .chatbot import engine


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def chatbot(request):
    payload = request.data if isinstance(request.data, dict) else {}
    pregunta = str(payload.get("pregunta", "")).strip()
    contexto = payload.get("contexto") or {}

    if not pregunta:
        return Response(
            {
                "ok": False,
                "respuesta": "Escribe una pregunta para poder ayudarte.",
            },
            status=400,
        )

    resultado = engine.procesar(
        pregunta,
        contexto=contexto,
    )

    return Response({
        "ok": True,
        **resultado,
    })


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def buscar_hospitales(request):
    q = str(request.query_params.get("q", "")).strip()
    if len(q) < 3:
        return Response([])

    resultado = engine.buscador_hospital.buscar(q)

    if resultado["status"] == "ganador_claro":
        hospital = resultado["hospital"]
        return Response([
            {
                "id": hospital["id"],
                "nombre_original": hospital["desc_original"],
            }
        ])

    hospitales = [
        {
            "id": candidato["id"],
            "nombre_original": candidato["descripcion"],
        }
        for candidato in resultado.get("candidatos", [])
    ]
    return Response(hospitales)


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def buscar_variables(request):
    q = str(request.query_params.get("q", "")).strip()
    if len(q) < 3:
        return Response([])

    texto_variable = engine.buscador_variable._preparar_texto(q)
    variable_canonica = engine.buscador_variable.buscar_variable_canonica(texto_variable)
    resultado = engine.buscador_variable.buscar(q, aplicar_canonica=False)

    if resultado["status"] == "ganador_claro":
        variable = resultado["variable"]
        variables = [
            {
                "id": variable["id"],
                "descripcion": variable.get("descripcion") or variable.get("desc_original"),
            }
        ]
    else:
        variables = [
            {
                "id": candidato["id"],
                "descripcion": candidato["descripcion"],
            }
            for candidato in resultado.get("candidatos", [])
        ]

    if variable_canonica:
        sugerencia_canonica = {
            "id": variable_canonica["id"],
            "descripcion": variable_canonica.get("descripcion") or variable_canonica.get("desc_original"),
        }
        variables = [
            variable
            for variable in variables
            if str(variable["id"]) != str(sugerencia_canonica["id"])
        ]
        variables.insert(0, sugerencia_canonica)

    return Response(variables)
