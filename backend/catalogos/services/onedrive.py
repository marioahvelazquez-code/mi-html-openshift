
import os
import re
import tempfile
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

from django.conf import settings


def guardar_excel_onedrive(
    archivo,
    ruta_relativa,
    nombre_archivo,
):
    carpeta_base = Path(
        settings.ONEDRIVE_EXCEL_PATH
    ).resolve(strict=True)

    if not carpeta_base.is_dir():
        raise FileNotFoundError(
            "La carpeta base de OneDrive no está disponible"
        )

    # Validar la ruta que viene de SQL Server.
    if not isinstance(ruta_relativa, str):
        raise ValueError("Ruta relativa inválida")

    ruta = ruta_relativa.strip().replace("\\", "/")

    partes = ruta.split("/")

    if (
        not ruta
        or ruta.startswith("/")
        or any(p in ("", ".", "..") for p in partes)
        or any(":" in p or "\x00" in p for p in partes)
    ):
        raise ValueError("Ruta de OneDrive no permitida")

    carpeta = (carpeta_base / ruta).resolve()

    if not carpeta.is_relative_to(carpeta_base):
        raise ValueError(
            "La ruta está fuera de la carpeta autorizada"
        )

    if not carpeta.is_dir():
        raise FileNotFoundError(
            f"La carpeta de destino no existe: {ruta}"
        )

    # Validar el nombre definido en SQL Server.
    nombre_base = str(nombre_archivo).strip()

    if not re.fullmatch(r"[A-Za-z0-9_-]+", nombre_base):
        raise ValueError(
            "El nombre configurado contiene caracteres no permitidos"
        )

    # Fecha del día en horario de México.
    fecha = datetime.now(
        ZoneInfo("America/Mexico_City")
    ).strftime("%Y%m%d")

    nombre_final = f"{nombre_base}_{fecha}.xlsx"
    destino = carpeta / nombre_final

    temporal_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=".carga_",
            suffix=".tmp",
            dir=carpeta,
            delete=False,
        ) as temporal:

            temporal_path = Path(temporal.name)
            archivo.seek(0)

            for bloque in archivo.chunks():
                temporal.write(bloque)

            temporal.flush()
            os.fsync(temporal.fileno())

        # Si existe el mismo archivo del mismo día,
        # se reemplaza.
        os.replace(temporal_path, destino)

        return {
            "nombre": nombre_final,
            "ruta": str(destino),
            "ruta_relativa": ruta,
            "tamano": destino.stat().st_size,
        }

    finally:
        if temporal_path is not None:
            temporal_path.unlink(missing_ok=True)
