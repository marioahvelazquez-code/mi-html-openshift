### Orquestador de la Ficha Presidencial
### Coordina repository, processor y renderer. Los insumos se leen una sola vez
### y se reutilizan para las 32 fichas.

import os
import unicodedata
from datetime import datetime

import config
import repository
import processor
import renderer


def nombre_archivo(entidad):
    """Construye el nombre del pptx de salida a partir del nombre de entidad.
    Parametros:
    entidad: nombre de la entidad tal como aparece en el encabezado"""
    descompuesto = unicodedata.normalize("NFKD", entidad.upper())
    limpio = "".join(c for c in descompuesto if not unicodedata.combining(c))
    limpio = limpio.replace(" ", "_")
    fecha = datetime.now().strftime("%d_%m_%Y")
    return f"{config.PREFIJO_SALIDA}_{limpio}_{fecha}_{config.SUFIJO_SALIDA}.pptx"


class GeneradorFichas:
    """Fachada del proceso de generacion. Carga los insumos al construirse y
    expone la generacion individual y en lote."""

    def __init__(self):
        self.fuente = repository.cargar_todo()

    def claves_disponibles(self):
        """Devuelve las claves de entidad del catalogo, ordenadas."""
        return sorted(self.fuente.catalogo.keys())

    def plantilla_de(self, cve_ent):
        """Devuelve la plantilla que corresponde a una entidad. Las entidades
        listadas en PLANTILLAS_POR_ENTIDAD usan su propia plantilla.
        Parametros:
        cve_ent: clave de entidad de dos digitos"""
        nombre = config.PLANTILLAS_POR_ENTIDAD.get(cve_ent)
        if nombre is None:
            return config.PLANTILLA
        return os.path.join(config.CARPETA_ASSETS, nombre)

    def generar(self, cve_ent, output_dir=None):
        """Genera la ficha de una entidad y devuelve la ruta del archivo.
        Parametros:
        cve_ent: clave de entidad de dos digitos"""
        cve_ent = str(cve_ent).zfill(2)
        if cve_ent not in self.fuente.catalogo:
            raise ValueError(f"Clave de entidad no encontrada en el catalogo: {cve_ent}")

        ficha = processor.construir_ficha(cve_ent, self.fuente)
        plantilla = self.plantilla_de(cve_ent)

        if not os.path.exists(plantilla):
            raise FileNotFoundError(f"No se encontro la plantilla: {plantilla}")

        carpeta_salida = output_dir or config.CARPETA_OUTPUT
        os.makedirs(carpeta_salida, exist_ok=True)
        ruta_salida = os.path.join(carpeta_salida, nombre_archivo(ficha.entidad))

        return renderer.renderizar(ficha, plantilla, ruta_salida,
                                   processor.repartir_listado)

    def generar_lote(self, output_dir=None):
        """Genera las fichas de todas las entidades del catalogo y devuelve la
        lista de rutas generadas."""
        rutas = []
        for cve_ent in self.claves_disponibles():
            entidad = self.fuente.catalogo[cve_ent]
            print(f"[{cve_ent}] {entidad}")
            rutas.append(self.generar(cve_ent, output_dir=output_dir))
        return rutas