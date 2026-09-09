import os
from pathlib import Path
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich import box

from sync.analyzer import analizar_origen, calcular_espacio_necesario
from utils.formatting import format_bytes
# Importamos el nuevo menú interactivo de árbol
from ui.interactive import menu_arbol_checkbox
from config import DEFAULT_ROOT_FOLDER


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
        console.clear()
        console.print(
            Panel(
                "[bold red]No se encontró ningún contenido con el método de escaneo seleccionado.[/bold red]",
                border_style="red",
            )
        )
        return None

    console.clear()
    disponibles = sorted(disponibles, key=lambda x: x["nombre"].lower())

    # Invocamos la nueva interfaz de Árbol (File Explorer style)
    return menu_arbol_checkbox(console, "EXPLORADOR DE DIRECTORIOS", disponibles)


def solicitar_nombre_raiz(console):
    console.clear()
    panel = Panel(
        f"[white]Ingresa el nombre para la carpeta contenedora:\n[dim]Presiona ENTER directamente para usar el valor por defecto.[/dim]",
        title="[bold cyan] NOMBRE DE CARPETA RAÍZ [/bold cyan]",
        border_style="cyan",
    )
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

    console.clear()
    tabla = Table(box=box.ROUNDED, border_style="green", expand=True)
    tabla.add_column("Concepto", style="bold white")
    tabla.add_column("Resultado", justify="right")
    tabla.add_row("Contenido seleccionado", f"{len(seleccion_final)} paquete(s)")
    tabla.add_row("Total de archivos", f"{espacio['archivos']:,}")
    tabla.add_row("Espacio necesario", format_size(espacio["bytes"]))
    tabla.add_row("Destino final", str(base_dir))

    console.print(Panel(tabla, title="[bold green] PLAN DE SINCRONIZACIÓN [/bold green]", border_style="green"))

    return {
        "seleccion": seleccion_final,
        "origenes": origenes,
        "nombre_raiz": nombre_raiz,
        "base_dir": base_dir,
        "archivos": espacio["archivos"],
        "bytes": espacio["bytes"],
    }