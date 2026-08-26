### Configuracion de la Ficha Presidencial
### Rutas, nombres de archivo, nombres de shape y constantes del proyecto.
### Cuando llegue una actualizacion de insumos, solo se cambian los nombres
### de archivo de la seccion ARCHIVOS.

import os

if os.name == "nt":
    BASE_COORD = r"C:\Users\hp\OneDrive - imssmx\Archivos de Edgar Rosales Ortega - COORD_Datos"
else:
    BASE_COORD = "/root/Library/CloudStorage/OneDrive-imssmx/Archivos de Edgar Rosales Ortega - COORD_Datos"

BASE = os.path.join(BASE_COORD, "Ficha_presidencial")

CARPETA_INPUT = os.path.join(BASE, "input")
CARPETA_ASSETS = os.path.join(CARPETA_INPUT, "assets")
CARPETA_OUTPUT = os.path.join(BASE, "output")

PLANTILLA = os.path.join(CARPETA_ASSETS, "plantilla_ficha_presidencial_19082026.pptx")
CATALOGO_ESTADOS = os.path.join(BASE_COORD, "CATALOGOS", "catalogo_estados.xlsx")

ARCHIVOS = {
    "casa_x_casa": "Casaxcasa_17082026.xlsx",
    "vive_saludable": "vive_saludable_menores_escuelas_19082026.xlsx",
    "jornadas_paz": "jornadas_de_paz_2025_may_jun_2026.xlsx",
    "mexico_te_abraza": "México Te Abraza Actualizado al 140826.xlsx",
    "draft": "draft_2026_contratados_estado_20082026.xlsx",
    "equipo_medico": "equipo_medico_aceleradores_mastografos_tomografos_resonadores_20082026.xlsx",
    "infraestructura": "infra_hospitales_umf_ceci_21082026.xlsx",
}

HOJA_CASA_X_CASA = "Sheet2"
HOJA_VIVE_SALUDABLE = "Sheet1"
HOJA_JORNADAS_PAZ = "Sheet1"
HOJA_DRAFT = "Sheet1"
HOJA_EQUIPO = "Sheet1"
HOJA_HOSPITALES = "Hospitales"
HOJA_UMF = "UMF"
HOJA_CECI = "CECI"

# La hoja de Mexico Te Abraza cambia de nombre en cada actualizacion,
# por eso se lee por indice y no por nombre.
INDICE_HOJA_MTA = 0

# Valor que se escribe cuando el dato existe y es cero o nulo.
GUION = "-"

# Divisor para convertir los importes de equipo medico de pesos a mdp.
DIVISOR_MDP = 1_000_000

# Umbral a partir del cual el listado se reparte en dos columnas.
MIN_ELEMENTOS_DOS_COLUMNAS = 3

# Formato de cada renglon del listado de hospitales y UMF.
FORMATO_RENGLON_LISTA = "{n}. {nombre}"

# Detalle que se agrega al nombre del proyecto. El monto se omite cuando es
# cero y el ano cuando la columna Apertura viene vacia o sin ano legible.
FORMATO_MONTO_PROYECTO = "${monto} mdp"
FORMATO_ANIO_PROYECTO = "{anio}"
FORMATO_DETALLE_PROYECTO = " ({detalle})"
SEPARADOR_DETALLE = ", "

# Siglo que se antepone cuando la apertura trae el ano en dos digitos, por
# ejemplo Sep-26.
SIGLO_APERTURA = 2000

# Orden en que se agrupan los proyectos dentro del listado. Dentro de cada
# grupo el orden es alfabetico.
ORDEN_ESTATUS = ["nuevos", "proceso", "planeacion"]

# Encabezado de cada grupo dentro del listado.
ETIQUETAS_ESTATUS = {
    "hospitales": {
        "nuevos": "nuevos",
        "proceso": "en proceso",
        "planeacion": "planeación",
    },
    "umf": {
        "nuevos": "nuevas",
        "proceso": "en proceso",
        "planeacion": "planeación",
    },
}

COLOR_ENCABEZADO_ESTATUS = "006455"

# Sangria en centimetros que llevan los renglones de proyecto respecto al
# encabezado de su grupo.
SANGRIA_PROYECTO = 0.35

# Diferencia maxima de renglones entre las dos columnas que se acepta al
# repartir sin partir grupos. Si se rebasa, el grupo mas largo se parte y su
# encabezado se repite en la segunda columna.
MAX_DESBALANCE_COLUMNAS = 2

# Sufijo que se agrega al nombre de los proyectos ya terminados, es decir los
# que tienen estatus nuevos o nuevas.
SUFIJO_CONCLUIDO = {
    "hospitales": "-Concluido-",
    "umf": "-Concluida-",
}
COLOR_SUFIJO_CONCLUIDO = "006455"

# Umbral a partir de la cual la cifra se abrevia a millones.
UMBRAL_MILLONES = 1_000_000
FORMATO_MILLONES = "{:.1f}|M"

# Separador interno entre la cifra y su sufijo. No aparece en la ficha.
SEPARADOR_SUFIJO = "|"

# Proporcion del tamano de fuente que se aplica al sufijo de millones.
PROPORCION_SUFIJO = 0.6

# Entidades cuyo encabezado no usa el nombre oficial del catalogo.
ENTIDAD_ENCABEZADO = {
    "09": "CDMX",
}

# Porcion de 2025 incluida en las cifras de Jornadas de Paz.
# Solo estas entidades llevan nota al pie.
JORNADAS_PAZ_2025 = {
    "11": (100, 166819),
    "06": (20, 2775),
    "16": (12, 5441),
    "27": (41, 57503),
}

NOTA_JP_TEXTO = "Incluye {jornadas} jornadas y {atenciones} atenciones realizadas en 2025"
NOTA_JP_LEFT = 14.92
NOTA_JP_TOP = 26.33
NOTA_JP_ANCHO = 5.44
NOTA_JP_ALTO = 0.85
NOTA_JP_FUENTE = "Noto Sans"
NOTA_JP_TAMANO = 7

# Nombres de shape de la plantilla.
SHAPE_ENTIDAD = "TXT_ENTIDAD"

SHAPES_INVERSION = {
    "infraestructura": "TXT_INV_INFRA",
    "equipo": "TXT_INV_EQUIPO",
    "ceci": "TXT_INV_CECI",
    "total": "TXT_INV_TOTAL",
}

SHAPES_HOSPITALES = {
    "total": "TXT_HOSP_NUM",
    "monto": "TXT_HOSP_MDP",
    "nuevos": "TXT_HOSP_NUEVOS",
    "proceso": "TXT_HOSP_PROCESO",
    "planeacion": "TXT_HOSP_PLANEACION",
    "lista_1": "TXT_HOSP_LISTA_1",
    "lista_2": "TXT_HOSP_LISTA_2",
}

SHAPES_UMF = {
    "total": "TXT_UMF_NUM",
    "monto": "TXT_UMF_MDP",
    "nuevas": "TXT_UMF_NUEVAS",
    "proceso": "TXT_UMF_PROCESO",
    "planeacion": "TXT_UMF_PLANEACION",
    "lista_1": "TXT_UMF_LISTA_1",
    "lista_2": "TXT_UMF_LISTA_2",
}

SHAPE_TABLA_EQUIPO = "TABLA_EQUIPO"
SHAPE_EQ_MDP = "TXT_EQ_MDP"
SHAPE_DRAFT = "TXT_DRAFT_ESPECIALISTAS"

# Orden de las filas de TABLA_EQUIPO. La cifra va en la columna 0.
ORDEN_TABLA_EQUIPO = ["aceleradores", "mastografos", "tomografos", "resonadores"]
COLUMNA_CIFRA_TABLA_EQUIPO = 0

SHAPES_CECI = {
    "monto": "TXT_CECI_MDP",
    "meta": "TXT_CECI_META",
    "proceso": "TXT_CECI_PROCESO",
    "planeacion": "TXT_CECI_PLANEACION",
    "concluido": "TXT_CECI_CONCLUIDO",
}

# Grupos de las casillas de CECI, en el orden en que se muestran de izquierda
# a derecha. El grupo de concluido se elimina cuando la entidad no tiene y los
# grupos restantes se reacomodan dentro del area.
GRUPOS_CECI = {
    "meta": "GRP_CECI_META",
    "proceso": "GRP_CECI_PROCESO",
    "planeacion": "GRP_CECI_PLANEACION",
    "concluido": "GRP_CECI_CONCLUIDO",
}

# Area en centimetros donde se reparten las casillas de CECI. Corresponde al
# recuadro blanco que va detras de los textbox.
AREA_CECI = {
    "left": 11.18,
    "top": 19.01,
    "ancho": 9.55,
    "alto": 2.05,
}

SHAPES_VIVE_SALUDABLE = {
    "escuelas": "TXT_VS_ESCUELAS",
    "tamizajes": "TXT_VS_TAMIZAJES",
    "brigadas": "TXT_VS_BRIGADAS",
    "consultas": "TXT_VS_CONSULTAS",
}

SHAPES_CASA_X_CASA = {
    "diabetes": "TXT_CXC_DIABETES",
    "hipertension": "TXT_CXC_HIPERTENSION",
}

SHAPE_GRUPO_MTA = "GRP_MTA"
SHAPES_MTA = {
    "afiliaciones": "TXT_MTA_AFILIACIONES",
    "medicas": "TXT_MTA_MEDICAS",
    "preventivas": "TXT_MTA_PREVENTIVAS",
    "psicologicas": "TXT_MTA_PSICOLOGICAS",
}

SHAPE_GRUPO_JP = "GRP_JP"
SHAPES_JP = {
    "jornadas": "TXT_JP_JORNADAS",
    "atenciones": "TXT_JP_ATENCIONES",
}

# Plantillas por excepcion. La entidad que aparece aqui usa su propia
# plantilla en lugar de la general.
PLANTILLAS_POR_ENTIDAD = {
    "16": "plantilla_ficha_presidencial_michoacan_20082026.pptx",
}

# Monto de conservacion en mdp que se suma a infraestructura. La cifra ya viene
# escrita en la plantilla de la entidad, aqui solo se suma para que el total
# cuadre.
CONSERVACION_MDP = {
    "16": 1334,
}

PREFIJO_SALIDA = "FICHA_PRESIDENCIAL"
SUFIJO_SALIDA = "v2"


def ruta_insumo(clave):
    """Devuelve la ruta completa de un archivo de insumo.
    Parametros:
    clave: llave del diccionario ARCHIVOS"""
    return os.path.join(CARPETA_INPUT, ARCHIVOS[clave])