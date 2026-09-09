from pathlib import Path
import win32com.client


def resolver_acceso_directo(ruta_base: Path, nombre: str, log=None):
    """
    Busca:
        ruta_base/nombre
        ruta_base/nombre.lnk
    y devuelve el directorio real.
    """
    carpeta = ruta_base / nombre
    if carpeta.is_dir():
        return carpeta

    shortcut = ruta_base / f"{nombre}.lnk"
    if not shortcut.exists():
        return None

    try:
        if log:
            log(f"Acceso directo detectado: {shortcut.name}", "INFO")
        shell = win32com.client.Dispatch("WScript.Shell")
        link = shell.CreateShortCut(str(shortcut))
        target = link.Targetpath
        if not target:
            return None
        destino = Path(target)
        if destino.exists():
            if log:
                log(f"Destino resuelto: {destino}", "OK")
            return destino
        if log:
            log(f"El destino no existe: {destino}", "ERROR")
    except Exception as exc:
        if log:
            log(f"Error leyendo {shortcut.name}: {exc}", "ERROR")
    return None