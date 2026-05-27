"""Capa de acceso a SQL Server. Devuelve FichaData a partir de la clave."""

import logging
from pathlib import Path
from typing import Optional, List
import platform
import pyodbc
import pandas as pd
from ficha.src.core.data_models import FichaData
from ficha.src.core.config import AppConfig

logger = logging.getLogger(__name__)

class DataRepository:
    """Comunicación directa con SQL Server."""
    def __init__(self, config: AppConfig):
        self.config = config
        self.creds = config.sql_creds
        self.driver = self._obtener_driver()

    def _obtener_driver(self) -> str:
        if platform.system() == "Darwin":
            rutas = [
                "/usr/local/lib/libmsodbcsql.17.dylib",
                "/opt/homebrew/lib/libmsodbcsql.17.dylib",
                "/opt/homebrew/Cellar/msodbcsql17/17.10.6.1/lib/libmsodbcsql.17.dylib",
            ]
            for r in rutas:
                if Path(r).exists():
                    return f"{{{r}}}"
            return "{ODBC Driver 17 for SQL Server}"
        return "{ODBC Driver 17 for SQL Server}"

    def _get_connection(self):
        server_completo = f"{self.creds['server']},{self.creds['port']}"
        # conn_str = (
        #     f"DRIVER={self.driver};"
        #     f"SERVER={server_completo};"
        #     f"DATABASE=DB_FichaEstatal;"
        #     f"UID={self.creds['user']};"
        #     f"PWD={self.creds['password']};"
        #     f"TrustServerCertificate=yes;" 
        #     "LoginTimeout=30;"
        # )

        conn_str = pyodbc.connect(
                f"DRIVER={self.driver};"
                f"SERVER={server_completo};"
                r"DATABASE=DB_FichaEstatal;"
                f"UID={self.creds['user']};"
                f"PWD={self.creds['password']};"      
                r"TrustServerCertificate=yes;"  
            )      

        return conn_str 
    # pyodbc.connect(conn_str)

    def obtener_datos_ficha(self, clave_presupuestal: str) -> FichaData:
        """Ejecuta el SP V2 y mapea los result sets al modelo."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "{CALL sp_GenerarDataFichaHospitalaria_V2(?)}",
                (clave_presupuestal,))

            all_sets = []
            while True:
                if cursor.description:
                    cols = [c[0] for c in cursor.description]
                    data = cursor.fetchall()
                    df = pd.DataFrame.from_records(data, columns=cols)
                else:
                    df = pd.DataFrame()
                all_sets.append(df)
                if not cursor.nextset():
                    break

            if len(all_sets) < 11:
                raise ValueError(
                    f"El SP devolvió {len(all_sets)} sets, se esperaban al menos 11"
                )

            return FichaData.desde_sql(clave_presupuestal, all_sets)

    def obtener_dato_excel(self, clave_unidad: str) -> str:
        """Suma 'pda_consultorio' del Excel de regionalización para la clave."""
        try:
            ruta_excel = self.config.project_root / "assets" / "_BD_Regionalizacion.xlsx"
            if not ruta_excel.exists():
                logger.warning(f"Excel de regionalización no encontrado: {ruta_excel}")
                return "0"
            df = pd.read_excel(ruta_excel, sheet_name="BD_Regionalizacion")
            df['cve_presupuestal'] = df['cve_presupuestal'].astype(str)
            filtro = df[df['cve_presupuestal'] == str(clave_unidad)]
            if not filtro.empty:
                total = filtro['pda_consultorio'].sum()
                return f"{int(total):,}"
            return "0"
        except Exception as e:
            logger.warning(f"Error leyendo regionalización: {e}")
            return "0"

    def obtener_unidades_batch(self, id_estado: Optional[str] = None) -> List[str]:
        """Si se pasa id_estado, filtra por ese estado; si no, trae todo."""
        query = """
            SELECT ClavePresupuestal
            FROM DB_Catalogos.dbo.CUMM_ACTUAL
            WHERE NivelAtencion IN ('Segundo Nivel', 'Tercer Nivel')
              AND (es_umae IS NULL OR es_umae = 'UMAE')
              AND DescripcionTipoServicio NOT IN ('UMFR','UMAA','CCSM','UM Temporal COVID','HPSIQMF')
        """
        params = []
        if id_estado:
            query += " AND ClaveEntidadFederativa = ?"
            params.append(id_estado)

        with self._get_connection() as conn:
            df = pd.read_sql(query, conn, params=params)
            return df['ClavePresupuestal'].astype(str).tolist()

    def obtener_todas_las_claves(self) -> List[str]:
        return self.obtener_unidades_batch(id_estado=None)