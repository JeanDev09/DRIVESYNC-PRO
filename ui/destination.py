import shutil
import tkinter as tk
from pathlib import Path
from tkinter import filedialog
from rich.panel import Panel
from rich.console import Group
from rich import box

from ui.theme import clear_view, screen_header

REQ_SPACE_GB = 1.0


def seleccionar_carpeta_local(console):
    clear_view(console)
    console.print(Panel(Group(screen_header("IDLE", "Elige una ubicación local para recibir los archivos."),
                              "[white]PC / Disco externo[/white]\n[dim]Se abrirá el selector de carpetas del sistema.[/dim]"),
                        border_style="bright_black", box=box.HORIZONTALS, padding=(0, 1)))
    root = None
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        ruta = filedialog.askdirectory(
            title="Selecciona la carpeta de destino de DriveSync Pro"
        )
    except tk.TclError as exc:
        console.print(f"\n[yellow]No se pudo abrir el selector de carpetas: {exc}[/yellow]")
        return None
    finally:
        if root is not None:
            root.destroy()

    if not ruta:
        return None

    path = Path(ruta)
    try:
        uso = shutil.disk_usage(path)
        libre_gb = uso.free / (1024 ** 3)
        console.print(
            f"\n[green]✓ Destino seleccionado[/green]  [dim]{path} · {libre_gb:.2f} GB libres[/dim]"
        )
        return path
    except Exception as e:
        console.print(f"\n  [red]No se pudo comprobar el disco: {e}[/red]")
        return None
