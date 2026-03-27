from django.http import HttpResponse
from django.db import connection
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from xml.sax.saxutils import escape
from django.db import transaction
import pandas as pd

from .serializers import (
    AreaSerializer,
    TemaSerializer,
    DiccionarioCampoSerializer
)


@api_view(["GET"])
def areas(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id_area, nombre, descripcion
            FROM cat_area
            WHERE activo = 1
            ORDER BY nombre
        """)
        rows = cursor.fetchall()

    data = [
        {
            "id_area": r[0],
            "nombre": r[1],
            "descripcion": r[2],
        }
        for r in rows
    ]

    return Response(data)

@api_view(["GET"])
def temas(request):
    id_area = request.GET.get("id_area")

    if not id_area:
        return Response([], status=200)

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id_tema, id_area, nombre, descripcion, tabla_destino, modo_carga
            FROM cat_tema
            WHERE activo = 1
              AND id_area = %s
            ORDER BY nombre
        """, [id_area])

        rows = cursor.fetchall()

    data = [
        {
            "id_tema": r[0],
            "id_area": r[1],
            "nombre": r[2],
            "descripcion": r[3],
            "tabla_destino": r[4],
            "modo_carga": r[5],
        }
        for r in rows
    ]

    return Response(data)

@api_view(["GET"])
def diccionario(request):
    id_tema = request.GET.get("id_tema")

    if not id_tema:
        return Response([], status=200)

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT
                id_campo,
                columna_excel,
                columna_bd,
                tipo_dato,
                longitud,
                obligatorio,
                orden
            FROM cat_diccionario_campo
            WHERE activo = 1
              AND id_tema = %s
            ORDER BY orden
        """, [id_tema])

        rows = cursor.fetchall()

    data = [
        {
            "id_campo": r[0],
            "columna_excel": r[1],
            "columna_bd": r[2],
            "tipo_dato": r[3],
            "longitud": r[4],
            "obligatorio": bool(r[5]),
            "orden": r[6],
        }
        for r in rows
    ]

    return Response(data)

    
# Mario: consulta de entidades.
@api_view(["GET"])
def entidades(request):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select distinct desc_edo_NomPropio
            from [dbo].[Cat_Entidad]  ORDER BY desc_edo_NomPropio
            """
        )
        rows = cursor.fetchall()

    data = [{"nombre": r[0]} for r in rows]
    return Response(data)
    # Mario: Termina consulta de entidades.


#Mario: Inicio endpoint guardar/consultar bitacora de revision.
@api_view(["GET", "POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def guardar_bitacora_revision(request):
    #Mario: Inicio consulta de bitacora por presentacion y objeto base.
    if request.method == "GET":
        id_presentacion = str(request.query_params.get("id_presentacion", "")).strip()
        id_objeto_base = str(request.query_params.get("id_objeto_base", "")).strip()

        if not id_presentacion or not id_objeto_base:
            return Response(
                {
                    "ok": False,
                    "message": "Parámetros faltantes",
                    "faltantes": [
                        key
                        for key, value in {
                            "id_presentacion": id_presentacion,
                            "id_objeto_base": id_objeto_base,
                        }.items()
                        if not value
                    ],
                },
                status=400,
            )

        like_pattern = f"{id_objeto_base}_%"

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT [ID_objeto], [Comentario], [Estatus]
                FROM [dbo].[sistema_bitacora]
                WHERE [ID_presentacion] = %s
                  AND [ID_objeto] LIKE %s
                ORDER BY [ID_objeto]
                """,
                [id_presentacion, like_pattern],
            )
            rows = cursor.fetchall()

        por_pagina = {}
        for row in rows:
            id_objeto = str(row[0] or "").strip()
            comentario = str(row[1] or "").strip()
            estatus = str(row[2] or "").strip()

            if "_" not in id_objeto:
                continue

            pagina_txt = id_objeto.rsplit("_", 1)[1]
            if not pagina_txt.isdigit():
                continue

            pagina = int(pagina_txt)
            por_pagina[pagina] = {
                "pagina": pagina,
                "id_objeto": id_objeto,
                "comentario": comentario,
                "estatus": estatus,
            }

        data = [por_pagina[p] for p in sorted(por_pagina.keys())]
        return Response({"ok": True, "items": data})
    #Mario: Fin consulta de bitacora por presentacion y objeto base.

    #Mario: Inicio guardado de bitacora por pagina.
    payload = request.data if isinstance(request.data, dict) else {}

    id_registro = str(payload.get("id", "")).strip()
    id_user = str(payload.get("id_user", "")).strip()
    id_presentacion = str(payload.get("id_presentacion", "")).strip()
    id_objeto = str(payload.get("id_objeto", "")).strip()
    comentario = str(payload.get("comentario", "")).strip()
    estatus = str(payload.get("estatus", "")).strip()

    faltantes = []
    if not id_registro:
        faltantes.append("id")
    if not id_user:
        faltantes.append("id_user")
    if not id_presentacion:
        faltantes.append("id_presentacion")
    if not id_objeto:
        faltantes.append("id_objeto")
    if not estatus:
        faltantes.append("estatus")

    if faltantes:
        return Response(
            {"ok": False, "message": "Campos faltantes", "faltantes": faltantes},
            status=400,
        )

    accion = "guardada"
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT TOP 1 1
            FROM [dbo].[sistema_bitacora]
            WHERE [ID] = %s
              AND [Id_user] = %s
              AND [ID_presentacion] = %s
              AND [ID_objeto] = %s
            """,
            [id_registro, id_user, id_presentacion, id_objeto],
        )
        existe = cursor.fetchone() is not None

        if existe:
            cursor.execute(
                """
                UPDATE [dbo].[sistema_bitacora]
                SET [Comentario] = %s,
                    [Estatus] = %s
                WHERE [ID] = %s
                  AND [Id_user] = %s
                  AND [ID_presentacion] = %s
                  AND [ID_objeto] = %s
                """,
                [comentario, estatus, id_registro, id_user, id_presentacion, id_objeto],
            )
            accion = "actualizada"
        else:
            cursor.execute(
                """
                INSERT INTO [dbo].[sistema_bitacora]
                ([ID], [Id_user], [ID_presentacion], [ID_objeto], [Comentario], [Estatus])
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                [id_registro, id_user, id_presentacion, id_objeto, comentario, estatus],
            )

    return Response({"ok": True, "message": f"Revisión {accion}"})
    #Mario: Fin guardado de bitacora por pagina.
#Mario: Fin endpoint guardar/consultar bitacora de revision.


#Mario: Inicio endpoint reporte excel de revision.
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def generar_reporte_excel_revision(request):
    payload = request.data if isinstance(request.data, dict) else {}

    id_user = str(payload.get("id_user", "")).strip()
    id_presentacion = str(payload.get("id_presentacion", "")).strip()
    id_objeto_base = str(payload.get("id_objeto_base", "")).strip()
    revisiones = payload.get("revisiones", [])

    faltantes = []
    if not id_user:
        faltantes.append("id_user")
    if not id_presentacion:
        faltantes.append("id_presentacion")
    if not id_objeto_base:
        faltantes.append("id_objeto_base")
    if not isinstance(revisiones, list) or len(revisiones) == 0:
        faltantes.append("revisiones")

    if faltantes:
        return Response(
            {"ok": False, "message": "Campos faltantes", "faltantes": faltantes},
            status=400,
        )

    filas_xml = []
    for index, item in enumerate(revisiones, start=1):
        revision = item if isinstance(item, dict) else {}
        comentario = escape(str(revision.get("comentario", "") or ""))
        estatus_raw = str(revision.get("estatus", "") or "").strip().lower()
        resultado = "Aprobada" if estatus_raw == "correcta" else "Rechazada"
        id_objeto = escape(f"{id_objeto_base}_{index}")

        filas_xml.append(
            """
            <Row>
              <Cell><Data ss:Type=\"String\">{lamina}</Data></Cell>
              <Cell><Data ss:Type=\"String\">{id_user}</Data></Cell>
              <Cell><Data ss:Type=\"String\">{presentacion}</Data></Cell>
              <Cell><Data ss:Type=\"String\">{id_objeto}</Data></Cell>
              <Cell><Data ss:Type=\"String\">{comentario}</Data></Cell>
              <Cell><Data ss:Type=\"String\">{resultado}</Data></Cell>
            </Row>
            """.format(
                lamina=index,
                id_user=escape(id_user),
                presentacion=escape(id_presentacion),
                id_objeto=id_objeto,
                comentario=comentario,
                resultado=escape(resultado),
            )
        )

    contenido = f"""<?xml version=\"1.0\"?>
<Workbook xmlns=\"urn:schemas-microsoft-com:office:spreadsheet\"
 xmlns:o=\"urn:schemas-microsoft-com:office:office\"
 xmlns:x=\"urn:schemas-microsoft-com:office:excel\"
 xmlns:ss=\"urn:schemas-microsoft-com:office:spreadsheet\">
  <Worksheet ss:Name=\"ReporteRevision\">
    <Table>
      <Row>
        <Cell><Data ss:Type=\"String\">Lámina</Data></Cell>
        <Cell><Data ss:Type=\"String\">ID usuario</Data></Cell>
        <Cell><Data ss:Type=\"String\">Presentación</Data></Cell>
        <Cell><Data ss:Type=\"String\">ID objeto</Data></Cell>
        <Cell><Data ss:Type=\"String\">Comentario</Data></Cell>
        <Cell><Data ss:Type=\"String\">Resultado</Data></Cell>
      </Row>
      {''.join(filas_xml)}
    </Table>
  </Worksheet>
</Workbook>"""

    response = HttpResponse(contenido, content_type="application/vnd.ms-excel; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="reporte_revision_{id_objeto_base}.xls"'
    return response
#Mario: Fin endpoint reporte excel de revision.

@api_view(["POST"])
def subir_excel(request):
    
    archivo = request.FILES.get("file")
    id_tema = request.POST.get("id_tema")
    hoja = request.POST.get("hoja")

    print("FILES:", request.FILES)

    if not archivo:
        print("❌ No llegó archivo")
        return Response({"error": "No se envió archivo"}, status=400)

    try:
        print("📄 Nombre:", archivo.name, flush=True)
        

        # df = pd.read_excel(archivo, engine="openpyxl")
        df = pd.read_excel(archivo, sheet_name=hoja, engine="openpyxl")
        df.columns = df.columns.str.strip()
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT columna_excel, columna_bd, obligatorio, tipo_dato, longitud
                FROM cat_diccionario_campo
                WHERE id_tema = %s AND activo = 1
            """, [id_tema])            

            dic = cursor.fetchall()
            columnas_esperadas = [d[0] for d in dic]  # columna_excel
        #
        columnas_excel = list(df.columns)
        faltantes_estructura  = [c for c in columnas_esperadas if c not in columnas_excel]
        extras = [c for c in columnas_excel if c not in columnas_esperadas]
        print("ANTES DE VALIDACIONES")
        if faltantes_estructura  or extras:
            return Response({
                "error": "Estructura de columnas inválida",
                "faltantes": faltantes_estructura ,
                "extras": extras,
                "columnas_esperadas": columnas_esperadas
            }, status=400)     
           
        dic_tipos = {
            d[1]: {
                "excel": d[0],
                "obligatorio": d[2],
                "tipo": d[3],
                "longitud": d[4]
            }
            for d in dic
        }    
        map_bd = {d[0]: d[1] for d in dic}




        df = df.rename(columns=map_bd)
        filas = df.to_dict(orient="records")
        #
        errores = []

        for i, fila in enumerate(filas, start=1):
            for col_bd, value in fila.items():
                config = dic_tipos.get(col_bd)

                if not config:
                    continue

                #  obligatorio
                if config["obligatorio"] and (value is None or str(value).strip() == ""):
                    errores.append({
                        "fila": i,
                        "columna": config["excel"],
                        "error": "Campo obligatorio vacío"
                    })
                    continue

                #  tipo entero
                if config["tipo"] == "int":
                    try:
                        int(value)
                    except:
                        errores.append({
                            "fila": i,
                            "columna": config["excel"],
                            "error": f"Valor inválido: {value}"
                        })

                #  tipo decimal
                elif config["tipo"] == "decimal":
                    try:
                        float(value)
                    except:
                        errores.append({
                            "fila": i,
                            "columna": config["excel"],
                            "error": f"Debe ser numérico: {value}"
                        })

                #  tipo fecha
                elif config["tipo"] == "date":
                    try:
                        pd.to_datetime(value)
                    except:
                        errores.append({
                            "fila": i,
                            "columna": config["excel"],
                            "error": f"Fecha inválida: {value}"
                        })      
                if config.get("longitud") and len(str(value)) > config["longitud"]:
                    errores.append({
                        "fila": i,
                        "columna": config["excel"],
                        "error": f"Excede longitud {config['longitud']}"
                    })                          
        #
        if errores:
            return Response({
                "error": "Errores de validación",
                "detalle": errores[:20],
                "total_errores": len(errores)
            }, status=400)        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT tabla_destino, modo_carga
                FROM cat_tema
                WHERE id_tema = %s
            """, [id_tema])

            tabla, modo_carga = cursor.fetchone()
            tabla = f"[{tabla}]"
            # filas = df.to_dict(orient="records")

        with transaction.atomic():
            with connection.cursor() as cursor:
                print("dos", flush=True)
                if modo_carga == "REPLACE":
                    cursor.execute(f"DELETE FROM {tabla}")
                if not filas:
                    return Response({"error": "El archivo no contiene registros"}, status=400)
                cols = ", ".join([f"[{c}]" for c in filas[0].keys()])
                vals = ", ".join(["%s"] * len(filas[0]))

                sql = f"INSERT INTO {tabla} ({cols}) VALUES ({vals})"

                data = [list(f.values()) for f in filas]

                cursor.executemany(sql, data)   
                print("tres", flush=True)
        #
        print("Excel leído, filas:", len(df))

        return Response({
            "columnas": list(df.columns),
            "filas": df.to_dict(orient="records")[:10],
            "total_registros": len(df)
        })

    except Exception as e:
        import traceback
        print("ERROR:")
        traceback.print_exc()

        return Response({"error": str(e)}, status=500)
    
@api_view(["POST"])
def obtener_hojas_excel(request):
    archivo = request.FILES.get("file")

    if not archivo:
        return Response({"error": "No se envió archivo"}, status=400)

    try:
        xls = pd.ExcelFile(archivo, engine="openpyxl")
        hojas = xls.sheet_names

        return Response({
            "hojas": hojas
        })

    except Exception as e:
        return Response({"error": str(e)}, status=500)