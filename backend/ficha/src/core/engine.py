"""
Motor principal de generación de fichas hospitalarias.
Expone:
- generar_ficha(clave) → ruta del PPT generado (o lanza excepción).
- generar_batch(claves, n_workers=1) → resumen {ok, errores, tiempo}.
  - Modo masivo robusto: cada clave se procesa en aislamiento; si una truena,
    se registra el error y se continúa con la siguiente.
  - Si n_workers > 1, paralelizamos con ThreadPoolExecutor. Cada worker
    abre su propia conexión SQL (importante porque pyodbc.Connection no es
    thread-safe para uso simultáneo).
"""

import logging
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from ficha.src.core.config import AppConfig
from ficha.src.data.repository import DataRepository
from ficha.src.core.processor import DataProcessor
from ficha.src.utils.assets import AssetManager
from ficha.src.utils.renderer import PPTRenderer

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class ResumenBatch:
    ok: List[Tuple[str, str]] = field(default_factory=list)        # (clave, ruta)
    errores: List[Tuple[str, str]] = field(default_factory=list)   # (clave, mensaje)
    tiempo_total: float = 0.0

    @property
    def total(self) -> int:
        return len(self.ok) + len(self.errores)

    @property
    def tasa_exito(self) -> float:
        return (len(self.ok) / self.total) if self.total else 0.0

    def imprimir(self):
        print(f"\n{'='*60}")
        print(f"  Total procesadas: {self.total}")
        print(f"  ✓ Exitosas:       {len(self.ok)}")
        print(f"  ✗ Errores:        {len(self.errores)}")
        print(f"  Tasa éxito:       {self.tasa_exito:.1%}")
        print(f"  Tiempo total:     {self.tiempo_total:.1f}s "
              f"({self.tiempo_total / max(self.total, 1):.1f}s/ficha)")
        if self.errores:
            print(f"\n  Detalle de errores:")
            for cve, msg in self.errores:
                print(f"    • {cve}: {msg}")
        print('='*60)


class FichaEngine:
    """Orquestador del flujo end-to-end."""
    def __init__(self, config: Optional[AppConfig] = None):
        logger.info("Inicializando Motor de Fichas...")
        self.config = config or AppConfig()
        # En modo masivo, cada thread crea su propio Repository para evitar
        # compartir conexiones pyodbc. Los demás componentes son stateless.
        self._thread_local = threading.local()
        self.assets_manager = AssetManager(self.config)
        self.renderer = PPTRenderer(self.config)

    @property
    def repo(self) -> DataRepository:
        """Devuelve un DataRepository propio del thread actual."""
        if not hasattr(self._thread_local, 'repo'):
            self._thread_local.repo = DataRepository(self.config)
        return self._thread_local.repo

    def generar_ficha(self, clave: str) -> str:
        """Genera UNA ficha. Lanza excepción si algo falla."""
        # 1. Datos SQL
        logger.info(f"[{clave}] 1/5 SQL...")
        ficha = self.repo.obtener_datos_ficha(clave)

        # 2. Población (Excel)
        logger.info(f"[{clave}] 2/5 Excel regionalización...")
        ficha.poblacion_regionalizacion = self.repo.obtener_dato_excel(clave)

        # 3. KPIs
        logger.info(f"[{clave}] 3/5 Procesando KPIs...")
        ficha = DataProcessor.procesar_ficha(ficha)

        # 4. Fotos
        logger.info(f"[{clave}] 4/5 Fotos...")
        fotos = self.assets_manager.preparar_fotos_unidad(clave)
        
        # 5. PPTX
        logger.info(f"[{clave}] 5/5 PPTX...")
        ruta = self.renderer.generar_ppt(ficha, fotos)
        logger.info(f"[{clave}] ✓ {ruta.name}")
        return str(ruta)

    def generar_batch(self,
                      claves: List[str],
                      n_workers: int = 1,
                      verbose_cada: int = 10) -> ResumenBatch:
        """
        Genera fichas en lote con manejo de errores por clave.
        - n_workers: 1 = secuencial; >1 = paralelo con ThreadPool.
        - verbose_cada: imprime progreso cada N fichas.
        """
        resumen = ResumenBatch()
        t0 = time.time()
        total = len(claves)
        logger.info(f"Iniciando batch de {total} fichas con {n_workers} worker(s)...")

        if n_workers <= 1:
            for i, clave in enumerate(claves, 1):
                self._procesar_una_clave(clave, resumen)
                if i % verbose_cada == 0 or i == total:
                    logger.info(f"  Progreso: {i}/{total}")
        else:
            with ThreadPoolExecutor(max_workers=n_workers) as pool:
                futuros = {pool.submit(self._generar_clave_safe, c): c for c in claves}
                for i, fut in enumerate(as_completed(futuros), 1):
                    clave = futuros[fut]
                    ok, ruta_o_msg = fut.result()
                    if ok:
                        resumen.ok.append((clave, ruta_o_msg))
                    else:
                        resumen.errores.append((clave, ruta_o_msg))
                    if i % verbose_cada == 0 or i == total:
                        logger.info(f"  Progreso: {i}/{total}")

        resumen.tiempo_total = time.time() - t0
        return resumen

    # helpers internos
    def _procesar_una_clave(self, clave: str, resumen: ResumenBatch):
        """Versión secuencial: muta el resumen directamente."""
        ok, ruta_o_msg = self._generar_clave_safe(clave)
        if ok:
            resumen.ok.append((clave, ruta_o_msg))
        else:
            resumen.errores.append((clave, ruta_o_msg))

    def _generar_clave_safe(self, clave: str) -> Tuple[bool, str]:
        """Wrapper que captura excepciones y devuelve (ok, ruta|mensaje)."""
        try:
            ruta = self.generar_ficha(clave)
            return True, ruta
        except Exception as e:
            logger.error(f"[{clave}] ✗ {type(e).__name__}: {e}")
            return False, f"{type(e).__name__}: {e}"