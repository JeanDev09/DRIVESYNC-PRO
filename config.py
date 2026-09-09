import os
from pathlib import Path

APP_TITLE = "DRIVESYNC PRO"
APP_SUBTITLE = "GOOGLE DRIVE BATCH CLONER"
APP_VERSION = "v4.3"
DEVELOPER = "JeanDev"
DEFAULT_ROOT_FOLDER = "Mi Unidad / Cloud Storage"
MAX_LOGS = 12

# Canales de soporte y contacto
FOROBETA_URL = "https://forobeta.com/members/jeandev.362650/"
WHATSAPP_NUMERO = "51925030997"

# Base de datos local (Persistencia de progreso y caché de tamaños)
APP_DATA_DIR = Path(os.environ.get("APPDATA", Path.home())) / "DriveSyncPro"
DB_PATH = APP_DATA_DIR / "sync_cache.db"