"""Constantes de búsqueda del chatbot."""

PARCHES_TEXTO = {
    "mcgregor": "mc gregor",
    "macgregor": "mc gregor",
    "edomex": "edo mex",
    "bajacalifornia": "baja california",
    "quintanaroo": "quintana roo",
    "sanluis": "san luis",
    "siglo 21": "siglo xxi",
    "centro medico nacional": "cmn",
    "hospital de especialidades": "hes",
    "hospital de cardiologia": "hc",
    "hospital de pediatria": "hp",
    "hospital de oncologia": "honco",
    "hospital de ginecologia": "hgo",
    "hospital de obstetricia": "hgo",
}

PALABRAS_BASURA_HOSPITAL = {
    "cuanto",
    "cuantos",
    "cuanta",
    "cuantas",
    "total",
    "totales",
    "tiene",
    "tienen",
    "hay",
    "numero",
    "cantidad",
    "dame",
    "muestra",
    "consulta",
    "camas",
    "cama",
    "consultorios",
    "consultorio",
    "medicina",
    "interna",
    "urgencias",
    "pediatria",
    "cirugia",
    "ginecologia",
    "obstetricia",
    "terapia",
    "intensiva",
    "adultos",
    "neonatal",
    "del",
    "de",
    "la",
    "el",
    "los",
    "las",
    "en",
    "por",
    "para",
       "cuanto", "cuantos", "cuanta", "cuantas",
    "tiene", "tienen", "hay", "dame", "muestra",
    "numero", "cantidad"
}

PALABRAS_BASURA_VARIABLE = {
    # Tipos, siglas y nombres de hospitales
    "hospital", "hgz", "hgr", "hgzmf", "umf", "umae", "cmn", "siglo", "xxi", 
    "la", "raza", "mc", "gregor", "magdalena", "salinas", "monterrey", "guadalajara",

    # Conectores, preposiciones y artículos
    "del", "de", "la", "el", "los", "las", "en", "por", "para",

    # Verbos de petición y preguntas
    "cuanto", "cuantos", "cuanta", "cuantas", "tiene", "tienen", "hay", 
    "dame", "muestra", "numero", "cantidad",

    # Términos de ámbito territorial
    "delegacion", "delegaciones", "estado", "estados", "entidad", "entidades", 
    "region", "regiones", "nivel", "atencion", "nacional", "pais", "republica", 
    "todo", "todos", "hospitales",

    # Regiones
    "centro", "norte", "occidente", "sureste", "oriente", "poniente", "sur",

    # Niveles de atención
    "primer", "segundo", "tercer",

    # Entidades y delegaciones normalizadas
    "aguascalientes",
    "baja", "california",
    "campeche",
    "chiapas",
    "chihuahua",
    "ciudad", "mexico", "cdmx", "df", # Unifica las variantes de CDMX
    "coahuila",
    "colima",
    "durango",
    "edomex", # Variante de Estado de México
    "guanajuato",
    "guerrero",
    "hidalgo",
    "jalisco",
    "michoacan",
    "morelos",
    "nayarit",
    "nuevo", "leon",
    "oaxaca",
    "puebla",
    "queretaro",
    "quintana", "roo",
    "san", "luis", "potosi",
    "sinaloa",
    "sonora",
    "tabasco",
    "tamaulipas",
    "tlaxcala",
    "veracruz",
    "yucatan",
    "zacatecas"
}

VARIABLES_CANONICAS = {
    "camas_censables": {
        "tokens_genericos": {
            "cama",
            "camas",
            "censable",
            "censables",
        },
        "grupos_requeridos": (
            {"cama", "camas"},
            {"censable", "censables"},
        ),
        "descripcion_objetivo": "total de camas censables de la unidad",
    },
    "quirofanos": {
        "tokens_genericos": {
            "quirofano",
            "quirofanos",
        },
        "grupos_requeridos": (
            {"quirofano", "quirofanos"},
        ),
        "descripcion_objetivo": "sala de quirofano",
    },
    "consultorios": {
        "tokens_genericos": {
            "consultorio",
            "consultorios",
        },
        "grupos_requeridos": (
            {"consultorio", "consultorios"},
        ),
        "descripcion_objetivo": "total de consultorios de la unidad",
    },
}

UMBRAL_HOSPITAL = 0.80
UMBRAL_VARIABLE = 0.45
DELTA_EMPATE = 0.05
