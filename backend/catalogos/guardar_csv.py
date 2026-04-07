import csv
from pathlib import Path


CSV_FILENAME = "arquitectura_seguridad.csv"
CSV_FIELDS = [
    "variable",
    "definicion",
    "tipo",
    "unidadMedicion",
    "fuente",
    "consistente",
    "disponible",
    "confidencial",
    "sensible",
    "resumen",
    "observaciones",
]


def _resolve_csv_path() -> Path:
    shared_assets = Path("/shared-assets")
    if shared_assets.exists():
        return shared_assets / CSV_FILENAME

    return Path(__file__).resolve().parents[2] / "frontend" / "src" / "assets" / CSV_FILENAME


def guardar_fila_arquitectura(data):
    """Guarda una fila de datos en un CSV compartido con el frontend."""
    csv_path = _resolve_csv_path()
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = csv_path.exists()

    try:
        row = {field: data.get(field, "") for field in CSV_FIELDS}

        with open(csv_path, "a", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=CSV_FIELDS)

            if not file_exists:
                writer.writeheader()

            writer.writerow(row)

        return True, str(csv_path)
    except Exception as error:
        return False, str(error)
