import csv
import os
from datetime import datetime
from datetime import datetime as dt
from zoneinfo import ZoneInfo

from django.conf import settings
from django.http import FileResponse
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


BITACORA_NOMBRE = "bitacora_operaciones.csv"
BITACORA_NOMBRE_LEGACY = "bitacora_operaciones.txt"
BITACORA_HEADERS = [
    "inicio_operaciones",
    "clave_presupuestal",
    "fecha_inicio_operaciones",
    "region",
    "entidad",
    "unidad",
]


def _ruta_bitacora() -> str:
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
    return os.path.join(settings.MEDIA_ROOT, BITACORA_NOMBRE)


def _ruta_bitacora_legacy() -> str:
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
    return os.path.join(settings.MEDIA_ROOT, BITACORA_NOMBRE_LEGACY)


def _parsear_linea_legacy(linea: str):
    partes = [parte.strip() for parte in linea.strip().split("|") if parte.strip()]
    if len(partes) < 3:
        return None

    fila = {
        "inicio_operaciones": partes[0],
        "clave_presupuestal": "",
        "fecha_inicio_operaciones": "",
        "region": "",
        "entidad": "",
        "unidad": "",
    }

    for parte in partes[1:]:
        if "=" not in parte:
            continue
        clave, valor = parte.split("=", 1)
        clave = clave.strip()
        valor = valor.strip()
        if clave in fila:
            fila[clave] = valor

    if not fila["clave_presupuestal"] or not fila["fecha_inicio_operaciones"]:
        return None

    return fila


def _asegurar_bitacora_csv():
    bitacora_csv = _ruta_bitacora()
    bitacora_legacy = _ruta_bitacora_legacy()

    if os.path.isfile(bitacora_csv):
        if os.path.getsize(bitacora_csv) == 0:
            with open(bitacora_csv, "w", newline="", encoding="utf-8") as archivo_csv:
                writer = csv.DictWriter(archivo_csv, fieldnames=BITACORA_HEADERS)
                writer.writeheader()
        return bitacora_csv

    filas_legacy = []
    if os.path.isfile(bitacora_legacy):
        with open(bitacora_legacy, "r", encoding="utf-8") as archivo_legacy:
            for linea in archivo_legacy:
                fila = _parsear_linea_legacy(linea)
                if fila:
                    filas_legacy.append(fila)

    with open(bitacora_csv, "w", newline="", encoding="utf-8") as archivo_csv:
        writer = csv.DictWriter(archivo_csv, fieldnames=BITACORA_HEADERS)
        writer.writeheader()
        if filas_legacy:
            writer.writerows(filas_legacy)

    return bitacora_csv


def _validar_password_descarga(request):
    password_esperada = str(getattr(settings, "DOWNLOAD_PASSWORD", "imss2026"))
    password_recibida = str(
        request.headers.get("X-Download-Password")
        or request.query_params.get("pwd", "")
    ).strip()

    if not password_recibida:
        return Response({"ok": False, "message": "Se requiere contraseña para descargar."}, status=401)

    if password_recibida != password_esperada:
        return Response({"ok": False, "message": "Contraseña incorrecta."}, status=403)

    return None


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def guardar_inicio_operaciones(request):
    clave_presupuestal = str(request.data.get("clave_presupuestal", "")).strip()
    fecha_inicio_operaciones = str(request.data.get("fecha_inicio_operaciones", "")).strip()
    region = str(request.data.get("region", "")).strip()
    entidad = str(request.data.get("entidad", "")).strip()
    unidad = str(request.data.get("unidad", "")).strip()

    faltantes = [
        k
        for k, v in {
            "clave_presupuestal": clave_presupuestal,
            "fecha_inicio_operaciones": fecha_inicio_operaciones,
        }.items()
        if not v
    ]
    if faltantes:
        return Response({"ok": False, "message": f"Faltan campos: {', '.join(faltantes)}"}, status=400)

    try:
        fecha_formateada = dt.strptime(fecha_inicio_operaciones, "%Y-%m-%d").date().isoformat()
    except ValueError:
        return Response(
            {"ok": False, "message": "La fecha debe tener formato YYYY-MM-DD."},
            status=400,
        )

    bitacora_path = _asegurar_bitacora_csv()
    marca_tiempo = datetime.now(ZoneInfo("America/Mexico_City")).strftime("%Y-%m-%d %H:%M:%S")

    with open(bitacora_path, "a", newline="", encoding="utf-8") as bitacora:
        writer = csv.DictWriter(bitacora, fieldnames=BITACORA_HEADERS)
        writer.writerow(
            {
                "inicio_operaciones": marca_tiempo,
                "clave_presupuestal": clave_presupuestal,
                "fecha_inicio_operaciones": fecha_formateada,
                "region": region,
                "entidad": entidad,
                "unidad": unidad,
            }
        )

    return Response(
        {
            "ok": True,
            "message": "Registro guardado en bitacora.",
        }
    )


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def descargar_bitacora(request):
    error_password = _validar_password_descarga(request)
    if error_password:
        return error_password

    bitacora_path = _asegurar_bitacora_csv()
    return FileResponse(
        open(bitacora_path, "rb"),
        as_attachment=True,
        filename=BITACORA_NOMBRE,
        content_type="text/csv; charset=utf-8",
    )
