### Logica de negocio de la Ficha Presidencial
### Toma los datos crudos del repository y construye una FichaData por entidad,
### con todos los valores ya formateados como texto. Aqui viven las reglas de
### calculo, el guion para cero y la decision de que bloques se eliminan.

import unicodedata

import config
from data_models import FichaData


def formato(valor):
    """Formatea un numero como entero con separador de miles. A partir de un
    millon se abrevia con un decimal para que quepa en el textbox.
    Devuelve None cuando el dato no existe, para que el renderer deje el
    placeholder de la plantilla, y guion cuando el dato existe y es cero.
    Parametros:
    valor: numero o None"""
    if valor is None:
        return None
    if round(valor) == 0:
        return config.GUION
    if abs(valor) >= config.UMBRAL_MILLONES:
        return config.FORMATO_MILLONES.format(valor / config.UMBRAL_MILLONES)
    return f"{round(valor):,.0f}"


def formato_guion(valor):
    """Igual que formato, pero un dato inexistente tambien se pinta como guion.
    Se usa en los bloques donde la ausencia significa cero.
    Parametros:
    valor: numero o None"""
    if valor is None:
        return config.GUION
    return formato(valor)


def clave_orden(texto):
    """Devuelve la llave de ordenamiento alfabetico sin acentos.
    Parametros:
    texto: nombre del proyecto"""
    descompuesto = unicodedata.normalize("NFKD", texto.upper())
    return "".join(c for c in descompuesto if not unicodedata.combining(c))


def detalle_proyecto(proyecto):
    """Arma el detalle entre parentesis que acompana al nombre del proyecto.
    Incluye el monto cuando no es cero y el ano de apertura cuando existe. Si
    no hay ninguno de los dos, devuelve cadena vacia.
    Parametros:
    proyecto: objeto Proyecto"""
    partes = []

    if proyecto.inversion and round(proyecto.inversion) != 0:
        partes.append(config.FORMATO_MONTO_PROYECTO.format(
            monto=f"{round(proyecto.inversion):,.0f}"))

    if proyecto.anio_apertura:
        partes.append(config.FORMATO_ANIO_PROYECTO.format(
            anio=proyecto.anio_apertura))

    if not partes:
        return ""

    return config.FORMATO_DETALLE_PROYECTO.format(
        detalle=config.SEPARADOR_DETALLE.join(partes))


def resumen_proyectos(proyectos, bloque):
    """Calcula conteos por estatus, monto total y el listado agrupado.
    El listado se devuelve como una lista de grupos, uno por estatus con
    proyectos, en el orden de ORDEN_ESTATUS y alfabetico dentro de cada grupo.
    La numeracion es corrida entre grupos.
    Parametros:
    proyectos: lista de objetos Proyecto de una entidad
    bloque: hospitales o umf, define las etiquetas de encabezado"""
    conteos = {"nuevos": 0, "proceso": 0, "planeacion": 0}
    monto = 0.0
    for p in proyectos:
        if p.estatus in conteos:
            conteos[p.estatus] += 1
        monto += p.inversion

    etiquetas = config.ETIQUETAS_ESTATUS[bloque]
    grupos = []
    consecutivo = 1

    for estatus in config.ORDEN_ESTATUS:
        del_grupo = sorted((p for p in proyectos if p.estatus == estatus),
                           key=lambda p: clave_orden(p.nombre))
        if not del_grupo:
            continue

        renglones = []
        for proyecto in del_grupo:
            texto = config.FORMATO_RENGLON_LISTA.format(n=consecutivo,
                                                        nombre=proyecto.nombre)
            texto += detalle_proyecto(proyecto)
            renglones.append({"texto": texto, "encabezado": False})
            consecutivo += 1

        grupos.append({"encabezado": etiquetas[estatus], "renglones": renglones})

    return {
        "total": formato(len(proyectos)),
        "monto": formato(monto),
        "nuevos": formato(conteos["nuevos"]),
        "proceso": formato(conteos["proceso"]),
        "planeacion": formato(conteos["planeacion"]),
    }, grupos, monto


def aplanar(grupos):
    """Convierte los grupos en una lista plana de renglones, intercalando el
    encabezado de cada grupo antes de sus proyectos.
    Parametros:
    grupos: lista de grupos devuelta por resumen_proyectos"""
    renglones = []
    for indice, grupo in enumerate(grupos):
        renglones.append({"texto": grupo["encabezado"], "encabezado": True,
                          "grupo": indice})
        for renglon in grupo["renglones"]:
            renglones.append(dict(renglon, grupo=indice))
    return renglones


def repartir_por_grupos(grupos):
    """Reparte los grupos completos entre dos columnas, buscando el corte que
    deje el numero de renglones mas parejo. Ningun grupo se parte.
    Parametros:
    grupos: lista de grupos devuelta por resumen_proyectos"""
    tamanos = [1 + len(g["renglones"]) for g in grupos]
    total = sum(tamanos)

    mejor_corte = len(grupos)
    mejor_diferencia = None

    for corte in range(1, len(grupos) + 1):
        izquierda = sum(tamanos[:corte])
        diferencia = abs(izquierda - (total - izquierda))
        if mejor_diferencia is None or diferencia < mejor_diferencia:
            mejor_diferencia = diferencia
            mejor_corte = corte

    columna_1 = aplanar(grupos[:mejor_corte])
    columna_2 = aplanar(grupos[mejor_corte:])
    return columna_1, columna_2, mejor_diferencia


def repartir_partiendo_grupo(grupos):
    """Reparte los renglones a la mitad aunque el corte caiga dentro de un
    grupo. Cuando eso ocurre, el encabezado del grupo se repite al inicio de la
    segunda columna.
    Parametros:
    grupos: lista de grupos devuelta por resumen_proyectos"""
    renglones = aplanar(grupos)
    corte = (len(renglones) + 1) // 2

    # Un encabezado nunca se queda solo al final de la primera columna.
    if corte > 0 and renglones[corte - 1]["encabezado"]:
        corte -= 1

    columna_1 = renglones[:corte]
    columna_2 = renglones[corte:]

    if columna_2 and not columna_2[0]["encabezado"]:
        indice = columna_2[0]["grupo"]
        columna_2 = [{"texto": grupos[indice]["encabezado"], "encabezado": True,
                      "grupo": indice}] + columna_2

    return columna_1, columna_2


def repartir_listado(grupos, max_primera=None):
    """Reparte el listado agrupado en dos columnas.
    Primero intenta repartir grupos completos. Si el desbalance resultante
    rebasa MAX_DESBALANCE_COLUMNAS, parte el listado a la mitad repitiendo el
    encabezado del grupo que quedo cortado.
    Con un solo grupo corto, todo va en la primera columna y la segunda se
    elimina.
    Parametros:
    grupos: lista de grupos devuelta por resumen_proyectos
    max_primera: se conserva por compatibilidad, no se usa"""
    if not grupos:
        return [], []

    proyectos = sum(len(g["renglones"]) for g in grupos)
    if proyectos < config.MIN_ELEMENTOS_DOS_COLUMNAS:
        return aplanar(grupos), []

    columna_1, columna_2, diferencia = repartir_por_grupos(grupos)

    if not columna_2 or diferencia > config.MAX_DESBALANCE_COLUMNAS:
        return repartir_partiendo_grupo(grupos)

    return columna_1, columna_2


def construir_ficha(cve_ent, fuente):
    """Construye la FichaData de una entidad a partir de los datos crudos.
    Parametros:
    cve_ent: clave de entidad de dos digitos
    fuente: objeto FuenteDatos con todas las fuentes cargadas"""
    entidad = config.ENTIDAD_ENCABEZADO.get(cve_ent, fuente.catalogo.get(cve_ent, ""))
    ficha = FichaData(cve_ent=cve_ent, entidad=entidad)

    # Hospitales y UMF
    hospitales = fuente.hospitales.get(cve_ent, [])
    umf = fuente.umf.get(cve_ent, [])

    ficha.hospitales, lista_hosp, monto_hosp = resumen_proyectos(hospitales, "hospitales")
    ficha.umf, lista_umf, monto_umf = resumen_proyectos(umf, "umf")

    ficha.lista_hospitales = lista_hosp
    ficha.lista_umf = lista_umf

    # Equipo medico. La ausencia de la entidad significa cero, no dato faltante.
    equipo = fuente.equipo.get(cve_ent)
    if equipo is None:
        ficha.equipo = {llave: config.GUION for llave in config.ORDEN_TABLA_EQUIPO}
        monto_equipo = 0.0
    else:
        ficha.equipo = {llave: formato_guion(equipo.get(llave))
                        for llave in config.ORDEN_TABLA_EQUIPO}
        monto_equipo = equipo.get("inversion") or 0.0

    ficha.equipo_mdp = formato(monto_equipo)

    # CECI
    ceci = fuente.ceci.get(cve_ent)
    if ceci is None:
        monto_ceci = 0.0
        ficha.ceci = {llave: None for llave in config.SHAPES_CECI}
    else:
        monto_ceci = ceci.get("inversion") or 0.0
        ficha.ceci = {
            "monto": formato(monto_ceci),
            "meta": formato(ceci.get("meta")),
            "proceso": formato(ceci.get("proceso")),
            "planeacion": formato(ceci.get("planeacion")),
            "concluido": formato(ceci.get("concluido")),
        }
        # La casilla de concluido solo se muestra cuando la entidad ya tiene
        # alguno. En las demas el grupo se elimina y las casillas restantes se
        # reacomodan dentro del area.
        ficha.aplica_ceci_concluido = bool(ceci.get("concluido"))

    # Inversion. Infraestructura es hospitales mas UMF, mas conservacion en las
    # entidades que la reportan. El total suma los tres conceptos.
    monto_conservacion = config.CONSERVACION_MDP.get(cve_ent, 0)
    monto_infra = monto_hosp + monto_umf + monto_conservacion
    ficha.inversion = {
        "infraestructura": formato(monto_infra),
        "equipo": formato(monto_equipo),
        "ceci": formato(monto_ceci),
        "total": formato(monto_infra + monto_equipo + monto_ceci),
    }

    # Draft 2026
    ficha.draft = formato(fuente.draft.get(cve_ent))

    # Vive Saludable
    vive = fuente.vive_saludable.get(cve_ent)
    if vive is not None:
        ficha.vive_saludable = {llave: formato(vive.get(llave))
                                for llave in config.SHAPES_VIVE_SALUDABLE}

    # Casa por Casa
    casa = fuente.casa_x_casa.get(cve_ent)
    if casa is not None:
        ficha.casa_x_casa = {llave: formato(casa.get(llave))
                             for llave in config.SHAPES_CASA_X_CASA}

    # Jornadas de Paz. Si la entidad no aparece en el archivo, el bloque se
    # elimina completo de la diapositiva.
    jornadas = fuente.jornadas_paz.get(cve_ent)
    if jornadas is not None:
        ficha.aplica_jornadas_paz = True
        ficha.jornadas_paz = {llave: formato(jornadas.get(llave))
                              for llave in config.SHAPES_JP}
        if cve_ent in config.JORNADAS_PAZ_2025:
            n_jornadas, n_atenciones = config.JORNADAS_PAZ_2025[cve_ent]
            ficha.nota_jornadas_paz = config.NOTA_JP_TEXTO.format(
                jornadas=f"{n_jornadas:,.0f}",
                atenciones=f"{n_atenciones:,.0f}",
            )

    # Mexico Te Abraza. Mismo criterio que Jornadas de Paz.
    abraza = fuente.mexico_te_abraza.get(cve_ent)
    if abraza is not None:
        ficha.aplica_mexico_te_abraza = True
        ficha.mexico_te_abraza = {llave: formato_guion(abraza.get(llave))
                                  for llave in config.SHAPES_MTA}

    return ficha