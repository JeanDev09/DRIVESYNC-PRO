import os
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich import box
from storage.persistence import obtener_tamano_carpeta_persistente
from utils.formatting import format_bytes


def leer_tecla() -> str:
    if os.name == "nt":
        import msvcrt
        ch = msvcrt.getwch()
        if ch in ("\x00", "\xe0"):
            sub = msvcrt.getwch()
            if sub == "H":
                return "UP"
            elif sub == "P":
                return "DOWN"
            elif sub == "K":
                return "LEFT"
            elif sub == "M":
                return "RIGHT"
            return "SPECIAL"
        if ch in ("\r", "\n"): return "ENTER"
        if ch == " ": return "SPACE"
        if ch == "\x1b": return "ESC"
        if ch == "\x03": raise KeyboardInterrupt
        return ch.lower()
    else:
        import tty, termios
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                ch2 = sys.stdin.read(1)
                if ch2 == "[":
                    ch3 = sys.stdin.read(1)
                    if ch3 == "A": return "UP"
                    if ch3 == "B": return "DOWN"
                    if ch3 == "C": return "RIGHT"
                    if ch3 == "D": return "LEFT"
                return "ESC"
            if ch in ("\r", "\n"): return "ENTER"
            if ch == " ": return "SPACE"
            return ch.lower()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


def menu_radio(console: Console, titulo: str, opciones: list[dict], default_idx: int = 0) -> int | None:
    cursor = default_idx
    total = len(opciones)

    def render():
        tabla = Table(box=box.ROUNDED, border_style="cyan", expand=True)
        tabla.add_column("", width=2, justify="center")
        tabla.add_column("Sel", width=4, justify="center")
        tabla.add_column("Opción", style="bold white", ratio=1)
        tabla.add_column("Detalle", justify="right", style="cyan")
        for i, opc in enumerate(opciones):
            es_cursor = i == cursor
            puntero = "[bold cyan]>[/bold cyan]" if es_cursor else " "
            radio = "[bold green](•)[/bold green]" if es_cursor else "[dim]( )[/dim]"
            estilo_texto = "bold bright_white" if es_cursor else "white"
            tabla.add_row(puntero, radio, f"[{estilo_texto}]{opc['titulo']}[/{estilo_texto}]", opc.get("detalle", ""))

        footer = "\n  [bold cyan]↑/↓[/bold cyan] Mover cursor       [bold cyan]Enter[/bold cyan] Seleccionar       [bold cyan]C[/bold cyan] Cancelar"
        return Panel(tabla, title=f"[bold cyan] {titulo} [/bold cyan]", subtitle=footer, border_style="cyan")

    # AQUÍ ESTÁ EL CAMBIO CLAVE: transient=True
    with Live(render(), console=console, auto_refresh=False, transient=True) as live:
        while True:
            live.update(render(), refresh=True)
            tecla = leer_tecla()
            if tecla == "UP":
                cursor = (cursor - 1) % total
            elif tecla == "DOWN":
                cursor = (cursor + 1) % total
            elif tecla == "ENTER":
                return cursor
            elif tecla in ("c", "esc"):
                return None


def menu_arbol_checkbox(console: Console, titulo: str, items_raiz: list[dict]) -> list[dict] | None:
    console.print(
        "\n[dim cyan]Calculando tamaños de carpetas desde caché (esto puede tardar unos segundos la primera vez)...[/dim cyan]")

    def crear_nodo(nombre_relativo: str, ruta: Path, nivel: int = 0, padre=None, estado_heredado=0):
        tamano = obtener_tamano_carpeta_persistente(str(ruta))
        tamano_str = format_bytes(tamano)
        nombre_base = ruta.name if nivel > 0 else nombre_relativo
        nombre_display = f"{nombre_base} [dim yellow]({tamano_str})[/dim yellow]"

        return {
            "nombre_relativo": nombre_relativo,
            "nombre_display": nombre_display,
            "ruta": ruta,
            "nivel": nivel,
            "padre": padre,
            "hijos": [],
            "expandido": False,
            "cargado": False,
            "estado_sel": estado_heredado
        }

    nodos_raiz = [crear_nodo(item["nombre"], item["ruta"], 0, None) for item in items_raiz]

    def obtener_visibles():
        vis = []

        def rec(lista):
            for n in lista:
                vis.append(n)
                if n["expandido"]: rec(n["hijos"])

        rec(nodos_raiz)
        return vis

    def cargar_hijos(nodo):
        if nodo["cargado"]: return
        try:
            for item in os.listdir(nodo["ruta"]):
                if item.lower() in ["desktop.ini", "thumbs.db", ".ds_store", ".shortcut-targets-by-id"]: continue
                ruta_hijo = nodo["ruta"] / item
                if ruta_hijo.is_dir():
                    nombre_rel = f"{nodo['nombre_relativo']}/{item}"
                    estado_hijo = 2 if nodo["estado_sel"] == 2 else 0
                    nodo["hijos"].append(crear_nodo(nombre_rel, ruta_hijo, nodo["nivel"] + 1, nodo, estado_hijo))
            nodo["hijos"] = sorted(nodo["hijos"], key=lambda x: x["nombre_display"].lower())
            nodo["cargado"] = True
        except Exception:
            nodo["cargado"] = True

    def forzar_estado_descendientes(nodo, estado):
        nodo["estado_sel"] = estado
        for hijo in nodo["hijos"]:
            forzar_estado_descendientes(hijo, estado)

    def actualizar_estado_ascendentes(nodo):
        padre = nodo["padre"]
        if not padre: return

        if padre["hijos"]:
            estados_hijos = [h["estado_sel"] for h in padre["hijos"]]
            if all(e == 2 for e in estados_hijos):
                padre["estado_sel"] = 2
            elif all(e == 0 for e in estados_hijos):
                padre["estado_sel"] = 0
            else:
                padre["estado_sel"] = 1

        actualizar_estado_ascendentes(padre)

    cursor = 0
    mensaje_error = ""
    visibles = obtener_visibles()

    def render():
        tabla = Table(box=box.ROUNDED, border_style="cyan", expand=True)
        tabla.add_column("", width=2, justify="center")
        tabla.add_column("Estructura de Directorios", style="bold white", ratio=1)

        for i, nodo in enumerate(visibles):
            es_cursor = i == cursor
            puntero = "[bold cyan]>[/bold cyan]" if es_cursor else " "

            if nodo["estado_sel"] == 2:
                check = "[bold green]\\[x][/bold green]"
            elif nodo["estado_sel"] == 1:
                check = "[bold yellow]\\[-][/bold yellow]"
            else:
                check = "[dim]\\[ ][/dim]"

            indent = "    " * nodo["nivel"]
            icono = "[cyan]▼[/cyan]" if nodo["expandido"] else "[cyan]▶[/cyan]"

            estilo = "bold bright_white" if es_cursor else "white"
            texto = f"{indent}{icono} {check} [{estilo}]{nodo['nombre_display']}[/{estilo}]"

            tabla.add_row(puntero, texto)

        footer = (
            "\n  [bold cyan]↑/↓[/bold cyan] Mover   "
            "[bold cyan]→[/bold cyan] Expandir   "
            "[bold cyan]←[/bold cyan] Contraer   "
            "[bold cyan]Espacio[/bold cyan] Seleccionar   "
            "[bold cyan]Enter[/bold cyan] Confirmar"
        )
        if mensaje_error:
            footer += f"\n\n  {mensaje_error}"

        return Panel(tabla, title=f"[bold cyan] {titulo} [/bold cyan]", subtitle=footer, border_style="cyan")

    # AQUÍ ESTÁ EL CAMBIO CLAVE: transient=True
    with Live(render(), console=console, auto_refresh=False, transient=True) as live:
        while True:
            live.update(render(), refresh=True)
            tecla = leer_tecla()
            total = len(visibles)

            if tecla == "UP":
                cursor = (cursor - 1) % total if total > 0 else 0
                mensaje_error = ""
            elif tecla == "DOWN":
                cursor = (cursor + 1) % total if total > 0 else 0
                mensaje_error = ""
            elif tecla == "RIGHT":
                nodo = visibles[cursor]
                if not nodo["expandido"]:
                    cargar_hijos(nodo)
                    if nodo["hijos"]:
                        nodo["expandido"] = True
                        visibles = obtener_visibles()
            elif tecla == "LEFT":
                nodo = visibles[cursor]
                if nodo["expandido"]:
                    nodo["expandido"] = False
                    visibles = obtener_visibles()
                elif nodo["padre"]:
                    cursor = visibles.index(nodo["padre"])
            elif tecla == "SPACE":
                nodo = visibles[cursor]
                nuevo_estado = 0 if nodo["estado_sel"] == 2 else 2
                forzar_estado_descendientes(nodo, nuevo_estado)
                actualizar_estado_ascendentes(nodo)
                mensaje_error = ""
            elif tecla == "ENTER":
                elegidos = []

                def recolectar(lista):
                    for n in lista:
                        if n["estado_sel"] == 2:
                            elegidos.append({"nombre": n["nombre_relativo"], "ruta": n["ruta"]})
                        elif n["estado_sel"] == 1:
                            recolectar(n["hijos"])

                recolectar(nodos_raiz)
                if not elegidos:
                    mensaje_error = "[bold red]  Debes seleccionar al menos un elemento.[/bold red]"
                    continue
                return elegidos
            elif tecla in ("c", "esc"):
                return None