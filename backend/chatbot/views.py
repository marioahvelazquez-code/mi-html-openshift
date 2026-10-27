import logging

from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .chatbot import engine
from .autocompletado_variable import sugerir_variables


logger = logging.getLogger(__name__)

MESES_ES = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def fecha_corte_ifu(request):
    try:
        periodo = engine.consulta_ifu.obtener_fecha_corte()
    except Exception as error:
        logger.error(
            "No fue posible obtener la fecha de corte del IFU: %s",
            type(error).__name__,
        )
        return Response(
            {
                "error": (
                    "No fue posible obtener la fecha de corte del IFU."
                ),
            },
            status=503,
        )

    if not periodo:
        return Response(
            {
                "anio": None,
                "mes": None,
                "mes_nombre": None,
                "fecha_corte": None,
            }
        )

    anio = periodo["anio"]
    mes = periodo["mes"]
    mes_nombre = MESES_ES.get(mes)
    fecha_corte = (
        f"Fecha de corte del IFU, {mes_nombre} de {anio}"
        if mes_nombre
        else None
    )

    return Response(
        {
            "anio": anio,
            "mes": mes,
            "mes_nombre": mes_nombre,
            "fecha_corte": fecha_corte,
        }
    )


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
    resultado = sugerir_variables(engine.buscador_variable, q)
    if request.query_params.get("incluir_metadata") == "1":
        return Response(resultado)
    # Conserva el contrato de lista y sus campos para consumidores anteriores.
    return Response([
        {"id": item["id"], "descripcion": item["descripcion"]}
        for item in resultado["items"]
    ])
