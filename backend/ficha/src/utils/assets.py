"""
Gestor de fotos para fichas hospitalarias.
Estructura esperada en OneDrive:
  fotos_fachada/
    _010101012151_HGZ 1 Aguascalientes/
        FACHADA - quien sea.jpeg     (cualquier nombre, tomamos la primera)
    _291301012151_HGZ 3 Mante/
        fachada.jpeg
  fotos_origen/
    _200817012151_HGZ 67 Apodaca/
        foto_1_200817012151.jpeg
        foto_2_200817012151.jpeg
        foto_3_200817012151.jpeg
        foto_4_200817012151.jpeg
Reglas:
- Las subcarpetas pueden empezar con '_' o no, y siempre contienen la clave.
- Para fachada: la primera imagen alfabéticamente de la subcarpeta.
- Para interiores: archivos cuyo nombre contiene 'foto_1' .. 'foto_4'.
- Convertimos todo a JPG y cacheamos en /assets/cache_fotos para no reprocesar.
"""

import logging
from collections import defaultdict
from pathlib import Path
from typing import Optional, Dict, List
from PIL import Image
try:
    import pillow_heif
    pillow_heif.register_heif_opener()  # iPhone HEIC
except ImportError:
    logging.getLogger(__name__).warning(
        "pillow-heif no instalado: archivos .heic/.heif no se procesarán"
    )

from ficha.src.core.config import AppConfig

logger = logging.getLogger(__name__)

EXTENSIONES_VALIDAS = {'.jpg', '.jpeg', '.png', '.heic', '.heif',
                       '.webp', '.bmp', '.tiff', '.tif'}


class AssetManager:
    """Encuentra fotos en OneDrive, las normaliza a JPG y devuelve sus rutas."""
    def __init__(self, config: AppConfig):
        self.config = config
        self.ruta_fotos    = config.ruta_fotos_origen
        self.ruta_fachadas = config.ruta_fotos_fachada
        self.cache_dir     = config.project_root / "assets" / "cache_fotos"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self._directory_cache = {
            str(self.ruta_fotos.resolve()): self._collect_directories(self.ruta_fotos),
            str(self.ruta_fachadas.resolve()): self._collect_directories(self.ruta_fachadas),
        }
        self._directory_index = {
            str(self.ruta_fotos.resolve()): self._build_directory_index(self.ruta_fotos),
            str(self.ruta_fachadas.resolve()): self._build_directory_index(self.ruta_fachadas),
        }
        self._found_subcarpeta: Dict[str, Optional[Path]] = {}
        self._images_cache: Dict[str, List[Path]] = {}

    def preparar_fotos_unidad(self, clave: str) -> Dict[str, Optional[Path]]:
        """
        Devuelve un dict con las 5 rutas de fotos. Las claves no cambian:
          fachada, interior_1, interior_2, interior_3, interior_4
        Si una foto no existe, su valor es None.
        """

        carpeta_fachada  = self._encontrar_subcarpeta(self.ruta_fachadas, clave)

        carpeta_interior = self._encontrar_subcarpeta(self.ruta_fotos, clave)

        return {
            
            "fachada":    self._obtener_fachada(carpeta_fachada, clave),
            "interior_1": self._obtener_interior(carpeta_interior, clave, 1),
            "interior_2": self._obtener_interior(carpeta_interior, clave, 2),
            "interior_3": self._obtener_interior(carpeta_interior, clave, 3),
            "interior_4": self._obtener_interior(carpeta_interior, clave, 4),
        }

    # búsqueda
    def _collect_directories(self, raiz: Path) -> List[Path]:
        if not raiz or not raiz.exists():
            return []
        return [d for d in raiz.iterdir() if d.is_dir()]

    def _build_directory_index(self, raiz: Path) -> Dict[str, List[Path]]:
        index: Dict[str, List[Path]] = defaultdict(list)
        for carpeta in self._collect_directories(raiz):
            nombre = carpeta.name.lower()
            index[nombre].append(carpeta)

            clave_principal = nombre.lstrip('_').split()[0]
            if clave_principal:
                index[clave_principal].append(carpeta)
        return index

    def _encontrar_subcarpeta(self, raiz: Path, clave: str) -> Optional[Path]:
        """Busca dentro de `raiz` la subcarpeta cuyo nombre contiene la clave."""
        if not raiz or not raiz.exists():
            return None

        clave_lower = clave.lower()
        cache_key = f"{str(raiz.resolve())}|{clave_lower}"
        if cache_key in self._found_subcarpeta:
            return self._found_subcarpeta[cache_key]

        root_key = str(raiz.resolve())
        candidatas = self._directory_index.get(root_key, {}).get(clave_lower, [])
        if not candidatas:
            candidatas = [
                d for d in self._directory_cache.get(root_key, [])
                if clave_lower in d.name.lower()
            ]

        if candidatas:
            resultado = sorted(candidatas, key=lambda p: p.name)[0]
        else:
            resultado = None

        self._found_subcarpeta[cache_key] = resultado
        return resultado

    def _listar_imagenes(self, carpeta: Path) -> List[Path]:
        """Devuelve archivos de imagen ordenados por nombre."""
        if not carpeta or not carpeta.exists():
            return []

        cache_key = str(carpeta.resolve())
        if cache_key in self._images_cache:
            return self._images_cache[cache_key]

        imagenes = sorted(
            [f for f in carpeta.iterdir()
             if f.is_file() and f.suffix.lower() in EXTENSIONES_VALIDAS],
            key=lambda p: p.name.lower()
        )
        self._images_cache[cache_key] = imagenes
        return imagenes

    def _obtener_fachada(self, carpeta: Optional[Path], clave: str) -> Optional[Path]:
        """Toma la PRIMERA imagen de la carpeta de fachada de la unidad."""
        cache = self.cache_dir / f"foto_fachada_{clave}.jpg"
        if cache.exists():
            return cache

        imagenes = self._listar_imagenes(carpeta)
        if not imagenes:
            return None
        return self._convertir_a_jpg(imagenes[0], cache)

    def _obtener_interior(
        self, carpeta: Optional[Path], clave: str, numero: int
    ) -> Optional[Path]:
        """
        Busca una imagen cuyo nombre contenga 'foto_{numero}' (con delimitador).
        Aceptamos: foto_1, foto-1, foto 1 — el separador entre 'foto' y el num.
        """
        cache = self.cache_dir / f"foto_{numero}_{clave}.jpg"
        if cache.exists():
            return cache

        imagenes = self._listar_imagenes(carpeta)
        if not imagenes:
            return None

        # Patrones aceptados
        patrones = [f"foto_{numero}", f"foto-{numero}", f"foto {numero}"]
        for img in imagenes:
            stem = img.stem.lower()
            for p in patrones:
                if p in stem:
                    # Sanity check: que el caracter después del número no sea
                    # otro dígito (foto_1 vs foto_10).
                    idx = stem.find(p) + len(p)
                    if idx >= len(stem) or not stem[idx].isdigit():
                        return self._convertir_a_jpg(img, cache)
        return None

    # conversión

    def _convertir_a_jpg(self, origen: Path, destino: Path) -> Optional[Path]:
        """Convierte cualquier formato soportado a JPEG y cachea."""
        try:
            with Image.open(origen) as img:
                if img.mode in ("RGBA", "P", "LA"):
                    img = img.convert("RGB")
                # Limita resolución máxima (6 MP) para PPTs más livianos
                img.thumbnail((3000, 3000), Image.LANCZOS)
                img.save(destino, "JPEG", quality=85, optimize=True)
            return destino
        except Exception as e:
            logger.warning(f"No se pudo procesar {origen.name}: {e}")
            return None