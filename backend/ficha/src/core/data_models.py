from dataclasses import dataclass, field
from typing import List, Optional
import pandas as pd


@dataclass
class FichaData:
    """Estructura centralizada de datos para un hospital (Contrato de Datos)."""

    # 1. IDENTIDAD Y GENERALES (Result Set 1 del SP)
    clave: str
    nombre: str
    estado: str
    fecha_inicio: Optional[str]
    antiguedad: int
    es_hr: bool
    tiene_mf: bool
    tipo_unidad: str

    # 2. DATOS CRUDOS (DataFrames directos de SQL)
    df_productividad: pd.DataFrame       # RS 2
    df_indicadores_dg: pd.DataFrame      # RS 3
    df_personal: pd.DataFrame            # RS 4
    df_comparativo_ant: pd.DataFrame     # RS 5
    df_capacidad: pd.DataFrame           # RS 6
    df_dia_tipico: pd.DataFrame          # RS 7
    df_metas: pd.DataFrame               # RS 8
    df_acumulado: pd.DataFrame           # RS 9
    df_top_especialidades: pd.DataFrame  # RS 10
    df_comparativo_int: pd.DataFrame     # RS 11
    df_comparativo_hr: pd.DataFrame      # reservado, vacío en V2

    # 3. DATOS ADICIONALES Y FORMATEO
    poblacion_regionalizacion: str = "0"
    fecha_corte_texto: str = ""

    # 4. KPIs Y LISTAS (calculados en el Processor)
    top_especialidades_lista: List[str] = field(default_factory=list)
    cartera_servicios_lista: List[str] = field(default_factory=list)
    equipo_relevante_lista: List[str] = field(default_factory=list)

    total_medicos: int = 0
    total_enfermeras: int = 0
    total_otros: int = 0
    total_personal: int = 0
    total_camas: int = 0
    total_especialidades: int = 0

    prod_esp: int = 0
    prod_iqx: int = 0
    prod_mf: int = 0
    prod_urg: int = 0
    prod_egr: int = 0
    prod_total: int = 0

    acum_esp: int = 0
    acum_iqx: int = 0
    acum_mf: int = 0

    dt_esp: int = 0
    dt_iqx: int = 0
    dt_urg: int = 0
    dt_partos: int = 0
    dt_egresos: int = 0
    dt_mf: int = 0
    dt_total: int = 0

    meta_esp: int = 0
    meta_iqx: int = 0
    avance_esp_str: str = "S/M"
    avance_iqx_str: str = "S/M"

    comp_esp_ant: int = 0
    comp_esp_aumento: int = 0
    comp_iqx_ant: int = 0
    comp_iqx_aumento: int = 0

    hr_esp_ant: int = 0
    hr_esp_act: int = 0
    hr_esp_var: str = "N/D"
    hr_iqx_ant: int = 0
    hr_iqx_act: int = 0
    hr_iqx_var: str = "N/D"

    @property
    def anio_inicio(self) -> str:
        if self.fecha_inicio and str(self.fecha_inicio).lower() not in ('none', 'nan', 'nat', ''):
            return str(self.fecha_inicio)[:4]
        return "N/D"

    @classmethod
    def desde_sql(cls, clave_unidad: str, sets: List[pd.DataFrame]):
        s1 = sets[0] if len(sets) > 0 else pd.DataFrame()
        gen = s1.iloc[0].to_dict() if not s1.empty else {}

        def get_set(idx):
            return sets[idx] if len(sets) > idx else pd.DataFrame()

        return cls(
            clave=clave_unidad,
            nombre=str(gen.get('DenominacionUnidad', '')),
            estado=str(gen.get('EntidadFederativa', '')),
            fecha_inicio=str(gen.get('FechaInicio', '')),
            antiguedad=int(gen.get('Antiguedad', 0) or 0),
            es_hr=bool(gen.get('EsHospitalRural', False)),
            tiene_mf=bool(gen.get('TieneMedicinaFamiliar', False)),
            tipo_unidad=str(gen.get('TipoUnidad', 'HOSP')),

            df_productividad=get_set(1),
            df_indicadores_dg=get_set(2),
            df_personal=get_set(3),
            df_comparativo_ant=get_set(4),
            df_capacidad=get_set(5),
            df_dia_tipico=get_set(6),
            df_metas=get_set(7),
            df_acumulado=get_set(8),
            df_top_especialidades=get_set(9),
            df_comparativo_int=get_set(10),
            df_comparativo_hr=get_set(11),
        )