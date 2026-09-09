"""Shared visual primitives for the terminal interface.

Keeping the small style vocabulary here prevents individual screens from
drifting into different colours, borders and keyboard help text.
"""
from rich.console import Console, Group
from rich.text import Text

from config import APP_TITLE, APP_VERSION, DEVELOPER, FOROBETA_URL, WHATSAPP_NUMERO


STATUS_META = {
    "IDLE": ("LISTO", "cyan"),
    "SCANNING": ("ESCANEANDO", "yellow"),
    "COPYING": ("SINCRONIZANDO", "cyan"),
    "FINISHED": ("COMPLETADO", "green"),
    "COMPLETED": ("COMPLETADO", "green"),
    "CANCELLED": ("CANCELADO", "yellow"),
    "ERROR": ("ERROR", "red"),
}


def status_label(status: str) -> tuple[str, str]:
    """Return the user-facing, semantic label for an internal sync status."""
    return STATUS_META.get(status, (status.replace("_", " "), "white"))


def screen_header(status: str = "IDLE", subtitle: str | None = None) -> Group:
    """Build a compact header without introducing a nested panel."""
    label, colour = status_label(status)
    title = Text()
    title.append(APP_TITLE, style="bold white")
    title.append("  ·  ", style="dim")
    title.append(APP_VERSION if APP_VERSION.startswith("v") else f"v{APP_VERSION}", style="cyan")
    title.append(" " * 3)
    title.append("● ", style=colour)
    title.append(label, style=f"bold {colour}")
    body = Text()
    if subtitle:
        body.append(subtitle, style="dim")
    return Group(title, body) if subtitle else Group(title)


def footer(*controls: tuple[str, str]) -> Text:
    """Render compact and uniform keyboard hints."""
    line = Text(justify="center")
    for index, (key, action) in enumerate(controls):
        if index:
            line.append("   ", style="dim")
        line.append(key, style="bold cyan")
        line.append(f" {action}", style="dim")
    return line


def contact_line() -> Text:
    """Return compact clickable developer and support links for Rich terminals."""
    text = Text(justify="center")
    text.append("Desarrollado por ", style="dim")
    text.append(DEVELOPER, style="white")
    text.append("  ·  ", style="dim")
    text.append("ForoBeta", style=f"cyan link {FOROBETA_URL}")
    text.append("  ·  ", style="dim")
    text.append("WhatsApp", style=f"green link https://wa.me/{WHATSAPP_NUMERO}")
    return text


def clear_view(console: Console) -> None:
    """Clear both the visible terminal and supported terminal scrollback."""
    if console.is_terminal:
        # CSI 3 J clears scrollback in Windows Terminal and modern ANSI terminals.
        console.file.write("\x1b[3J")
        console.file.flush()
    console.clear()


def truncate_middle(value: object, max_length: int) -> str:
    """Keep both ends of a long name/path visible without breaking layouts."""
    text = str(value)
    if max_length <= 3 or len(text) <= max_length:
        return text[:max_length]
    head = max(1, (max_length - 3) // 2)
    return f"{text[:head]}...{text[-(max_length - 3 - head):]}"
