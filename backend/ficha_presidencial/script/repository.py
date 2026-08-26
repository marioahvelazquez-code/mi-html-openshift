### Capa de acceso a datos de la Ficha Presidencial
### Lee los Excel de insumo y entrega un objeto FuenteDatos con la informacion
### cruda indexada por clave de entidad. No aplica reglas de negocio ni formato.

import os
import re
import unicodedata
import datetime
import openpyxl

import config
from data_models import FuenteDatos, Proyecto

# Caracteres invisibles que traen los archivos por copiado desde PowerPoint.
INVISIBLES = ("\u200b", "\ufeff", "\xa0", "\u2060")


def limpiar(valor):
    """Quita caracteres invisibles y espacios sobrantes de un texto.
    Parametros:
    valor: contenido de celda o encabezado"""
    if valor is None:
        return ""
    texto = str(valor)
    for caracter in INVISIBLES:
        texto = texto.replace(caracter, "")
    return texto.strip()


def normalizar(valor):
    """Normaliza un texto para comparaciones: sin acentos, en mayusculas.
    Parametros:
    valor: contenido de celda o encabezado"""
    texto = limpiar(valor).upper()
    descompuesto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in descompuesto if not unicodedata.combining(c))


def clave_entidad(valor):
    """Convierte una clave de entidad a texto de dos digitos.
    Parametros:
    valor: clave leida del archivo, puede venir como entero o texto"""
    texto = limpiar(valor)
    if not texto:
        return ""
    return texto.zfill(2)


def numero(valor):
    """Convierte un valor de celda a numero. Devuelve None si esta vacio.
    Parametros:
    valor: contenido de celda"""
    if valor is None:
        return None
    if isinstance(valor, (int, float)):
        return valor
    texto = limpiar(valor).replace(",", "").replace("%", "")
    if not texto or texto == config.GUION:
        return None
    try:
        return float(texto)
    except ValueError:
        return None


def leer_hoja(ruta, hoja=None, indice=None):
    """Lee una hoja de Excel y devuelve una lista de diccionarios cuyas llaves
    son los encabezados normalizados.
    Parametros:
    ruta: ruta completa del archivo
    hoja: nombre de la hoja, opcional
    indice: indice de la hoja, se usa cuando el nombre cambia entre versiones"""
    if not os.path.exists(ruta):
        raise FileNotFoundError(f"No se encontro el archivo: {ruta}")

    libro = openpyxl.load_workbook(ruta, data_only=True)
    if indice is not None:
        ws = libro.worksheets[indice]
    else:
        ws = libro[hoja]

    filas = list(ws.iter_rows(values_only=True))
    libro.close()

    if not filas:
        return []

    encabezados = [normalizar(c) for c in filas[0]]
    registros = []
    for fila in filas[1:]:
        registro = {}
        for encabezado, valor in zip(encabezados, fila):
            if encabezado:
                registro[encabezado] = valor
        registros.append(registro)
    return registros


def anio_apertura(valor):
    """Extrae el ano de la columna Apertura. Devuelve None cuando la celda esta
    vacia o no contiene un ano legible, como en el caso de Inaugurado.
    Acepta fecha de Excel, ano de cuatro digitos y formatos tipo Sep-26.
    Parametros:
    valor: contenido de la celda Apertura"""
    if valor is None:
        return None

    if isinstance(valor, (datetime.datetime, datetime.date)):
        return valor.year

    if isinstance(valor, (int, float)):
        entero = int(valor)
        return entero if 1900 <= entero <= 2100 else None

    texto = limpiar(valor)
    if not texto:
        return None

    completo = re.search(r"(19|20)\d{2}", texto)
    if completo:
        return int(completo.group(0))

    corto = re.search(r"[-/\s](\d{2})$", texto)
    if corto:
        return config.SIGLO_APERTURA + int(corto.group(1))

    return None


def normalizar_estatus(valor):
    """Convierte el estatus del archivo a las tres categorias de la ficha.
    Parametros:
    valor: contenido de la columna Estatus"""
    texto = normalizar(valor)
    if texto in ("NUEVOS", "NUEVAS"):
        return "nuevos"
    if texto == "EN PROCESO":
        return "proceso"
    if texto == "PLANEACION":
        return "planeacion"
    return ""


def cargar_catalogo(ruta):
    """Lee el catalogo de estados y devuelve el nombre oficial por clave y el
    indice de alias normalizados hacia la clave.
    Parametros:
    ruta: ruta del archivo de catalogo"""
    registros = leer_hoja(ruta, hoja="catalogo_estados")
    catalogo = {}
    alias = {}
    for r in registros:
        cve = clave_entidad(r.get("CVE_ENT"))
        oficial = limpiar(r.get("ENTIDAD_OFICIAL"))
        if not cve or not oficial:
            continue
        catalogo[cve] = oficial
        alias[normalizar(oficial)] = cve
        valor_alias = normalizar(r.get("ALIAS"))
        if valor_alias:
            alias[valor_alias] = cve
    return catalogo, alias


def cve_desde_nombre(valor, alias):
    """Resuelve la clave de entidad a partir de un nombre de estado.
    Parametros:
    valor: nombre del estado tal como viene en el archivo
    alias: indice de alias normalizados"""
    return alias.get(normalizar(valor), "")


def cargar_proyectos(ruta, hoja):
    """Lee una hoja de proyectos de infraestructura, hospitales o UMF.
    Parametros:
    ruta: ruta del archivo
    hoja: nombre de la hoja"""
    registros = leer_hoja(ruta, hoja=hoja)
    resultado = {}
    for r in registros:
        cve = clave_entidad(r.get("CVE_ENT"))
        nombre = limpiar(r.get("PROYECTO"))
        if not cve or not nombre:
            continue
        proyecto = Proyecto(
            nombre=nombre,
            estatus=normalizar_estatus(r.get("ESTATUS")),
            inversion=numero(r.get("INVERSION")) or 0.0,
            anio_apertura=anio_apertura(r.get("APERTURA")),
        )
        resultado.setdefault(cve, []).append(proyecto)
    return resultado


def cargar_ceci(ruta, hoja):
    """Lee la hoja de CECI.
    Parametros:
    ruta: ruta del archivo
    hoja: nombre de la hoja"""
    registros = leer_hoja(ruta, hoja=hoja)
    resultado = {}
    for r in registros:
        cve = clave_entidad(r.get("CVE_ENT"))
        if not cve:
            continue
        resultado[cve] = {
            "meta": numero(r.get("CANTIDAD_META")),
            "proceso": numero(r.get("CANTIDAD_PROCESO")),
            "planeacion": numero(r.get("CANTIDAD_PLANEACION")),
            "concluido": numero(r.get("CANTIDAD_CONCLUIDO")),
            "inversion": numero(r.get("INVERSION_TOTAL")),
        }
    return resultado


def cargar_equipo(ruta, hoja, alias):
    """Lee la hoja de equipo medico. Los importes vienen en pesos y se
    convierten a mdp. El cruce es por nombre de entidad.
    Parametros:
    ruta: ruta del archivo
    hoja: nombre de la hoja
    alias: indice de alias normalizados"""
    registros = leer_hoja(ruta, hoja=hoja)
    campos = {
        "aceleradores": "ACELERADORES_LINEALES",
        "mastografos": "MASTOGRAFOS",
        "tomografos": "TOMOGRAFOS",
        "resonadores": "RESONADORES",
    }
    resultado = {}
    for r in registros:
        cve = cve_desde_nombre(r.get("ENTIDAD"), alias)
        if not cve:
            continue
        datos = {}
        importe_total = 0.0
        for llave, prefijo in campos.items():
            datos[llave] = numero(r.get(f"{prefijo}_CANTIDAD"))
            importe = numero(r.get(f"{prefijo}_IMPORTE"))
            if importe:
                importe_total += importe
        datos["inversion"] = importe_total / config.DIVISOR_MDP
        resultado[cve] = datos
    return resultado


def cargar_draft(ruta, hoja):
    """Lee el conteo de especialistas contratados del Draft 2026.
    Parametros:
    ruta: ruta del archivo
    hoja: nombre de la hoja"""
    registros = leer_hoja(ruta, hoja=hoja)
    resultado = {}
    for r in registros:
        cve = clave_entidad(r.get("CVE_ENT"))
        valor = numero(r.get("ESPECIALISTAS"))
        if cve and valor is not None:
            resultado[cve] = int(valor)
    return resultado


def cargar_vive_saludable(ruta, hoja):
    """Lee la hoja de Vive Saludable. Descarta la fila de total, que no trae
    clave de entidad.
    Parametros:
    ruta: ruta del archivo
    hoja: nombre de la hoja"""
    registros = leer_hoja(ruta, hoja=hoja)
    resultado = {}
    for r in registros:
        cve = clave_entidad(r.get("CVE_ENTIDAD"))
        if not cve:
            continue
        resultado[cve] = {
            "escuelas": numero(r.get("ESCUELAS TAMIZADAS")),
            "tamizajes": numero(r.get("NINAS Y NINOS TAMIZADOS")),
            "brigadas": numero(r.get("BRIGADAS")),
            "consultas": numero(r.get("CONSULTAS UMF")),
        }
    return resultado


def cargar_casa_x_casa(ruta, hoja):
    """Lee la hoja de Casa por Casa. Cada indicador es la suma de sospechosos
    mas descontrolados. Descarta la fila de total.
    Parametros:
    ruta: ruta del archivo
    hoja: nombre de la hoja"""
    registros = leer_hoja(ruta, hoja=hoja)
    resultado = {}
    for r in registros:
        cve = clave_entidad(r.get("CVE_ENTIDAD"))
        if not cve:
            continue
        hipertension = (numero(r.get("SOSPECHOSOS_HIPERTENCION")) or 0) + \
                       (numero(r.get("DESCONTROLADOS_HIPERTENCION")) or 0)
        diabetes = (numero(r.get("SOSPECHOSOS_DIABETES")) or 0) + \
                   (numero(r.get("DESCONTROLADOS_DIABETES")) or 0)
        resultado[cve] = {"hipertension": hipertension, "diabetes": diabetes}
    return resultado


def cargar_jornadas_paz(ruta, hoja, alias):
    """Lee la hoja de Jornadas de Paz. Solo aparecen las entidades con jornadas.
    Parametros:
    ruta: ruta del archivo
    hoja: nombre de la hoja
    alias: indice de alias normalizados"""
    registros = leer_hoja(ruta, hoja=hoja)
    resultado = {}
    for r in registros:
        cve = cve_desde_nombre(r.get("ESTADO"), alias)
        if not cve:
            continue
        jornadas = numero(r.get("NO. JORNADAS")) or 0
        atenciones = numero(r.get("NO. ATENCIONES")) or 0
        if cve in resultado:
            resultado[cve]["jornadas"] += jornadas
            resultado[cve]["atenciones"] += atenciones
        else:
            resultado[cve] = {"jornadas": jornadas, "atenciones": atenciones}
    return resultado


def cargar_mexico_te_abraza(ruta, indice, alias):
    """Lee la hoja de Mexico Te Abraza. Viene desagregada por plaza, por lo que
    se agregan las filas de una misma entidad. Descarta la fila de total y la
    nota final, que no traen entidad.
    Parametros:
    ruta: ruta del archivo
    indice: indice de la hoja
    alias: indice de alias normalizados"""
    registros = leer_hoja(ruta, indice=indice)
    campos = {
        "medicas": "ATENCIONES MEDICAS",
        "preventivas": "MEDICINA PREVENTIVA",
        "psicologicas": "PSICOLOGIA",
        "afiliaciones": "AFILIACION Y VIGENCIA DE DERECHOS",
    }
    resultado = {}
    for r in registros:
        cve = cve_desde_nombre(r.get("ENTIDAD"), alias)
        if not cve:
            continue
        acumulado = resultado.setdefault(cve, {k: 0 for k in campos})
        for llave, encabezado in campos.items():
            acumulado[llave] += numero(r.get(encabezado)) or 0
    return resultado


def cargar_todo():
    """Lee todas las fuentes y devuelve un objeto FuenteDatos."""
    catalogo, alias = cargar_catalogo(config.CATALOGO_ESTADOS)
    infra = config.ruta_insumo("infraestructura")

    return FuenteDatos(
        catalogo=catalogo,
        alias=alias,
        hospitales=cargar_proyectos(infra, config.HOJA_HOSPITALES),
        umf=cargar_proyectos(infra, config.HOJA_UMF),
        ceci=cargar_ceci(infra, config.HOJA_CECI),
        equipo=cargar_equipo(config.ruta_insumo("equipo_medico"),
                             config.HOJA_EQUIPO, alias),
        draft=cargar_draft(config.ruta_insumo("draft"), config.HOJA_DRAFT),
        vive_saludable=cargar_vive_saludable(config.ruta_insumo("vive_saludable"),
                                             config.HOJA_VIVE_SALUDABLE),
        casa_x_casa=cargar_casa_x_casa(config.ruta_insumo("casa_x_casa"),
                                       config.HOJA_CASA_X_CASA),
        jornadas_paz=cargar_jornadas_paz(config.ruta_insumo("jornadas_paz"),
                                         config.HOJA_JORNADAS_PAZ, alias),
        mexico_te_abraza=cargar_mexico_te_abraza(config.ruta_insumo("mexico_te_abraza"),
                                                 config.INDICE_HOJA_MTA, alias),
    )