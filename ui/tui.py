import time
from datetime import datetime
from collections import deque
from rich import box
from rich.console import Console, Group
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from rich.progress_bar import ProgressBar

from utils.formatting import format_bytes, format_time
from config import APP_TITLE, DEVELOPER, APP_VERSION, APP_SUBTITLE


class ReelsTUI:
    def __init__(self, origen: str, destino: str):
        self.console = Console()
        self.origen = origen
        self.destino = destino

        self.status = "IDLE"
        self.status_message = "Esperando..."
        self.logs = deque(maxlen=8)

        self.global_total = 0
        self.global_processed = 0
        self.global_copied = 0
        self.global_skipped = 0
        self.global_errors = 0

        self.batch_total = 0
        self.batch_processed = 0
        self.batch_copied = 0
        self.batch_skipped = 0
        self.batch_errors = 0
        self.batch_index = 0

        self.bytes_total = 0
        self.bytes_copied = 0
        self.current_file_size = 0
        self.current_file_copied = 0

        self.current_batch = "--"
        self.current_file = "--"
        self.current_source = "--"
        self.current_destination = "--"

        self.start_time = time.monotonic()
        self.last_update_time = self.start_time
        self.last_bytes = 0
        self.current_speed = 0

        self.live = None

    def start(self):
        self.start_time = time.monotonic()
        self.live = Live(self._generate_layout(), console=self.console, refresh_per_second=10)
        self.live.start()

    def stop(self):
        if self.live:
            self.live.update(self._generate_layout())
            self.live.stop()

    def refresh(self):
        if self.live:
            now = time.monotonic()
            if now - self.last_update_time >= 1.0:
                elapsed = now - self.last_update_time
                bytes_diff = self.bytes_copied - self.last_bytes
                self.current_speed = bytes_diff / elapsed
                self.last_update_time = now
                self.last_bytes = self.bytes_copied

            self.live.update(self._generate_layout())

    def log(self, message: str, level: str = "INFO"):
        colors = {"INFO": "cyan", "WARN": "yellow", "ERROR": "red", "OK": "green"}
        color = colors.get(level, "white")
        timestamp = datetime.now().strftime("%H:%M:%S")
        icon = {"INFO": "ℹ", "WARN": "⚠", "ERROR": "✖", "OK": "✔"}.get(level, "•")
        self.logs.append(f"[dim]{timestamp}[/dim] [{color}]{icon} {level:<5}[/{color}] {message}")

    def set_status(self, status: str, message: str):
        self.status = status
        self.status_message = message

    def _truncate(self, text: str, length: int = 50) -> str:
        if len(text) > length:
            return "..." + text[-(length - 3):]
        return text

    def _generate_layout(self) -> Layout:
        layout = Layout()

        # 1. Estructura principal
        layout.split_column(
            Layout(name="header", size=5),
            Layout(name="main"),
            Layout(name="logs", size=10)
        )

        # 2. División en dos columnas
        layout["main"].split_row(
            Layout(name="left", ratio=1),
            Layout(name="right", ratio=1)
        )

        # 3. Cuadrantes Clásicos (4 Paneles)
        layout["left"].split_column(
            Layout(name="transfer", ratio=1),
            Layout(name="stats", ratio=1)
        )
        layout["right"].split_column(
            Layout(name="routes", ratio=1),
            Layout(name="activity", ratio=1)
        )

        # ================= HEADER =================
        header_text = Text(justify="center")
        header_text.append(f"{APP_TITLE} v{APP_VERSION}\n", style="bold cyan")
        header_text.append(f"{APP_SUBTITLE}\n", style="bold white")
        header_text.append(f"DEVELOPER {DEVELOPER}", style="dim")
        layout["header"].update(Panel(header_text, border_style="cyan", box=box.ROUNDED))

        # ================= CUADRANTE 1: TRANSFERENCIA =================
        t_trans = Table.grid(padding=(0, 2), expand=True)
        t_trans.add_column("Key", style="bold cyan", width=12)
        t_trans.add_column("Value")

        status_color = {"IDLE": "dim", "SCANNING": "yellow", "COPYING": "green", "FINISHED": "bold green",
                        "ERROR": "bold red", "CANCELLED": "bold red"}.get(self.status, "white")
        t_trans.add_row("ESTADO", f"[{status_color}]{self.status}[/{status_color}]")
        t_trans.add_row("MENSAJE", self.status_message)
        t_trans.add_row("VELOCIDAD", f"{format_bytes(self.current_speed)}/s")

        elapsed = time.monotonic() - self.start_time
        t_trans.add_row("TIEMPO", format_time(elapsed))

        if self.current_file_size > 0:
            pct = (self.current_file_copied / self.current_file_size) * 100
            peso_texto = f"{format_bytes(self.current_file_copied)} / {format_bytes(self.current_file_size)} [bold green]({pct:.1f}%)[/bold green]"
        else:
            peso_texto = "--"
        t_trans.add_row("PROGRESO", peso_texto)

        layout["transfer"].update(Panel(t_trans, title="[bold cyan] TRANSFERENCIA [/bold cyan]", border_style="cyan"))

        # ================= CUADRANTE 2: RUTAS =================
        t_rutas = Table.grid(padding=(0, 2), expand=True)
        t_rutas.add_column("Key", style="bold cyan", width=10)
        t_rutas.add_column("Value")
        t_rutas.add_row("ARCHIVO", self._truncate(self.current_file, 55))
        t_rutas.add_row("ORIGEN", self._truncate(self.current_source, 55))
        t_rutas.add_row("DESTINO", self._truncate(self.current_destination, 55))

        layout["routes"].update(Panel(t_rutas, title="[bold cyan] RUTAS [/bold cyan]", border_style="cyan"))

        # ================= CUADRANTE 3: ESTADÍSTICAS =================
        t_stats = Table.grid(padding=(0, 2), expand=True)
        t_stats.add_column("Key", style="bold cyan", width=14)
        t_stats.add_column("Value", justify="right")

        t_stats.add_row("ARCHIVOS", str(self.global_total))
        t_stats.add_row("PROCESADOS", str(self.global_processed))
        t_stats.add_row("COPIADOS", str(self.global_copied))
        t_stats.add_row("OMITIDOS", str(self.global_skipped))
        t_stats.add_row("ERRORES", f"[red]{self.global_errors}[/red]" if self.global_errors > 0 else "0")

        layout["stats"].update(Panel(t_stats, title="[bold cyan] ESTADÍSTICAS [/bold cyan]", border_style="cyan"))

        # ================= CUADRANTE 4: ACTIVIDAD & PROGRESO =================
        t_act = Table.grid(padding=(0, 2), expand=True)
        t_act.add_column("Key", style="bold cyan", width=12)
        t_act.add_column("Value")
        t_act.add_row("LOTE ACTUAL", self._truncate(self.current_batch, 50))
        t_act.add_row("PROCESADO", f"{self.batch_processed} / {self.batch_total}")

        global_pct = (self.bytes_copied / self.bytes_total * 100) if self.bytes_total > 0 else 0
        eta = "--:--:--"
        if self.current_speed > 0 and self.bytes_total > 0:
            remaining_bytes = self.bytes_total - self.bytes_copied
            eta = format_time(remaining_bytes / self.current_speed)

        prog_bar = ProgressBar(total=100, completed=global_pct, width=None)

        details = Text.assemble(
            ("Completado ", "dim"), (f"{global_pct:.1f}%", "bold green"),
            (" " * 20),
            ("ETA ", "dim"), (eta, "bold yellow")
        )

        # Agrupamos los elementos para que se rendericen en el mismo panel
        content = Group(t_act, Text(""), prog_bar, details)
        layout["activity"].update(Panel(content, title="[bold cyan] PROGRESO GLOBAL [/bold cyan]", border_style="cyan"))

        # ================= EVENTOS =================
        log_text = "\n".join(self.logs)
        layout["logs"].update(Panel(log_text, title="[bold cyan] EVENTOS [/bold cyan]", border_style="cyan"))

        return layout