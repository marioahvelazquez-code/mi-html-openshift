### Contrato de datos entre capas de la Ficha Presidencial
### El repository entrega FuenteDatos con la informacion cruda de todas las
### fuentes. El processor construye una FichaData por entidad, ya formateada
### como texto. El renderer solo escribe lo que recibe en FichaData.

from dataclasses import dataclass, field
from typing import Optional, List, Dict


@dataclass
class Proyecto:
    """Una unidad de infraestructura, hospital o UMF.
    Parametros:
    nombre: nombre del proyecto tal como se imprime en el listado
    estatus: nuevos, proceso o planeacion, ya normalizado
    inversion: monto en mdp
    anio_apertura: ano de apertura, None cuando no viene o no es legible"""
    nombre: str
    estatus: str
    inversion: float
    anio_apertura: Optional[int] = None


@dataclass
class FuenteDatos:
    """Datos crudos de todas las fuentes, indexados por clave de entidad.
    Cada diccionario usa la clave de dos digitos como llave.
    Una entidad ausente en un diccionario significa que no hay dato."""
    catalogo: Dict[str, str] = field(default_factory=dict)
    alias: Dict[str, str] = field(default_factory=dict)
    hospitales: Dict[str, List[Proyecto]] = field(default_factory=dict)
    umf: Dict[str, List[Proyecto]] = field(default_factory=dict)
    ceci: Dict[str, dict] = field(default_factory=dict)
    equipo: Dict[str, dict] = field(default_factory=dict)
    draft: Dict[str, int] = field(default_factory=dict)
    vive_saludable: Dict[str, dict] = field(default_factory=dict)
    casa_x_casa: Dict[str, dict] = field(default_factory=dict)
    jornadas_paz: Dict[str, dict] = field(default_factory=dict)
    mexico_te_abraza: Dict[str, dict] = field(default_factory=dict)


@dataclass
class FichaData:
    """Datos de una ficha, ya formateados como texto listo para escribir.
    Un valor None significa que el dato no existe y el renderer deja intacto
    el placeholder de la plantilla. El guion se entrega ya formateado como
    texto por el processor."""
    cve_ent: str
    entidad: str

    inversion: Dict[str, Optional[str]] = field(default_factory=dict)
    hospitales: Dict[str, Optional[str]] = field(default_factory=dict)
    umf: Dict[str, Optional[str]] = field(default_factory=dict)
    ceci: Dict[str, Optional[str]] = field(default_factory=dict)
    equipo: Dict[str, Optional[str]] = field(default_factory=dict)
    vive_saludable: Dict[str, Optional[str]] = field(default_factory=dict)
    casa_x_casa: Dict[str, Optional[str]] = field(default_factory=dict)
    jornadas_paz: Dict[str, Optional[str]] = field(default_factory=dict)
    mexico_te_abraza: Dict[str, Optional[str]] = field(default_factory=dict)

    equipo_mdp: Optional[str] = None
    draft: Optional[str] = None

    # Cada elemento es una tupla de nombre de proyecto y sufijo. El sufijo
    # solo se llena en los proyectos ya concluidos.
    lista_hospitales: List[tuple] = field(default_factory=list)
    lista_umf: List[tuple] = field(default_factory=list)

    aplica_ceci_concluido: bool = False
    aplica_jornadas_paz: bool = False
    aplica_mexico_te_abraza: bool = False
    nota_jornadas_paz: Optional[str] = None