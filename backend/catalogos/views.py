from django.db import connection
from django.http import HttpResponse
from html import escape
import re
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


def _resolver_autenticacion(payload):
    payload = payload if isinstance(payload, dict) else {}

    usuario = str(payload.get("usuario", "")).strip()
    contrasena = str(payload.get("contrasena", "")).strip()

    if not usuario or not contrasena:
        return Response(
            {"ok": False, "message": "Captura usuario y contrasena para continuar."},
            status=400,
        )

    query = """
        SELECT TOP 1 fld_cambio_pwd
        FROM [dbo].[cat_usuarios]
        WHERE UPPER(LTRIM(RTRIM(fld_claveUsuario))) = UPPER(LTRIM(RTRIM(%s)))
          AND LTRIM(RTRIM(fld_passwordUsuario)) = LTRIM(RTRIM(%s))
    """

    with connection.cursor() as cursor:
        cursor.execute(query, [usuario, contrasena])
        row = cursor.fetchone()

    if row is None:
        return Response(
            {"ok": False, "message": "Usuario o contrasena incorrectos."},
            status=401,
        )

    valor_cambio_pwd = row[0]
    valor_cambio_pwd_txt = str(valor_cambio_pwd).strip().upper()
    requiere_cambio_pwd = valor_cambio_pwd_txt in {"1", "S", "SI", "TRUE", "T", "Y", "YES"}

    return Response(
        {
            "ok": True,
            "message": "Autenticacion correcta.",
            "requiere_cambio_pwd": requiere_cambio_pwd,
            "usuario": usuario,
        }
    )


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def autenticar_usuario(request):
    return _resolver_autenticacion(request.data)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def cambiar_password_primer_ingreso(request):
    payload = request.data if isinstance(request.data, dict) else {}

    usuario = str(payload.get("usuario", "")).strip()
    contrasena_actual = str(payload.get("contrasena_actual", "")).strip()
    nueva_contrasena = str(payload.get("nueva_contrasena", "")).strip()

    if not usuario or not contrasena_actual or not nueva_contrasena:
        return Response(
            {"ok": False, "message": "Usuario, contrasena actual y nueva contrasena son obligatorios."},
            status=400,
        )

    if contrasena_actual == nueva_contrasena:
        return Response(
            {"ok": False, "message": "La nueva contrasena debe ser diferente a la actual."},
            status=400,
        )

    query = """
        UPDATE [dbo].[cat_usuarios]
           SET fld_passwordUsuario = %s,
               fld_cambio_pwd = 0
         WHERE UPPER(LTRIM(RTRIM(fld_claveUsuario))) = UPPER(LTRIM(RTRIM(%s)))
           AND LTRIM(RTRIM(fld_passwordUsuario)) = LTRIM(RTRIM(%s))
    """

    with connection.cursor() as cursor:
        cursor.execute(query, [nueva_contrasena, usuario, contrasena_actual])
        filas_actualizadas = cursor.rowcount

    if filas_actualizadas <= 0:
        return Response(
            {"ok": False, "message": "No fue posible actualizar la contrasena. Verifica tus datos."},
            status=400,
        )

    return Response({"ok": True, "message": "Contrasena actualizada correctamente."})


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def login_usuarios(request):
    # Alias de compatibilidad para no romper clientes anteriores.
    return _resolver_autenticacion(request.data)


ENTIDADES_FEDERATIVAS = [
    "Aguascalientes", "Baja California", "Baja California Sur", "Campeche", "Coahuila", "Colima",
    "Chiapas", "Chihuahua", "Ciudad de Mexico", "Durango", "Guanajuato", "Guerrero", "Hidalgo",
    "Jalisco", "Estado de Mexico", "Michoacan", "Morelos", "Nayarit", "Nuevo Leon", "Oaxaca",
    "Puebla", "Queretaro", "Quintana Roo", "San Luis Potosi", "Sinaloa", "Sonora", "Tabasco",
    "Tamaulipas", "Tlaxcala", "Veracruz", "Yucatan", "Zacatecas",
]


def _extraer_pagina(id_objeto):
    match = re.search(r"_(\d+)$", str(id_objeto or ""))
    if not match:
        return None
    return int(match.group(1))


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def listar_entidades(request):
    return Response([{"nombre": entidad} for entidad in ENTIDADES_FEDERATIVAS])


@api_view(["GET", "POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def bitacora_revision(request):
    if request.method == "POST":
        payload = request.data if isinstance(request.data, dict) else {}
        id_catalogo = str(payload.get("id", "")).strip()
        id_user = str(payload.get("id_user", "")).strip()
        id_presentacion = str(payload.get("id_presentacion", "")).strip()
        id_objeto = str(payload.get("id_objeto", "")).strip()
        comentario = str(payload.get("comentario", "")).strip()
        estatus = str(payload.get("estatus", "")).strip()

        if not id_user or not id_presentacion or not id_objeto or not estatus:
            return Response(
                {"ok": False, "message": "id_user, id_presentacion, id_objeto y estatus son obligatorios."},
                status=400,
            )

        query_update = """
            UPDATE dbo.sistema_bitacora
               SET Comentario = %s,
                   Estatus = %s,
                   fecha = SYSDATETIME(),
                   ID = %s
             WHERE Id_user = %s
               AND ID_presentacion = %s
               AND ID_objeto = %s
        """
        query_insert = """
            INSERT INTO dbo.sistema_bitacora (ID, Id_user, ID_presentacion, ID_objeto, Comentario, Estatus, fecha)
            VALUES (%s, %s, %s, %s, %s, %s, SYSDATETIME())
        """

        try:
            with connection.cursor() as cursor:
                cursor.execute(query_update, [comentario, estatus, id_catalogo, id_user, id_presentacion, id_objeto])
                if cursor.rowcount == 0:
                    cursor.execute(query_insert, [id_catalogo, id_user, id_presentacion, id_objeto, comentario, estatus])
        except Exception as exc:
            return Response(
                {"ok": False, "message": "No se pudo guardar la revision en base de datos.", "detail": str(exc)},
                status=503,
            )

        return Response({"ok": True, "message": "Revision guardada correctamente."})


    id_user = str(request.query_params.get("id_user", "")).strip()
    id_presentacion = str(request.query_params.get("id_presentacion", "")).strip()
    id_objeto_base = str(request.query_params.get("id_objeto_base", "")).strip()

    print("[DEBUG] bitacora_revision params:", {
        "id_user": id_user,
        "id_presentacion": id_presentacion,
        "id_objeto_base": id_objeto_base
    })


    if not id_user or not id_presentacion or not id_objeto_base:
        return Response(
            {"ok": False, "message": "id_user, id_presentacion e id_objeto_base son obligatorios."},
            status=400,
        )

    like_pattern = f"{id_objeto_base}_%"
    query = """
        SELECT ID_objeto, Estatus, Comentario
        FROM dbo.sistema_bitacora
        WHERE ID_presentacion = %s
        AND ID_objeto LIKE %s
        ORDER BY fecha DESC
    """
    print(f"[DEBUG] bitacora_revision SQL: {query.strip()} | params: [{id_presentacion}, {like_pattern}]")

    try:
        with connection.cursor() as cursor:
            cursor.execute(query, [id_presentacion, like_pattern])
            rows = cursor.fetchall()
    except Exception as exc:
        return Response(
            {"ok": False, "message": "No se pudo consultar la bitacora.", "detail": str(exc)},
            status=503,
        )

    vistos = set()
    items = []
    for id_objeto, estatus, comentario in rows:
        pagina = _extraer_pagina(id_objeto)
        if pagina is None or pagina in vistos:
            continue
        vistos.add(pagina)
        items.append(
            {
                "pagina": pagina,
                "estatus": str(estatus or ""),
                "comentario": str(comentario or ""),
            }
        )

    items.sort(key=lambda item: item["pagina"])
    return Response({"ok": True, "items": items})


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def reporte_excel_bitacora(request):
    payload = request.data if isinstance(request.data, dict) else {}
    revisiones = payload.get("revisiones")
    id_presentacion = str(payload.get("id_presentacion", "")).strip() or "sin_presentacion"
    id_objeto_base = str(payload.get("id_objeto_base", "")).strip() or "sin_objeto"

    if not isinstance(revisiones, list):
        return Response({"ok": False, "message": "revisiones debe ser una lista."}, status=400)

    filas = []
    for indice, revision in enumerate(revisiones, start=1):
        if not isinstance(revision, dict):
            continue
        estatus = str(revision.get("estatus", "")).strip()
        comentario = str(revision.get("comentario", "")).strip()
        if not estatus and not comentario:
            continue
        filas.append((indice, estatus, comentario))

    html = [
        "<html><head><meta charset='utf-8'></head><body>",
        f"<h3>Reporte de revision: {escape(id_objeto_base)} ({escape(id_presentacion)})</h3>",
        "<table border='1'>",
        "<tr><th>Pagina</th><th>Estatus</th><th>Comentario</th></tr>",
    ]
    for pagina, estatus, comentario in filas:
        html.append(
            "<tr>"
            f"<td>{pagina}</td>"
            f"<td>{escape(estatus)}</td>"
            f"<td>{escape(comentario)}</td>"
            "</tr>"
        )
    html.append("</table></body></html>")

    response = HttpResponse("".join(html), content_type="application/vnd.ms-excel; charset=utf-8")
    response["Content-Disposition"] = f"attachment; filename=reporte_revision_{id_objeto_base}.xls"
    return response
