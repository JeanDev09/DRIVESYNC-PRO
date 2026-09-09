import sys
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from config import APP_TITLE, APP_SUBTITLE, APP_VERSION, DEVELOPER
from drive.detector import detectar_unidades_drive
from ui.interactive import menu_radio
from ui.destination import seleccionar_carpeta_local
from ui.setup import preparar_seleccion
from ui.tui import ReelsTUI
from ui.final import mostrar_final
from sync.copier import ejecutar_sincronizacion
from storage.persistence import init_database

console = Console()


def flujo_principal():
    console.clear()
    unidades = detectar_unidades_drive()
    if not unidades:
        console.print("\n[bold red]✖ No se detectaron unidades de Google Drive en este equipo.[/bold red]")
        Prompt.ask("Presiona ENTER para volver...")
        return

    opciones_origen = [{"titulo": u.nombre_limpio, "detalle": f"Google Drive = {u.libre_gb:.1f} GB Libres"} for u in
                       unidades]

    idx_origen = menu_radio(console, "UNIDADES GOOGLE DRIVE DETECTADAS", opciones_origen)
    if idx_origen is None: return
    unidad_origen = unidades[idx_origen]
    console.clear()

    opciones_destino = [
        {"titulo": "PC / Disco externo", "detalle": "Seleccionar una carpeta local en tu equipo"},
        {"titulo": "Google Drive", "detalle": "Copiar directamente a una unidad en la nube"}
    ]

    idx_tipo_destino = menu_radio(console, "DESTINO DE LA COPIA", opciones_destino)
    if idx_tipo_destino is None: return
    console.clear()

    if idx_tipo_destino == 0:
        ruta_destino = seleccionar_carpeta_local(console)
        if not ruta_destino: return
    else:
        idx_dest_drive = menu_radio(console, "CUENTA DE GOOGLE DRIVE DESTINO", opciones_origen)
        if idx_dest_drive is None: return
        ruta_destino = unidades[idx_dest_drive].ruta_unidad
    console.clear()

    opciones_escaneo = [
        {"titulo": "Escanear shortcuts o accesos directos",
         "detalle": "Detecta enlaces .lnk y carpetas compartidas ancladas a tu Drive"},
        {"titulo": "Escanear carpetas", "detalle": "Detecta únicamente carpetas normales dentro de tu unidad"}
    ]
    idx_escaneo = menu_radio(console, "MÉTODO DE ESCANEO", opciones_escaneo)
    if idx_escaneo is None: return
    console.clear()

    plan = preparar_seleccion(
        console=console,
        drive_raiz=unidad_origen.ruta_unidad,
        destino=ruta_destino,
        modo_escaneo=idx_escaneo
    )

    if not plan: return

    confirmacion = Prompt.ask("\n[bold green]¿Deseas iniciar la sincronización?[/bold green] [S/N]",
                              choices=["S", "s", "N", "n"], default="S")
    if confirmacion.upper() != "S": return
    console.clear()

    tui = ReelsTUI(unidad_origen.ruta_unidad, ruta_destino)
    tui.start()

    try:
        ejecutar_sincronizacion(plan, tui)
    except KeyboardInterrupt:
        tui.set_status("CANCELLED", "Interrumpido por el usuario (Progreso guardado)")
        tui.refresh()
    finally:
        tui.stop()

    mostrar_final(tui)


def mostrar_menu_principal():
    while True:
        console.clear()
        console.print(
            Panel(
                f"[bold cyan]{APP_TITLE} {APP_VERSION}[/bold cyan] - [dim]{APP_SUBTITLE}[/dim]\n"
                f"[dim]Desarrollado por {DEVELOPER} | VERSIÓN LIBRE[/dim]",
                border_style="cyan",
                box=box.DOUBLE,
            )
        )
        console.print("  [bold cyan]1.[/bold cyan] Iniciar Clonación / Sincronización")
        console.print("  [bold red]2.[/bold red] Salir")

        try:
            opc = Prompt.ask("\nSelecciona una opción", choices=["1", "2"], default="1")
        except (KeyboardInterrupt, EOFError):
            break

        if opc == "1":
            flujo_principal()
        elif opc == "2":
            break


def main():
    try:
        init_database()
        mostrar_menu_principal()
    except KeyboardInterrupt:
        console.print("\n\n[dim]Programa finalizado.[/dim]\n")
        sys.exit(0)


if __name__ == "__main__":
    main()