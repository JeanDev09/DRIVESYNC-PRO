"""Live synchronization dashboard, deliberately separate from copy logic."""
import time
from collections import deque
from datetime import datetime

from rich import box
from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress_bar import ProgressBar
from rich.table import Table
from rich.text import Text

from config import MAX_LOGS
from ui.theme import clear_view, footer, screen_header, status_label, truncate_middle
from utils.formatting import format_bytes, format_speed, format_time


class ReelsTUI:
    """Presentation state consumed by the existing synchronization engine."""

    def __init__(self, origen: str, destino: str):
        self.console = Console()
        self.origen, self.destino = origen, destino
        self.status, self.status_message = "IDLE", "Listo para iniciar."
        self.logs = deque(maxlen=MAX_LOGS)
        self.global_total = self.global_processed = self.global_copied = 0
        self.global_skipped = self.global_errors = 0
        self.batch_total = self.batch_processed = self.batch_copied = 0
        self.batch_skipped = self.batch_errors = self.batch_index = 0
        self.bytes_total = self.bytes_copied = 0
        self.current_file_size = self.current_file_copied = 0
        self.current_batch = self.current_file = "--"
        self.current_source = self.current_destination = "--"
        self.start_time = time.monotonic()
        self.current_speed = 0.0
        self._samples = deque(maxlen=8)
        self._last_render = 0.0
        self.live = None

    def start(self):
        self.start_time = time.monotonic()
        self._samples.clear()
        self._samples.append((self.start_time, self.bytes_copied))
        clear_view(self.console)
        self.live = Live(self._generate_layout(), console=self.console,
                         refresh_per_second=10, transient=False)
        self.live.start()

    def stop(self):
        if self.live:
            self.live.update(self._generate_layout(), refresh=True)
            self.live.stop()
            self.live = None

    def refresh(self):
        """Throttle rendering and calculate speed over a stable sample window."""
        if not self.live:
            return
        now = time.monotonic()
        if now - self._last_render < 0.08:
            return
        self._last_render = now
        self._samples.append((now, self.bytes_copied))
        if len(self._samples) >= 2:
            started, start_bytes = self._samples[0]
            elapsed = now - started
            copied = self.bytes_copied - start_bytes
            self.current_speed = copied / elapsed if elapsed >= 0.35 and copied >= 0 else 0.0
        self.live.update(self._generate_layout(), refresh=True)

    def log(self, message: str, level: str = "INFO"):
        level = level.upper()
        if level not in {"INFO", "OK", "WARN", "ERROR"}:
            level = "INFO"
        self.logs.append((datetime.now().strftime("%H:%M:%S"), level, str(message)))

    def set_status(self, status: str, message: str):
        self.status, self.status_message = status, message

    @staticmethod
    def _percent(current: int, total: int) -> float:
        return min(100.0, (current / total * 100)) if total else 0.0

    def _eta(self) -> str:
        if self.current_speed <= 0 or self.bytes_total <= self.bytes_copied:
            return "Calculando..." if self.bytes_total > self.bytes_copied else "--:--:--"
        # A minimum copied amount avoids an unstable ETA at transfer startup.
        if len(self._samples) < 3 or self.bytes_copied <= 0:
            return "Calculando..."
        return format_time((self.bytes_total - self.bytes_copied) / self.current_speed)

    def _metric(self, label: str, value: str, style: str = "white") -> Text:
        text = Text()
        text.append(f"{label}\n", style="dim")
        text.append(value, style=style)
        return text

    def _generate_layout(self) -> Layout:
        layout = Layout()
        layout.split_column(Layout(name="header", size=3), Layout(name="body"),
                            Layout(name="footer", size=1))
        layout["body"].split_column(Layout(name="overview", size=9),
                                     Layout(name="stats", size=5), Layout(name="logs", ratio=1))

        layout["header"].update(
            Panel(screen_header(self.status, self.status_message),
                  border_style="bright_black", box=box.HORIZONTALS, padding=(0, 1))
        )
        layout["overview"].update(self._overview())
        layout["stats"].update(self._stats())
        layout["logs"].update(self._logs())
        layout["footer"].update(footer(("Ctrl+C", "cancelar de forma segura")))
        return layout

    def _overview(self) -> Panel:
        width = max(24, self.console.width - 10)
        route_length = max(18, width // 2)
        global_percent = self._percent(self.bytes_copied, self.bytes_total)
        file_percent = self._percent(self.current_file_copied, self.current_file_size)
        label, colour = status_label(self.status)
        grid = Table.grid(expand=True, padding=(0, 1))
        grid.add_column(ratio=1)
        grid.add_column(ratio=1)
        origin = truncate_middle(self.origen, route_length)
        destination = truncate_middle(self.destino, route_length)
        grid.add_row(Text.assemble(("ORIGEN\n", "dim cyan"), (origin, "white")),
                     Text.assemble(("DESTINO\n", "dim cyan"), (destination, "white")))
        grid.add_row(Text.assemble(("ARCHIVO ACTUAL  ", "dim cyan"),
                                   (truncate_middle(self.current_file, width), "bold white")), "")
        grid.add_row(Text.assemble(("Origen: ", "dim"),
                                   (truncate_middle(self.current_source, width), "dim")), "")
        grid.add_row(Text.assemble(("Destino: ", "dim"),
                                   (truncate_middle(self.current_destination, width), "dim")), "")

        progress = ProgressBar(total=100, completed=global_percent, width=None,
                               complete_style="cyan", finished_style="green",
                               pulse_style="bright_cyan")
        details = Table.grid(expand=True)
        details.add_column(ratio=1)
        details.add_column(justify="right")
        details.add_row(
            Text.assemble((f"{global_percent:.1f}% ", f"bold {colour}"),
                          (f"· {self.global_processed:,}/{self.global_total:,} archivos", "dim")),
            Text.assemble((format_bytes(self.bytes_copied), "white"),
                          (f" / {format_bytes(self.bytes_total)}", "dim")),
        )
        file_line = Text.assemble(
            ("Archivo: ", "dim"),
            (f"{format_bytes(self.current_file_copied)} / {format_bytes(self.current_file_size)}", "white"),
            (f"  ({file_percent:.1f}%)", "dim") if self.current_file_size else ("", ""),
        )
        performance = Text.assemble(
            ("⚡ ", "cyan"), (format_speed(self.current_speed) if self.current_speed else "Calculando...", "white"),
            ("     ⏱ ", "dim"), (format_time(time.monotonic() - self.start_time), "white"),
            ("     ETA ", "dim"), (self._eta(), "yellow"),
        )
        return Panel(Group(grid, Text(""), Text("SINCRONIZACIÓN", style="dim cyan"), progress,
                           details, file_line, performance), box=box.HORIZONTALS,
                     border_style="bright_black", padding=(0, 1))

    def _stats(self) -> Panel:
        stats = Table.grid(expand=True, padding=(0, 2))
        for _ in range(5):
            stats.add_column(ratio=1)
        values = [("TOTAL", self.global_total, "white"), ("PROCESADOS", self.global_processed, "cyan"),
                  ("COPIADOS", self.global_copied, "green"), ("OMITIDOS", self.global_skipped, "white"),
                  ("ERRORES", self.global_errors, "red" if self.global_errors else "dim")]
        stats.add_row(*[self._metric(label, f"{value:,}", style) for label, value, style in values])
        return Panel(stats, title=" ARCHIVOS ", title_align="left", box=box.HORIZONTALS,
                     border_style="bright_black", padding=(0, 1))

    def _logs(self) -> Panel:
        icon_style = {"INFO": ("ℹ", "cyan"), "OK": ("✓", "green"),
                      "WARN": ("⚠", "yellow"), "ERROR": ("✖", "red")}
        lines = []
        available = max(18, self.console.width - 16)
        for timestamp, level, message in list(self.logs)[-MAX_LOGS:]:
            icon, colour = icon_style[level]
            line = Text()
            line.append(f"{timestamp}  ", style="dim")
            line.append(f"{icon} ", style=colour)
            line.append(f"{level:<5} ", style=colour)
            line.append(truncate_middle(message, available), style="white")
            lines.append(line)
        content = Group(*lines) if lines else Text("Aún no hay actividad.", style="dim")
        return Panel(content, title=" ACTIVIDAD ", title_align="left", box=box.HORIZONTALS,
                     border_style="bright_black", padding=(0, 1))
