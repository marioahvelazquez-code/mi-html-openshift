"""
Capa de Lógica de Negocio.
Transforma DataFrames crudos del SP en KPIs, sumatorias y listas.
Diseñado para no tronar nunca: si un DF viene vacío o le falta una columna,
la métrica correspondiente queda en 0 / lista vacía.
"""
import logging
import pandas as pd
from ficha.src.core.data_models import FichaData

logger = logging.getLogger(__name__)


class DataProcessor:

    @staticmethod
    def procesar_ficha(ficha: FichaData) -> FichaData:
        """Orquesta todas las reglas de negocio."""
        DataProcessor._procesar_personal(ficha)
        DataProcessor._procesar_productividad_y_dia_tipico(ficha)
        DataProcessor._procesar_acumulado(ficha)
        DataProcessor._procesar_metas_y_avances(ficha)
        DataProcessor._procesar_capacidad_y_listas(ficha)
        DataProcessor._procesar_comparativos(ficha)
        DataProcessor._procesar_fecha_corte(ficha)
        return ficha

    # helpers
    @staticmethod
    def _safe_int(v) -> int:
        """Convierte a int de forma defensiva (NaN, None, '' → 0)."""
        try:
            if v is None or pd.isna(v):
                return 0
            return int(v)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _sumar_col(df: pd.DataFrame, col_filtro: str, valor_filtro,
                   col_suma: str) -> int:
        """Suma `col_suma` filtrando por `col_filtro == valor_filtro`."""
        if df is None or df.empty:
            return 0
        if col_filtro not in df.columns or col_suma not in df.columns:
            return 0
        try:
            return int(df.loc[df[col_filtro] == valor_filtro, col_suma].sum())
        except Exception as e:
            logger.warning(f"Error sumando {col_suma}: {e}")
            return 0

    # secciones
    @staticmethod
    def _procesar_personal(ficha: FichaData):
        df = ficha.df_personal
        if df is None or df.empty or 'Categoria' not in df.columns:
            return
        d = dict(zip(df['Categoria'], df['Total']))
        ficha.total_medicos    = DataProcessor._safe_int(d.get('Médicos', 0))
        ficha.total_enfermeras = DataProcessor._safe_int(d.get('Enfermeras', 0))
        ficha.total_otros      = DataProcessor._safe_int(d.get('Otro', 0))
        ficha.total_personal   = (ficha.total_medicos +
                                  ficha.total_enfermeras +
                                  ficha.total_otros)

    @staticmethod
    def _procesar_productividad_y_dia_tipico(ficha: FichaData):
        # Productividad semanal (RS 2)
        s = lambda ind: DataProcessor._sumar_col(
            ficha.df_productividad, 'Clave indicador', ind, 'Atenciones')
        ficha.prod_esp = s('DPM_PRODSEM_ESP')
        ficha.prod_iqx = s('DPM_PRODSEM_IQX')
        ficha.prod_mf  = s('DPM_PRODSEM_MF')

        # Urgencias y Egresos (RS 3)
        d = lambda ind: DataProcessor._sumar_col(
            ficha.df_indicadores_dg, 'nom_indicador', ind, 'valor')
        ficha.prod_urg = d('CVE_PRODSEM_URG')
        ficha.prod_egr = d('CVE_PRODSEM_EGR')

        ficha.prod_total = (ficha.prod_esp + ficha.prod_iqx + ficha.prod_mf
                            + ficha.prod_urg + ficha.prod_egr)

        # Día Típico (RS 7)
        dt = lambda c: DataProcessor._sumar_col(
            ficha.df_dia_tipico, 'Concepto', c, 'Col01')
        ficha.dt_esp     = dt('+ Consultas Especialidades')
        ficha.dt_iqx     = dt('* Intervenciones Quirúrgicas')
        ficha.dt_urg     = dt('* Atenciones Urgencias')
        ficha.dt_partos  = dt('* Partos Atendidos')
        ficha.dt_egresos = dt('* Egresos Hospitalarios')
        ficha.dt_mf      = dt('+ Consultas Medicina Familiar')
        ficha.dt_total = (ficha.dt_esp + ficha.dt_iqx + ficha.dt_urg
                          + ficha.dt_partos + ficha.dt_egresos + ficha.dt_mf)

    @staticmethod
    def _procesar_acumulado(ficha: FichaData):
        """RS 9: el SP V2 lo devuelve en columna 'Valor'; soportamos también 'Atenciones'."""
        df = ficha.df_acumulado
        if df is None or df.empty:
            return
        col = 'Valor' if 'Valor' in df.columns else 'Atenciones'
        if 'Clave indicador' not in df.columns or col not in df.columns:
            return
        s = lambda ind: DataProcessor._sumar_col(df, 'Clave indicador', ind, col)
        ficha.acum_esp = s('DPM_PRODSEM_ESP')
        ficha.acum_iqx = s('DPM_PRODSEM_IQX')
        ficha.acum_mf  = s('DPM_PRODSEM_MF')

    @staticmethod
    def _procesar_metas_y_avances(ficha: FichaData):
        df = ficha.df_metas
        if df is not None and not df.empty and 'Clave indicador' in df.columns:
            s = lambda ind: DataProcessor._sumar_col(df, 'Clave indicador', ind, 'Meta')
            ficha.meta_esp = s('DPM_PRODSEM_ESP')
            ficha.meta_iqx = s('DPM_PRODSEM_IQX')

        ficha.avance_esp_str = (
            f"{(ficha.acum_esp / ficha.meta_esp * 100):.0f}%"
            if ficha.meta_esp > 0 else "S/M")
        ficha.avance_iqx_str = (
            f"{(ficha.acum_iqx / ficha.meta_iqx * 100):.0f}%"
            if ficha.meta_iqx > 0 else "S/M")

    @staticmethod
    def _procesar_capacidad_y_listas(ficha: FichaData):
        df = ficha.df_capacidad
        if df is not None and not df.empty and 'Categoria' in df.columns:
            camas = df[df['Categoria'].isin(['Camas censables', 'Camas no censables'])]
            ficha.total_camas = DataProcessor._safe_int(camas['Total'].sum()) if not camas.empty else 0

            esp = df[df['Categoria'] == 'Total de especialidades']
            ficha.total_especialidades = DataProcessor._safe_int(esp['Total'].sum()) if not esp.empty else 0

            df_cartera = df[
                (df['Tipo'] == 'Cartera de servicios') &
                (~df['Categoria'].isin(['Total de especialidades', 'Camas totales']))
            ]
            ficha.cartera_servicios_lista = [
                f"{int(r['Total'])} {str(r['Categoria']).lower()}"
                for _, r in df_cartera.iterrows()
            ]

            df_equipo = df[df['Tipo'] == 'Equipo relevante']
            ficha.equipo_relevante_lista = [
                f"{int(r['Total'])} {str(r['Categoria']).capitalize()}"
                for _, r in df_equipo.iterrows()
            ]

        # Top 10 Especialidades (RS 10)
        df_top = ficha.df_top_especialidades
        if df_top is not None and not df_top.empty and 'DES_ESPECIALIDAD' in df_top.columns:
            ficha.top_especialidades_lista = [
                f"{n}. {str(row['DES_ESPECIALIDAD']).strip()}"
                for n, (_, row) in enumerate(df_top.head(10).iterrows(), start=1)
            ]

    @staticmethod
    def _procesar_comparativos(ficha: FichaData):
        # RS 5 — comparativo semanal vs año anterior
        df5 = ficha.df_comparativo_ant
        if df5 is not None and not df5.empty and 'Indicador' in df5.columns:
            cols_valor = sorted([c for c in df5.columns if c.startswith('Valor_')])
            col_ant = cols_valor[0] if cols_valor else None  # ej. 'Valor_2024'

            def ext(ind):
                fila = df5[df5['Indicador'] == ind]
                if fila.empty:
                    return 0, 0
                v = fila[col_ant].iloc[0] if col_ant else 0
                a = fila['Aumento_Absoluto'].iloc[0] if 'Aumento_Absoluto' in df5.columns else 0
                return DataProcessor._safe_int(v), DataProcessor._safe_int(a)

            ficha.comp_esp_ant, ficha.comp_esp_aumento = ext('PRODSEM_ESP')
            ficha.comp_iqx_ant, ficha.comp_iqx_aumento = ext('PRODSEM_IQX')

        # RS 11 — comparativo interanual acumulado
        df11 = ficha.df_comparativo_int
        if df11 is not None and not df11.empty and 'Indicador' in df11.columns:
            def ext_int(ind):
                fila = df11[df11['Indicador'] == ind]
                if fila.empty:
                    return 0, 0, "N/D"
                ant = DataProcessor._safe_int(fila['ValorAnterior'].iloc[0])
                act = DataProcessor._safe_int(fila['ValorActual'].iloc[0])
                var = fila['Variacion_Porcentual'].iloc[0] if 'Variacion_Porcentual' in df11.columns else None
                var_str = f"{float(var):+.1f}%" if pd.notna(var) and ant > 0 else "N/D"
                return ant, act, var_str

            ficha.hr_esp_ant, ficha.hr_esp_act, ficha.hr_esp_var = ext_int('Consultas de Especialidad')
            ficha.hr_iqx_ant, ficha.hr_iqx_act, ficha.hr_iqx_var = ext_int('Cirugías')

    @staticmethod
    def _procesar_fecha_corte(ficha: FichaData):
        df = ficha.df_productividad
        if df is None or df.empty or 'Semana' not in df.columns or 'FechaCorte' not in df.columns:
            ficha.fecha_corte_texto = ""
            return
        try:
            fila = df.dropna(subset=['Semana', 'FechaCorte']).iloc[0]
            sem = int(fila['Semana'])
            fch = pd.to_datetime(fila['FechaCorte'])
            meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                     "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            ficha.fecha_corte_texto = (
                f"semana {sem}, {fch.day:02d} de {meses[fch.month - 1]} {fch.year}"
            )
        except Exception as e:
            logger.warning(f"No se pudo formatear fecha de corte: {e}")
            ficha.fecha_corte_texto = ""