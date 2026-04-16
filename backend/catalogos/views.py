import csv
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from django.conf import settings
from django.http import FileResponse
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


BITACORA_NOMBRE = "bitacora_operaciones.csv"
BITACORA_NOMBRE_LEGACY = "bitacora_operaciones.txt"
BITACORA_HEADERS = [
    "registro",
    "delegacion",
    "titular_unidad",
    "nombre_usuario",
    "cargo_usuario",
    "correo_institucional",
    "correo_personal",
    "telefono",
    "area",
    "tipo_cargo",
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
        "registro": partes[0],
        "delegacion": "",
        "titular_unidad": "",
        "nombre_usuario": "",
        "cargo_usuario": "",
        "correo_institucional": "",
        "correo_personal": "",
        "telefono": "",
        "area": "",
        "tipo_cargo": "",
    }

    equivalencias = {
        "inicio_operaciones": "registro",
        "region": "delegacion",
    }

    for parte in partes[1:]:
        if "=" not in parte:
            continue
        clave, valor = parte.split("=", 1)
        clave = clave.strip()
        valor = valor.strip()
        destino = equivalencias.get(clave, clave)
        if destino in fila:
            fila[destino] = valor

    return fila


def _normalizar_fila(fila):
    normalizada = {header: str(fila.get(header, "") or "").strip() for header in BITACORA_HEADERS}
    if not any(normalizada.values()):
        return None
    return normalizada


def _asegurar_bitacora_csv():
    bitacora_csv = _ruta_bitacora()
    bitacora_legacy = _ruta_bitacora_legacy()

    if os.path.isfile(bitacora_csv):
        if os.path.getsize(bitacora_csv) == 0:
            with open(bitacora_csv, "w", newline="", encoding="utf-8") as archivo_csv:
                writer = csv.DictWriter(archivo_csv, fieldnames=BITACORA_HEADERS)
                writer.writeheader()

        with open(bitacora_csv, "r", newline="", encoding="utf-8") as archivo_csv:
            reader = csv.DictReader(archivo_csv)
            headers_actuales = reader.fieldnames or []
            filas = [fila for fila in (_normalizar_fila(fila) for fila in reader) if fila]

        if headers_actuales != BITACORA_HEADERS:
            with open(bitacora_csv, "w", newline="", encoding="utf-8") as archivo_csv:
                writer = csv.DictWriter(archivo_csv, fieldnames=BITACORA_HEADERS)
                writer.writeheader()
                if filas:
                    writer.writerows(filas)

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
            writer.writerows(fila for fila in (_normalizar_fila(fila) for fila in filas_legacy) if fila)

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
    delegacion = str(request.data.get("delegacion", "")).strip()
    titular_unidad = str(request.data.get("titular_unidad", "")).strip()
    nombre_usuario = str(request.data.get("nombre_usuario", "")).strip()
    cargo_usuario = str(request.data.get("cargo_usuario", "")).strip()
    correo_institucional = str(request.data.get("correo_institucional", "")).strip()
    correo_personal = str(request.data.get("correo_personal", "")).strip()
    telefono = str(request.data.get("telefono", "")).strip()
    area = str(request.data.get("area", "")).strip()
    tipo_cargo = str(request.data.get("tipo_cargo", "")).strip()

    faltantes = [
        k
        for k, v in {
            "delegacion": delegacion,
            "titular_unidad": titular_unidad,
            "nombre_usuario": nombre_usuario,
            "cargo_usuario": cargo_usuario,
            "correo_institucional": correo_institucional,
            "correo_personal": correo_personal,
            "telefono": telefono,
            "area": area,
            "tipo_cargo": tipo_cargo,
        }.items()
        if not v
    ]
    if faltantes:
        return Response({"ok": False, "message": f"Faltan campos: {', '.join(faltantes)}"}, status=400)

    bitacora_path = _asegurar_bitacora_csv()
    marca_tiempo = datetime.now(ZoneInfo("America/Mexico_City")).strftime("%Y-%m-%d %H:%M:%S")

    with open(bitacora_path, "a", newline="", encoding="utf-8") as bitacora:
        writer = csv.DictWriter(bitacora, fieldnames=BITACORA_HEADERS)
        writer.writerow(
            {
                "registro": marca_tiempo,
                "delegacion": delegacion,
                "titular_unidad": titular_unidad,
                "nombre_usuario": nombre_usuario,
                "cargo_usuario": cargo_usuario,
                "correo_institucional": correo_institucional,
                "correo_personal": correo_personal,
                "telefono": telefono,
                "area": area,
                "tipo_cargo": tipo_cargo,
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
