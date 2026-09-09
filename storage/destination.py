import re
import shutil
from pathlib import Path

INVALID_WINDOWS_CHARS = r'<>:"/\|?*'


def limpiar_nombre_windows(nombre: str) -> str:
    nombre = str(nombre).strip()
    for char in INVALID_WINDOWS_CHARS:
        nombre = nombre.replace(char, "_")
    nombre = re.sub(r"\s+", " ", nombre)
    nombre = nombre.rstrip(" .")
    if not nombre:
        return "Pack de Reels"
    return nombre


def obtener_espacio_libre(ruta: Path) -> int:
    uso = shutil.disk_usage(ruta)
    return uso.free


def crear_directorio(ruta: Path):
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def verificar_espacio(destino: Path, necesario: int):
    try:
        libre = obtener_espacio_libre(destino)
        return {
            "ok": libre >= necesario,
            "libre": libre,
            "necesario": necesario,
            "faltante": max(0, necesario - libre),
        }
    except Exception as exc:
        return {
            "ok": False,
            "libre": 0,
            "necesario": necesario,
            "faltante": necesario,
            "error": str(exc),
        }