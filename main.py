import sys
from rich.console import Console
from rich.prompt import Prompt

from drive.detector import detectar_unidades_drive
from ui.interactive import menu_radio
from ui.destination import seleccionar_carpeta_local
from ui.setup import confirmar_inicio, preparar_seleccion
from ui.tui import ReelsTUI
from ui.final import mostrar_final
from ui.theme import clear_view
from sync.copier import ejecutar_sincronizacion
from storage.persistence import init_database

console = Console()


def flujo_principal():
    clear_view(console)
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
    clear_view(console)

    opciones_destino = [
        {"titulo": "PC / Disco externo", "detalle": "Seleccionar una carpeta local en tu equipo"},
        {"titulo": "Google Drive", "detalle": "Copiar directamente a una unidad en la nube"}
    ]

    idx_tipo_destino = menu_radio(console, "DESTINO DE LA COPIA", opciones_destino)
    if idx_tipo_destino is None: return
    clear_view(console)

    if idx_tipo_destino == 0:
        ruta_destino = seleccionar_carpeta_local(console)
        if not ruta_destino: return
    else:
        idx_dest_drive = menu_radio(console, "CUENTA DE GOOGLE DRIVE DESTINO", opciones_origen)
        if idx_dest_drive is None: return
        ruta_destino = unidades[idx_dest_drive].ruta_unidad
    clear_view(console)

    opciones_escaneo = [
        {"titulo": "Escanear shortcuts o accesos directos",
         "detalle": "Detecta enlaces .lnk y carpetas compartidas ancladas a tu Drive"},
        {"titulo": "Escanear carpetas", "detalle": "Detecta únicamente carpetas normales dentro de tu unidad"}
    ]
    idx_escaneo = menu_radio(console, "MÉTODO DE ESCANEO", opciones_escaneo)
    if idx_escaneo is None: return
    clear_view(console)

    plan = preparar_seleccion(
        console=console,
        drive_raiz=unidad_origen.ruta_unidad,
        destino=ruta_destino,
        modo_escaneo=idx_escaneo
    )

    if not plan: return

    if not confirmar_inicio(console):
        return
    clear_view(console)

    tui = ReelsTUI(unidad_origen.ruta_unidad, ruta_destino)
    tui.start()

    try:
        ejecutar_sincronizacion(plan, tui)
    except KeyboardInterrupt:
        tui.set_status("CANCELLED", "Interrumpido por el usuario (Progreso guardado)")
        tui.log("Sincronización cancelada por el usuario. El progreso parcial se conserva.", "WARN")
        tui.refresh()
    finally:
        tui.stop()

    mostrar_final(tui)


def mostrar_menu_principal():
    while True:
        clear_view(console)
        try:
            opc = menu_radio(console, "Inicio", [
                {"titulo": "Iniciar sincronización", "detalle": "Clona contenido de Google Drive a una ubicación elegida."},
                {"titulo": "Salir", "detalle": "Cerrar DriveSync Pro."},
            ], show_contact=True)
        except (KeyboardInterrupt, EOFError):
            break

        if opc == 0:
            flujo_principal()
        elif opc in (1, None):
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
