import json
import yaml
import platform
from pathlib import Path


class AppConfig:
    """
    Unifica config.yaml y secrets.json. Detecta automáticamente Mac/Windows.
    """
    def __init__(self,
                 config_rel_path="config/config.yaml",
                 secrets_rel_path="config/secrets.json"):
        self.project_root = Path(__file__).resolve().parent.parent.parent

        self.config_data = self._load_yaml(self.project_root / config_rel_path)
        self.secrets     = self._load_json(self.project_root / secrets_rel_path)

        self.home    = Path.home()
        self.os_name = platform.system()

        if self.os_name == "Darwin":
            rel_path = self.config_data['entorno']['mac']['base_relativa']
        else:
            rel_path = self.config_data['entorno']['windows']['base_relativa']

        # Si el repositorio contiene alguna de las rutas de assets locales,
        # preferimos usar project_root como base_path. Esto cubre el caso de
        # ejecución dentro de Docker cuando el repo monta las carpetas.
        rutas_locales = [
            self.config_data.get('rutas', {}).get('fotos_origen'),
            self.config_data.get('rutas', {}).get('fotos_fachada'),
            self.config_data.get('rutas', {}).get('plantilla_normal'),
            self.config_data.get('rutas', {}).get('plantilla_hr'),
        ]
        if any(r and (self.project_root / r).exists() for r in rutas_locales):
            self.base_path = self.project_root
        else:
            self.base_path = self.home / rel_path

    @staticmethod
    def _load_yaml(path: Path):
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    @staticmethod
    def _load_json(path: Path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    @property
    def sql_creds(self):
        return self.secrets['sql']

    @property
    def ruta_fotos_origen(self) -> Path:
        return self.base_path / self.config_data['rutas']['fotos_origen']

    @property
    def ruta_fotos_fachada(self) -> Path:
        return self.base_path / self.config_data['rutas']['fotos_fachada']

    @property
    def plantilla_pptx(self) -> Path:
        return self.project_root / self.config_data['rutas']['plantilla_normal']

    @property
    def plantilla_hr_pptx(self) -> Path:
        return self.project_root / self.config_data['rutas']['plantilla_hr']

    @property
    def ruta_salida(self) -> Path:
        carpeta = self.project_root / self.config_data.get('rutas', {}).get(
            'salida', 'output_fichas')
        carpeta.mkdir(parents=True, exist_ok=True)
        return carpeta