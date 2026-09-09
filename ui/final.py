"""Result screen for a completed, cancelled, or partially failed operation."""
import time

from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from ui.theme import clear_view, contact_line, footer, screen_header
from utils.formatting import format_bytes, format_time


def mostrar_final(tui):
    """Show a truthful final outcome without terminating the host application."""
    console = Console()
    clear_view(console)
    elapsed = time.monotonic() - tui.start_time
    cancelled = tui.status == "CANCELLED"
    has_errors = tui.global_errors > 0 or tui.status == "ERROR"
    if cancelled:
        heading, colour = "⚠ Sincronización cancelada", "yellow"
        description = "El progreso parcial se conserva para que puedas reanudarlo."
    elif has_errors:
        heading, colour = "⚠ Sincronización terminada con errores", "yellow"
        description = "Los archivos restantes se procesaron; revisa la actividad para identificar los fallos."
    else:
        heading, colour = "✓ Sincronización completada", "green"
        description = "Todos los elementos planificados se procesaron correctamente."

    summary = Table.grid(expand=True, padding=(0, 2))
    for _ in range(3):
        summary.add_column(ratio=1)
    summary.add_row(
        Text.assemble(("TOTAL\n", "dim"), (f"{tui.global_total:,}", "white")),
        Text.assemble(("PROCESADOS\n", "dim"), (f"{tui.global_processed:,}", "cyan")),
        Text.assemble(("COPIADOS\n", "dim"), (f"{tui.global_copied:,}", "green")),
    )
    summary.add_row(
        Text.assemble(("OMITIDOS\n", "dim"), (f"{tui.global_skipped:,}", "white")),
        Text.assemble(("ERRORES\n", "dim"), (f"{tui.global_errors:,}", "red" if tui.global_errors else "dim")),
        Text.assemble(("TIEMPO TOTAL\n", "dim"), (format_time(elapsed), "white")),
    )
    details = Text.assemble(("Tamaño transferido: ", "dim"),
                            (format_bytes(tui.bytes_copied), "white"))
    content = Group(screen_header(tui.status, description), Text(heading, style=f"bold {colour}"),
                    Text(""), summary, details, Text(""), contact_line(),
                    footer(("Enter", "volver al inicio")))
    console.print(Panel(content, border_style="bright_black", box=box.HORIZONTALS, padding=(0, 1)))
    try:
        Prompt.ask("", default="")
    except (KeyboardInterrupt, EOFError):
        pass
