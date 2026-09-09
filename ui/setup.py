import os
from pathlib import Path
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich import box

from sync.analyzer import analizar_origen, calcular_espacio_necesario
from utils.formatting import format_bytes
from ui.interactive import menu_arbol_checkbox
from config import DEFAULT_ROOT_FOLDER
from ui.theme import clear_view, footer, screen_header, truncate_middle


def format_size(value):
    return format_bytes(value)


def seleccionar_contenido(console, drive_raiz, modo_escaneo=0):
    disponibles = []
    nombres_agregados = set()
    drive_raiz = Path(drive_raiz)

    try:
        elementos_raiz = os.listdir(drive_raiz)
    except Exception as e:
        console.print(f"[bold red]Error leyendo la unidad: {e}[/bold red]")
        return None

    # MODO 0: Escanear shortcuts o accesos directos
    if modo_escaneo == 0:
        for item in elementos_raiz:
            if item.lower().endswith(".lnk"):
                nombre_limpio = item[:-4]
                if nombre_limpio not in nombres_agregados:
                    from drive.shortcuts import resolver_acceso_directo
                    origen = resolver_acceso_directo(drive_raiz, nombre_limpio)
                    if origen:
                        disponibles.append({"nombre": nombre_limpio, "ruta": origen})
                        nombres_agregados.add(nombre_limpio)

        ruta_targets = drive_raiz / ".shortcut-targets-by-id"
        if ruta_targets.exists() and ruta_targets.is_dir():
            try:
                for id_folder in os.listdir(ruta_targets):
                    ruta_id = ruta_targets / id_folder
                    if ruta_id.is_dir():
                        for sub_item in os.listdir(ruta_id):
                            ruta_real = ruta_id / sub_item
                            if ruta_real.is_dir() and sub_item not in nombres_agregados:
                                disponibles.append({
                                    "nombre": sub_item,
                                    "ruta": ruta_real
                                })
                                nombres_agregados.add(sub_item)
            except Exception:
                pass

    # MODO 1: Escanear carpetas (Normales)
    elif modo_escaneo == 1:
        for item in elementos_raiz:
            if item.lower() in ["desktop.ini", "thumbs.db", ".ds_store", ".shortcut-targets-by-id"]:
                continue

            ruta_item = drive_raiz / item
            if ruta_item.is_dir():
                disponibles.append({"nombre": item, "ruta": ruta_item})
                nombres_agregados.add(item)

    if not disponibles:
        clear_view(console)
        console.print(
            Panel(
                "[bold red]No se encontró ningún contenido con el método de escaneo seleccionado.[/bold red]",
                border_style="red",
            )
        )
        return None

    clear_view(console)
    disponibles = sorted(disponibles, key=lambda x: x["nombre"].lower())

    return menu_arbol_checkbox(console, "EXPLORADOR DE DIRECTORIOS", disponibles)


def solicitar_nombre_raiz(console):
    clear_view(console)
    panel = Panel(Group(screen_header("IDLE", "Define la carpeta que contendrá la sincronización."),
                        "[white]Nombre de carpeta raíz[/white]\n[dim]Pulsa Enter para usar el valor sugerido.[/dim]"),
                  border_style="bright_black", box=box.HORIZONTALS, padding=(0, 1))
    console.print(panel)

    while True:
        nombre = Prompt.ask("\n  [bold cyan]Nombre[/bold cyan]", default=DEFAULT_ROOT_FOLDER).strip()
        if not nombre:
            nombre = DEFAULT_ROOT_FOLDER

        caracteres_invalidos = '<>:"/\\|?*'
        if any(char in nombre for char in caracteres_invalidos):
            console.print("  [red]El nombre contiene caracteres no permitidos por Windows (<>:\"/\\|?*)[/red]")
            continue
        if nombre in {".", ".."}:
            console.print("  [red]Nombre inválido.[/red]")
            continue

        return nombre


def preparar_seleccion(console, drive_raiz, destino, modo_escaneo=0, tui=None):
    # La selección ya retorna los nodos óptimos del árbol
    seleccion_final = seleccionar_contenido(console, drive_raiz, modo_escaneo)

    if not seleccion_final:
        return None

    if tui:
        tui.set_status("SCANNING", "Preparando inventario...")
        tui.refresh()

    origenes = []
    for item in seleccion_final:
        origen = analizar_origen(
            nombre=item["nombre"],
            origen=item["ruta"],
            tui=tui,
        )
        origenes.append(origen)

    espacio = calcular_espacio_necesario(origenes)
    nombre_raiz = solicitar_nombre_raiz(console)
    base_dir = Path(destino) / nombre_raiz

    clear_view(console)
    tabla = Table.grid(expand=True, padding=(0, 1))
    tabla.add_column(style="dim cyan", width=13)
    tabla.add_column(style="white", ratio=1)
    tabla.add_row("ORIGEN", truncate_middle(drive_raiz, 72))
    tabla.add_row("DESTINO", truncate_middle(base_dir, 72))
    tabla.add_row("ELEMENTOS", f"{len(seleccion_final)} paquetes · {espacio['archivos']:,} archivos")
    tabla.add_row("TAMAÑO", format_size(espacio["bytes"]))
    tabla.add_row("MODO", "Accesos directos" if modo_escaneo == 0 else "Carpetas")
    console.print(Panel(Group(screen_header("IDLE", "Revisa el alcance antes de iniciar."), tabla,
                              footer(("Enter", "iniciar"), ("Esc", "cancelar"))),
                        title=" RESUMEN DE SINCRONIZACIÓN ", title_align="left",
                        border_style="bright_black", box=box.HORIZONTALS, padding=(0, 1)))

    return {
        "seleccion": seleccion_final,
        "origenes": origenes,
        "nombre_raiz": nombre_raiz,
        "base_dir": base_dir,
        "archivos": espacio["archivos"],
        "bytes": espacio["bytes"],
    }


def confirmar_inicio(console) -> bool:
    """Ask for confirmation immediately below the visual plan summary."""
    try:
        answer = Prompt.ask("[bold cyan]¿Iniciar sincronización?[/bold cyan]", choices=["s", "n"], default="s")
    except (KeyboardInterrupt, EOFError):
        return False
    return answer.lower() == "s"
