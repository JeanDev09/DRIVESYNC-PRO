def format_bytes(value):
    value = float(value)
    units = ["B", "KB", "MB", "GB", "TB"]
    for unit in units:
        if value < 1024:
            return f"{value:.2f} {unit}"
        value /= 1024
    return f"{value:.2f} PB"


def format_speed(bytes_per_second):
    return f"{format_bytes(bytes_per_second)}/s"


def format_time(seconds):
    if seconds is None or seconds < 0:
        return "--:--:--"
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds %= 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def shorten_text(text, max_length=55):
    text = str(text)
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def shorten_path(path, max_length=58):
    path = str(path)
    if len(path) <= max_length:
        return path
    return "..." + path[-(max_length - 3) :]