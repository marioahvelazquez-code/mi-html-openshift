
from decimal import Decimal, InvalidOperation
from datetime import time
import math
import re

import pandas as pd


def validar_excel(archivo, hoja, diccionario):
    """
    Valida un Excel contra las reglas de cat_diccionario_campo.

    No modifica el archivo original ni escribe en SQL Server.
    """

    if not diccionario:
        raise ValueError("No existen reglas de validación para el tema")

    if not archivo.name.lower().endswith(".xlsx"):
        raise ValueError("Solo se permiten archivos .xlsx")

    archivo.seek(0)

    try:
        df = pd.read_excel(
            archivo,
            sheet_name=hoja,
            engine="openpyxl",
            dtype=str,
            keep_default_na=False,
        )
    except (ValueError, KeyError) as exc:
        raise ValueError(
            "No se pudo leer la hoja indicada del Excel"
        ) from exc

    # Normalizar encabezados.
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
    )

    # Ignorar columnas sin encabezado
    df = df.loc[
        :, ~df.columns.str.contains(r"^Unnamed", case=False)
    ]
    df = df.loc[:, df.columns != ""]

    columnas_excel = list(df.columns)
    columnas_esperadas = [d[0] for d in diccionario]

    faltantes = [
        c for c in columnas_esperadas
        if c not in columnas_excel
    ]
    extras = [
        c for c in columnas_excel
        if c not in columnas_esperadas
    ]
    duplicadas = df.columns[df.columns.duplicated()].tolist()

    if faltantes or extras or duplicadas:
        return {
            "valido": False,
            "error": "Estructura de columnas inválida",
            "faltantes": faltantes,
            "extras": extras,
            "duplicadas": duplicadas,
            "columnas_esperadas": columnas_esperadas,
            "errores": [],
            "total_registros": 0,
        }

    configuraciones = {
        d[0]: {
            "obligatorio": bool(d[2]),
            "tipo": str(d[3]).strip().lower(),
            "longitud": d[4],
        }
        for d in diccionario
    }

    errores = []
    total_registros = 0

    for numero_fila, valores in enumerate(
        df.itertuples(index=False, name=None),
        start=2,
    ):
        fila = dict(zip(df.columns, valores))

        # Ignorar filas totalmente vacías, pero seguir revisando.
        if all(
            valor is None or str(valor).strip() == ""
            for valor in fila.values()
        ):
            continue

        total_registros += 1

        for columna, valor in fila.items():
            config = configuraciones[columna]

            if valor is None or pd.isna(valor):
                valor = None
            elif isinstance(valor, str):
                valor = valor.strip() or None

            if valor is None:
                if config["obligatorio"]:
                    errores.append({
                        "fila": numero_fila,
                        "columna": columna,
                        "error": "Campo obligatorio vacío",
                    })
                continue

            tipo = config["tipo"]

            if tipo == "int":
                try:
                    numero = Decimal(str(valor))
                    if (
                        not numero.is_finite()
                        or numero != numero.to_integral_value()
                    ):
                        raise ValueError()
                except (InvalidOperation, ValueError, TypeError):
                    errores.append({
                        "fila": numero_fila,
                        "columna": columna,
                        "error": f"Debe ser un número entero: {valor}",
                    })

            elif tipo == "decimal":
                try:
                    numero = Decimal(str(valor))
                    if not numero.is_finite():
                        raise ValueError()
                except (InvalidOperation, ValueError, TypeError):
                    errores.append({
                        "fila": numero_fila,
                        "columna": columna,
                        "error": f"Debe ser numérico: {valor}",
                    })

            elif tipo == "float":
                try:
                    numero = float(str(valor))
                    if not math.isfinite(numero):
                        raise ValueError()
                except (ValueError, TypeError, OverflowError):
                    errores.append({
                        "fila": numero_fila,
                        "columna": columna,
                        "error": f"Debe ser un número válido: {valor}",
                    })

            elif tipo == "time":
                texto = str(valor).strip()
                patron = r"\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?"
                try:
                    if not re.fullmatch(patron, texto):
                        raise ValueError()
                    time.fromisoformat(texto)
                except (ValueError, TypeError):
                    errores.append({
                        "fila": numero_fila,
                        "columna": columna,
                        "error": (
                            f"Hora inválida: {valor}. "
                            "Formatos permitidos: HH:MM, HH:MM:SS "
                            "o HH:MM:SS.ffffff"
                        ),
                    })

            elif tipo in ("date", "datetime"):
                try:
                    fecha = pd.to_datetime(
                        valor,
                        dayfirst=True,
                        errors="raise",
                    )
                    if pd.isna(fecha):
                        raise ValueError()
                except (ValueError, TypeError, OverflowError):
                    errores.append({
                        "fila": numero_fila,
                        "columna": columna,
                        "error": f"Fecha inválida: {valor}",
                    })

            elif (
                tipo in ("char", "varchar", "nchar", "nvarchar", "text")
                and config["longitud"] is not None
            ):
                if len(str(valor)) > int(config["longitud"]):
                    errores.append({
                        "fila": numero_fila,
                        "columna": columna,
                        "error": (
                            f"Excede longitud {config['longitud']}. "
                            f"Valor recibido: {valor}"
                        ),
                    })

    if total_registros == 0:
        return {
            "valido": False,
            "error": "El archivo no contiene registros",
            "errores": [],
            "total_registros": 0,
        }

    return {
        "valido": len(errores) == 0,
        "error": "Errores de validación" if errores else None,
        "errores": errores,
        "total_registros": total_registros,
    }
