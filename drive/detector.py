import ctypes
import shutil
import string
from pathlib import Path
from models import DriveUnit


def obtener_etiqueta_volumen(raiz: str) -> str:
    try:
        buffer = ctypes.create_unicode_buffer(1024)
        resultado = ctypes.windll.kernel32.GetVolumeInformationW(
            ctypes.c_wchar_p(raiz),
            buffer,
            ctypes.sizeof(buffer),
            None,
            None,
            None,
            None,
            0,
        )
        if resultado and buffer.value:
            return buffer.value
    except Exception:
        pass
    return "Local Drive"


def buscar_carpeta_drive(raiz: Path):
    posibles = ["Mi unidad", "My Drive"]
    for nombre in posibles:
        carpeta = raiz / nombre
        if carpeta.is_dir():
            return carpeta
    return None


def detectar_unidades_drive():
    unidades = []
    for letra in string.ascii_uppercase:
        raiz = Path(f"{letra}:/")
        if not raiz.exists():
            continue
        carpeta_drive = buscar_carpeta_drive(raiz)
        if not carpeta_drive:
            continue
        try:
            uso = shutil.disk_usage(raiz)
            unidades.append(
                DriveUnit(
                    letra=str(raiz),
                    ruta_unidad=carpeta_drive,
                    etiqueta=obtener_etiqueta_volumen(str(raiz)),
                    libre_bytes=uso.free,
                    total_bytes=uso.total,
                )
            )
        except Exception:
            continue
    return unidades