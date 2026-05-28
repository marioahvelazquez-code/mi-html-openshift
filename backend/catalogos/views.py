from django.http import HttpResponse, JsonResponse
from django.db import connection
from django.db import transaction
from django.utils import timezone
from xml.sax.saxutils import escape
from pathlib import Path
from zoneinfo import ZoneInfo
import subprocess
import pandas as pd
import requests

from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication


# Mario: Función para resolver archivos de ficha nacional dinámicamente por prefijo.
def _resolver_archivos_ficha_nacional():
    carpeta_montada = Path('/app/frontend-public/nacional')
    raiz_repo = Path(__file__).resolve().parents[2]
    carpeta_local = raiz_repo / 'frontend-angular' / 'app' / 'public' / 'nacional'
    carpeta_nacional = carpeta_montada if carpeta_montada.exists() else carpeta_local

    if not carpeta_nacional.exists() or not carpeta_nacional.is_dir():
        raise FileNotFoundError(f'No existe la carpeta nacional: {carpeta_nacional}')

    archivos = [archivo for archivo in carpeta_nacional.iterdir() if archivo.is_file()]

    def seleccionar(prefix: str, extensiones: tuple[str, ...]) -> str | None:
        candidatos = [
            archivo for archivo in archivos
            if archivo.name.lower().startswith(prefix.lower())
            and archivo.suffix.lower() in extensiones
        ]
        if not candidatos:
            return None
        candidatos.sort(key=lambda archivo: archivo.stat().st_mtime, reverse=True)
        return candidatos[0].name

    return {
        'pdf': seleccionar('ficha_nacional', ('.pdf',)),
        'pptx': seleccionar('ficha_nacional', ('.pptx', '.ppt')),
    }


# Mario: Función para resolver archivos de fichas estatales dinámicamente agrupados por prefijo (FE_XX_CLAVE).
def _resolver_archivos_fichas_estatales():
    carpeta_montada = Path('/app/frontend-public/fichas')
    raiz_repo = Path(__file__).resolve().parents[2]
    carpeta_local = raiz_repo / 'frontend-angular' / 'app' / 'public' / 'fichas'
    carpeta_estatales = carpeta_montada if carpeta_montada.exists() else carpeta_local

    if not carpeta_estatales.exists() or not carpeta_estatales.is_dir():
        raise FileNotFoundError(f'No existe la carpeta de fichas estatales: {carpeta_estatales}')

    archivos = [archivo for archivo in carpeta_estatales.iterdir() if archivo.is_file()]
    por_prefijo = {}

    for archivo in archivos:
        nombre = archivo.name
        partes = nombre.split('_')
        if len(partes) < 4:
            continue

        prefijo = '_'.join(partes[:3]).upper()
        if not prefijo.startswith('FE_'):
            continue

        extension = archivo.suffix.lower()
        if extension not in ('.pdf', '.pptx', '.ppt'):
            continue

        registro = por_prefijo.setdefault(
            prefijo,
            {
                'prefix': prefijo,
                'pdf': None,
                'pptx': None,
                '_pdf_mtime': -1,
                '_pptx_mtime': -1,
            },
        )

        mtime = archivo.stat().st_mtime

        if extension == '.pdf' and mtime > registro['_pdf_mtime']:
            registro['pdf'] = nombre
            registro['_pdf_mtime'] = mtime

        if extension in ('.pptx', '.ppt') and mtime > registro['_pptx_mtime']:
            registro['pptx'] = nombre
            registro['_pptx_mtime'] = mtime

    items = []
    for item in por_prefijo.values():
        items.append(
            {
                'prefix': item['prefix'],
                'pdf': item['pdf'],
                'pptx': item['pptx'],
            }
        )

    items.sort(key=lambda x: x['prefix'])
    return items


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def ficha_nacional_archivos(request):
    try:
        archivos = _resolver_archivos_ficha_nacional()
        return Response({"ok": True, **archivos})
    except Exception as exc:
        return Response(
            {"ok": False, "message": "No se pudieron resolver los archivos de ficha nacional.", "detail": str(exc)},
            status=503,
        )


# Mario: Endpoint para consultar dinámicamente los archivos de fichas estatales disponibles.
@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def ficha_estatales_archivos(request):
    try:
        items = _resolver_archivos_fichas_estatales()
        return Response({"ok": True, "items": items})
    except Exception as exc:
        return Response(
            {
                "ok": False,
                "message": "No se pudieron resolver los archivos de fichas estatales.",
                "detail": str(exc),
            },
            status=503,
        )

def autenticar_ad(usuario, password):
    url = "http://serviciosdigitalesinterno-stage.imss.gob.mx/serviciosDigitales-rest/v1/externos/directorioActivo/usuario/autentica"

    payload = {
        "claveUsusaio": usuario,
        "dominio": "metro",
        "password": password
    }

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    # print("Payload enviado:", payload, flush=True)

    try:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=50
        )

        # print("Status:", response.status_code, flush=True)
        # print("Respuesta:", response.text, flush=True)

        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as e:
        # print("Error AD:", e, flush=True)
        return False

    

@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def autenticar_usuario(request):

    payload = request.data if isinstance(request.data, dict) else {}

    usuario = str(payload.get("usuario", "")).strip()
    contrasena = str(payload.get("contrasena", "")).strip()

    

    if not usuario or not contrasena:
        return Response(
            {"ok": False, "message": "Captura usuario y contraseña."},
            status=400,
        )

    es_valido =  autenticar_ad(usuario, contrasena)
    if not es_valido:
        return Response(
            {"ok": False, "message": "Usuario y contraseña incorrectos."},
            status=401,
        )
    # print("Datos regresado:", es_valido, flush=True)
    # correo = es_valido.get('correo')
    # nombre = es_valido.get('nombre')
    # primerApellido = es_valido.get('primerApellido')
    # segundoApellido = es_valido.get('segundoApellido')

    if not es_valido:
        return Response(
            {"ok": False, "message": "Usuario y contraseña incorrectos."},
            status=400,
        )

    query = """
        SELECT TOP 1 pk_idUsuario, fld_cambio_pwd
        FROM [dbo].[cat_usuarios]
        WHERE UPPER(LTRIM(RTRIM(fld_claveUsuario))) = UPPER(LTRIM(RTRIM(%s)))
          
    """

    with connection.cursor() as cursor:
        cursor.execute(query, [usuario])
        row = cursor.fetchone()

    if row is None:
        return Response(
            {"ok": False, "message": "El Usuario no cuenta con los roles para acceder a la aplicación. Contacta al administrador."},
            status=401,
        )

    #  GENERAR TOKEN
    id_usuario = row[0]

    user, _ = User.objects.get_or_create(username=usuario)
    refresh = RefreshToken.for_user(user)
    refresh["id_usuario"] = id_usuario  #  

    access_token = str(refresh.access_token)
    # 
 

    valor_cambio_pwd = row[1]
    valor_cambio_pwd_txt = str(valor_cambio_pwd).strip().upper()
    requiere_cambio_pwd = valor_cambio_pwd_txt in {"1", "S", "SI", "TRUE", "T", "Y", "YES"}

    return Response(
        {
            "ok": True,
            "message": "Autenticación correcta.",
            "usuario": usuario,
            "token": access_token,   # 
            "requiere_cambio_pwd": requiere_cambio_pwd,
        }
    )


@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
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
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
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
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
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
            select distinct cve_edo, desc_edo_NomPropio
            from [dbo].[cat_entidad]
            order by desc_edo_NomPropio
            """
        )
        rows = cursor.fetchall()

    data = [{"cve_edo": r[0], "nombre": r[1]} for r in rows]
    return Response(data)
    # Mario: Termina consulta de entidades.


#Mario: Inicio endpoint guardar/consultar bitacora de revision.
@api_view(["GET", "POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def guardar_bitacora_revision(request):
    #Mario: Inicio consulta de bitacora por presentacion y objeto base.
    if request.method == "GET":
        id_user = str(request.query_params.get("id_user", "")).strip()
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
            if id_user:
                cursor.execute(
                    """
                    SELECT [ID_objeto], [Comentario], [Estatus]
                    FROM [dbo].[sistema_bitacora]
                    WHERE [ID_presentacion] = %s
                      AND [ID_objeto] LIKE %s
                      AND [Id_user] = %s
                    ORDER BY [ID_objeto]
                    """,
                    [id_presentacion, like_pattern, id_user],
                )
            else:
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

    if not id_registro:
        id_registro = timezone.now().strftime("%Y%m%d%H%M%S%f")[-12:]

    fecha_actual = timezone.localtime(timezone.now(), ZoneInfo("America/Mexico_City")).replace(tzinfo=None)

    accion = "guardada"
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT TOP 1 1
            FROM [dbo].[sistema_bitacora]
            WHERE [Id_user] = %s
              AND [ID_presentacion] = %s
              AND [ID_objeto] = %s
            """,
            [id_user, id_presentacion, id_objeto],
        )
        existe = cursor.fetchone() is not None

        if existe:
            cursor.execute(
                """
                UPDATE [dbo].[sistema_bitacora]
                SET [Comentario] = %s,
                    [Estatus] = %s,
                    [fecha] = %s
                WHERE [Id_user] = %s
                  AND [ID_presentacion] = %s
                  AND [ID_objeto] = %s
                """,
                [comentario, estatus, fecha_actual, id_user, id_presentacion, id_objeto],
            )
            accion = "actualizada"
        else:
            cursor.execute(
                """
                INSERT INTO [dbo].[sistema_bitacora]
                ([ID], [Id_user], [ID_presentacion], [ID_objeto], [Comentario], [Estatus], [fecha])
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                [id_registro, id_user, id_presentacion, id_objeto, comentario, estatus, fecha_actual],
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
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def subir_excel(request):
    print(request.META.get("HTTP_AUTHORIZATION"),flush=True)
    archivo = request.FILES.get("file")
    id_tema = request.POST.get("id_tema")
    id_area = request.POST.get("id_area")
    hoja = request.POST.get("hoja")


    if not archivo:
        
        return Response({"error": "No se envió archivo"}, status=400)

    try:
        # print(" Nombre:", archivo.name, flush=True)
        

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
        df.columns = (
            df.columns
            .astype(str)
            .str.strip()
            .str.replace(r"\s+", " ", regex=True)
        )

        df = df.loc[:, ~df.columns.str.contains("^Unnamed", case=False)]
        df = df.loc[:, df.columns != ""]
        df = df.loc[:, df.columns.notna()]        
        #
        columnas_excel = list(df.columns)
        faltantes_estructura  = [c for c in columnas_esperadas if c not in columnas_excel]
        extras = [c for c in columnas_excel if c not in columnas_esperadas]
        
        # usuario = request.auth.get("id_usuario")
        # usuario = request.auth["id_usuario"]
        # print(usuario, flush=True)
        if request.auth:
            usuario = request.auth["id_usuario"]
            print(usuario, flush=True)
        else:
            print("Error", flush=True)
            return Response({"error": "No autenticado"}, status=401)
        fecha_captura = timezone.now()
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
        filas_limpias = []

        for fila in filas:
            # Detectar si TODA la fila está vacía
            if all(
                (v is None) or (str(v).strip() == "") or (pd.isna(v))
                for v in fila.values()
            ):
                print("Fila vacía detectada, se detiene la carga", flush=True)
                break

            filas_limpias.append(fila)

        filas = filas_limpias        
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
                
                if modo_carga == "REPLACE":
                    cursor.execute(f"DELETE FROM {tabla}")
                if not filas:
                    return Response({"error": "El archivo no contiene registros"}, status=400)
                
                # Datos de carga gnericos

                # Agregar columnas extra a cada fila
                filas_con_auditoria = []
                for f in filas:
                    nueva = f.copy()
                    nueva["fecha_captura"] = fecha_captura
                    nueva["pk_idUsuario"] = usuario
                    filas_con_auditoria.append(nueva)

                #Construcción dinámica
                cols = ", ".join([f"[{c}]" for c in filas_con_auditoria[0].keys()])
                vals = ", ".join(["%s"] * len(filas_con_auditoria[0]))

                sql = f"INSERT INTO {tabla} ({cols}) VALUES ({vals})"

                data = [list(f.values()) for f in filas_con_auditoria]

                cursor.executemany(sql, data)   
        #
                sql = """
                INSERT INTO log_carga 
                (id_area, id_tema, pk_idUsuario, nombre_archivo, fecha_carga, registros_total)
                VALUES (%s, %s, %s, %s, %s, %s)
                """
                vals = (id_area, id_tema, usuario, archivo.name, fecha_captura, len(df))
                cursor.execute(sql, vals)

        return Response({
            "columnas": list(df.columns),
            "filas": df.to_dict(orient="records")[:10],
            "total_registros": len(df)
        })

    except Exception as e:
        import traceback
        print(str(e), flush=True)
        traceback.print_exc()

        return Response({"error": str(e)}, status=500)
    

@api_view(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
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
    


@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def bitacoracarga(request):


    query = """
        SELECT 
            b.nombre AS nombre_area,
            c.nombre AS nombre_tema,
            CONCAT(d.fld_nombreUsuario, ' ', d.fld_primer_ap, ' ', d.fld_segundo_ap) AS usuario,
            a.nombre_archivo,
            a.fecha_carga,
            a.registros_total
        FROM log_carga a
        INNER JOIN cat_area b ON a.id_area = b.id_area
        INNER JOIN cat_tema c ON a.id_tema = c.id_tema
        INNER JOIN cat_usuarios d ON a.pk_idUsuario = d.pk_idUsuario
    """

    query += " ORDER BY a.fecha_carga DESC"
    # print("Query: Check", flush=True)
    #  Ejecutar query
    with connection.cursor() as cursor:
        cursor.execute(query)

        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
    # print("Cursor: Check", flush=True)
    #  Convertir a JSON
    data = [
        dict(zip(columns, row))
        for row in rows
    ]
    print("Converted: Check", flush=True)
    return Response(data)


@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def getRegion(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT distinct [Region] as idRegion, [Region] FROM [DB_Catalogos].[dbo].[CUMM_ACTUAL]
        """)
        rows = cursor.fetchall()

    data = [
        {
            "id_region": r[0],
            "nombre": r[1],
            
        }
        for r in rows
    ]

    return Response(data)

@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def getEntidad(request):
    idRegion = request.GET.get("idRegion")
    if not idRegion:
        return Response([], status=200)
        
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT distinct [ClaveEntidadFederativa] as idEntidad, EntidadFederativa as Entidad FROM [DB_Catalogos].[dbo].[CUMM_ACTUAL] WHERE [Region] = %s
        """, [idRegion])
        rows = cursor.fetchall()

    data = [
        {
            "id_entidad": r[0],
            "Entidad": r[1],
            
        }
        for r in rows
    ]

    return Response(data)

@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def getNivelAtencion(request):
    idEntidad = request.GET.get("idEntidad")
    if not idEntidad:
        return Response([], status=200)
        
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT distinct NivelAtencion as id_NivelAtencion, NivelAtencion as Nombre
            FROM [DB_Catalogos].[dbo].[CUMM_ACTUAL] 
            WHERE [ClaveEntidadFederativa] = %s
            AND NivelAtencion in('Segundo Nivel', 'Tercer Nivel')                       
            order by NivelAtencion
        """, [idEntidad])
        rows = cursor.fetchall()

    data = [
        {
            "id_nivel_atencion": r[0],
            "nombre": r[1],
            
        }
        for r in rows
    ]

    return Response(data)

@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def getUnidad(request):
    idEntidad = request.GET.get("idEntidad")
    id_nivel_atencion = request.GET.get("id_nivel_atencion")


    if not idEntidad and not id_nivel_atencion:
        return Response([], status=200)
    


    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT distinct [ClavePresupuestal] as id_Unidad, [DenominacionUnidad] as Nombre
            FROM [DB_Catalogos].[dbo].[CUMM_ACTUAL] 
            WHERE [ClaveEntidadFederativa] = %s and [NivelAtencion] = %s
                and (es_umae is null or es_umae = 'UMAE')
            order by [DenominacionUnidad]
        """, [idEntidad, id_nivel_atencion])
        rows = cursor.fetchall()

    data = [
        {
            "id_unidad_medica": r[0],
            "nombre": r[1],
            
        }
        for r in rows
    ]

    return Response(data)


def convertir_pptx_a_pdf_local(pptx_path: Path, pdf_path: Path):
    """Convierte un PPTX a PDF usando LibreOffice dentro del contenedor."""
    cmd = [
        "libreoffice",
        "--headless",
        "--convert-to",
        "pdf",
        "--outdir",
        str(pdf_path.parent),
        str(pptx_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"LibreOffice falló ({result.returncode}): {result.stderr or result.stdout}"
        )
    if not pdf_path.exists():
        raise RuntimeError("LibreOffice terminó sin generar el PDF")


@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def getGeneraFicha(request):

    idUnidad = request.GET.get("idUnidad")

    if not idUnidad:
        return JsonResponse({
            "ok": False,
            "mensaje": "idUnidad requerido"
        }, status=400)

    import sys, logging
    sys.path.insert(0, '.')
    from ficha.src.core.engine import FichaEngine


    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    engine = FichaEngine()
    # Genera el pptx
    ruta = engine.generar_ficha(idUnidad)

    # Mario: valida que el motor regrese una ruta válida antes de procesar salida.
    if not ruta:
        return JsonResponse({
            "ok": False,
            "mensaje": "No se pudo generar la ficha en formato PPTX"
        }, status=500)

    # Convierte a objeto Path
    pptx_path = Path(ruta)
    # Ruta del PDF en la misma carpeta
    pdf_path = pptx_path.with_suffix(".pdf")

    nombre_archivo = pptx_path.name
    nombre_pdf = pdf_path.name

    # print(f"Archivo PPTX: {ruta}", flush=True)
    # print(f"Archivo PDF: {pdf_path}", flush=True)

    try:
        convertir_pptx_a_pdf_local(pptx_path, pdf_path)
        # print(f"Conversión local exitosa: {pdf_path}", flush=True)
    except Exception as exc:
        # print(f"Error conversión local: {exc}", flush=True)
        # Si se requiere mantener el fallback a Windows + COM, puedes
        # volver a activar este bloque, pero se recomienda usar LibreOffice.
        raise

    return JsonResponse({
        
        "ok": True,
        "url": f"/media/{nombre_pdf}",
        "pptx_url": f"/media/{nombre_archivo}"
    })

