from datetime import datetime
from zoneinfo import ZoneInfo
import os
import re
import unicodedata

from django.conf import settings
from django.http import FileResponse
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


TIPOS_FOTO_VALIDOS = {"fachada", "foto1", "foto2", "foto3", "foto4"}
EXTENSIONES_IMAGEN = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
TAMANO_MAXIMO_BYTES = 10 * 1024 * 1024  # 10 MB


def _slug(texto: str) -> str:
    texto = unicodedata.normalize("NFD", str(texto or ""))
    texto = texto.encode("ascii", "ignore").decode("ascii")
    texto = re.sub(r"[^a-zA-Z0-9]+", "_", texto).strip("_").lower()
    return texto


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def fotos_cargadas(request):
    clave_presupuestal = str(request.query_params.get("clave_presupuestal", "")).strip()
    region = str(request.query_params.get("region", "")).strip()
    entidad = str(request.query_params.get("entidad", "")).strip()
    unidad = str(request.query_params.get("unidad", "")).strip()

    faltantes = [
        k
        for k, v in {
            "clave_presupuestal": clave_presupuestal,
            "region": region,
            "entidad": entidad,
            "unidad": unidad,
        }.items()
        if not v
    ]
    if faltantes:
        return Response({"ok": False, "message": f"Faltan campos: {', '.join(faltantes)}"}, status=400)

    prefijo = f"{_slug(clave_presupuestal)}_{_slug(region)}_{_slug(entidad)}_{_slug(unidad)}"
    estado = {tipo: False for tipo in TIPOS_FOTO_VALIDOS}

    if os.path.isdir(settings.MEDIA_ROOT):
        for nombre in os.listdir(settings.MEDIA_ROOT):
            nombre_lower = nombre.lower()
            for tipo in TIPOS_FOTO_VALIDOS:
                if nombre_lower.startswith(f"{prefijo}_{tipo}."):
                    estado[tipo] = True

    return Response({"ok": True, "fotos": estado})


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def subir_foto(request):
    clave_presupuestal = str(request.POST.get("clave_presupuestal", "")).strip()
    region = str(request.POST.get("region", "")).strip()
    entidad = str(request.POST.get("entidad", "")).strip()
    unidad = str(request.POST.get("unidad", "")).strip()
    tipo = str(request.POST.get("tipo", "")).strip().lower()
    archivo = request.FILES.get("foto")

    faltantes = [
        k
        for k, v in {
            "clave_presupuestal": clave_presupuestal,
            "region": region,
            "entidad": entidad,
            "unidad": unidad,
            "tipo": tipo,
        }.items()
        if not v
    ]
    if faltantes:
        return Response({"ok": False, "message": f"Faltan campos: {', '.join(faltantes)}"}, status=400)

    if tipo not in TIPOS_FOTO_VALIDOS:
        return Response(
            {"ok": False, "message": f"Tipo invalido. Valores permitidos: {', '.join(sorted(TIPOS_FOTO_VALIDOS))}"},
            status=400,
        )

    if not archivo:
        return Response({"ok": False, "message": "No se envio ninguna imagen."}, status=400)

    ext = os.path.splitext(archivo.name)[1].lower()
    if ext not in EXTENSIONES_IMAGEN:
        return Response({"ok": False, "message": f"Extension no permitida: {ext}"}, status=400)

    if archivo.size > TAMANO_MAXIMO_BYTES:
        return Response({"ok": False, "message": "La imagen supera el tamaño maximo de 10 MB."}, status=400)

    nombre_archivo = f"{_slug(clave_presupuestal)}_{_slug(region)}_{_slug(entidad)}_{_slug(unidad)}_{tipo}{ext}"
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
    ruta_completa = os.path.join(settings.MEDIA_ROOT, nombre_archivo)

    with open(ruta_completa, "wb") as f:
        for chunk in archivo.chunks():
            f.write(chunk)

    bitacora_path = os.path.join(settings.MEDIA_ROOT, "bitacora_fotos.txt")
    marca_tiempo = datetime.now(ZoneInfo("America/Mexico_City")).strftime("%Y-%m-%d %H:%M:%S")
    with open(bitacora_path, "a", encoding="utf-8") as bitacora:
        bitacora.write(f"{marca_tiempo} | {nombre_archivo}\n")

    return Response(
        {
            "ok": True,
            "message": "Imagen guardada correctamente.",
            "archivo": nombre_archivo,
            "ruta": ruta_completa,
        }
    )


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def listar_fotos(request):
    fotos = []
    if os.path.isdir(settings.MEDIA_ROOT):
        for nombre in sorted(os.listdir(settings.MEDIA_ROOT)):
            if nombre == "bitacora_fotos.txt":
                continue
            ruta = os.path.join(settings.MEDIA_ROOT, nombre)
            if os.path.isfile(ruta):
                mtime = datetime.fromtimestamp(
                    os.path.getmtime(ruta), tz=ZoneInfo("America/Mexico_City")
                )
                fotos.append(
                    {
                        "nombre": nombre,
                        "bytes": os.path.getsize(ruta),
                        "fecha": mtime.strftime("%Y-%m-%d %H:%M:%S"),
                    }
                )
    return Response({"ok": True, "total": len(fotos), "fotos": fotos})


_NOMBRE_SEGURO = re.compile(r"^[a-zA-Z0-9._-]+$")


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def descargar_foto(request, nombre):
    if not nombre or not _NOMBRE_SEGURO.match(nombre):
        return Response({"ok": False, "message": "Nombre de archivo invalido."}, status=400)
    ruta = os.path.abspath(os.path.join(settings.MEDIA_ROOT, nombre))
    if not ruta.startswith(os.path.abspath(settings.MEDIA_ROOT) + os.sep):
        return Response({"ok": False, "message": "Acceso denegado."}, status=403)
    if not os.path.isfile(ruta):
        return Response({"ok": False, "message": "Foto no encontrada."}, status=404)
    return FileResponse(open(ruta, "rb"), as_attachment=True, filename=nombre)


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def descargar_bitacora(request):
    bitacora_path = os.path.join(settings.MEDIA_ROOT, "bitacora_fotos.txt")
    if not os.path.isfile(bitacora_path):
        return Response({"ok": False, "message": "La bitacora no existe aun."}, status=404)
    return FileResponse(
        open(bitacora_path, "rb"),
        as_attachment=True,
        filename="bitacora_fotos.txt",
        content_type="text/plain; charset=utf-8",
    )
