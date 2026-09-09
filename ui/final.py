import sys
import time
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from config import FOROBETA_URL, WHATSAPP_NUMERO
from utils.formatting import format_bytes, format_time


def mostrar_final(tui):
    console = Console()
    console.clear()

    # Calculamos el tiempo total de ejecución
    elapsed = time.monotonic() - tui.start_time

    # Creamos la tabla de resumen
    tabla = Table(box=box.ROUNDED, border_style="cyan", expand=True)
    tabla.add_column("Métrica", style="bold white")
    tabla.add_column("Resultado", justify="right", style="cyan")

    # Determinar el color del estado
    color_estado = "green"
    if tui.status in ["CANCELLED", "ERROR"]:
        color_estado = "red"

    tabla.add_row("Estado Final de Sincronización", f"[bold {color_estado}]{tui.status}[/bold {color_estado}]")
    tabla.add_row("Tiempo Transcurrido", format_time(elapsed))
    tabla.add_row("Total de Datos Transferidos", format_bytes(tui.bytes_copied))
    tabla.add_row("Archivos Completados", f"{tui.global_copied}")
    tabla.add_row("Archivos Omitidos (Ya existían)", str(tui.global_skipped))

    if tui.global_errors > 0:
        tabla.add_row("Errores Encontrados", f"[bold red]{tui.global_errors}[/bold red]")

    if tui.status == "CANCELLED":
        tabla.add_row("Aviso del Sistema",
                      "[yellow]El progreso parcial se guardó. Al reiniciar, continuará donde se quedó.[/yellow]")

    # Footer con información de contacto dinámica
    mensaje_despedida = (
        f"[dim]Gracias por usar DriveSync Pro.[/dim]\n"
        f"ForoBeta: [cyan]{FOROBETA_URL}[/cyan] | WhatsApp: [green]+{WHATSAPP_NUMERO}[/green]"
    )

    panel_principal = Panel(
        tabla,
        title="[bold cyan] RESUMEN DE LA OPERACIÓN [/bold cyan]",
        subtitle=mensaje_despedida,
        border_style="cyan"
    )

    console.print(panel_principal)
    print("\n")
    sys.exit(0)