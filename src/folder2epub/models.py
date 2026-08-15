from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class Page:
    index: int
    image_path: Path
    text: str = ""
