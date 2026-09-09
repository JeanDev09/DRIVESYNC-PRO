import shutil
import tkinter as tk
from pathlib import Path
from tkinter import filedialog

REQ_SPACE_GB = 1.0


def seleccionar_carpeta_local(console):
    console.print("\n  [cyan]Selecciona la carpeta de destino...[/cyan]")
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        ruta = filedialog.askdirectory(
            title="Selecciona dónde guardar los Reels"
        )
    finally:
        root.destroy()

    if not ruta:
        return None

    path = Path(ruta)
    try:
        uso = shutil.disk_usage(path)
        libre_gb = uso.free / (1024 ** 3)
        console.print(
            f"\n  [dim]Espacio actualmente libre: {libre_gb:.2f} GB[/dim]"
        )
        return path
    except Exception as e:
        console.print(f"\n  [red]No se pudo comprobar el disco: {e}[/red]")
        return None