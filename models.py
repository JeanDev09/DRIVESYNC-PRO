import re
from dataclasses import dataclass
from pathlib import Path

@dataclass
class DriveUnit:
    letra: str
    ruta_unidad: Path
    etiqueta: str
    libre_bytes: int
    total_bytes: int

    @property
    def libre_gb(self):
        return self.libre_bytes / (1024 ** 3)

    @property
    def total_gb(self):
        return self.total_bytes / (1024 ** 3)

    @property
    def nombre_limpio(self) -> str:
        """Remueve el sufijo truncado '- Goo...' que impone el límite de Windows."""
        limpio = re.sub(r"\s*-\s*Goo.*$", "", self.etiqueta).strip()
        letra_disco = str(self.letra).replace("/", "").replace("\\", "")
        return f"[{letra_disco}] {limpio if limpio else self.etiqueta}"