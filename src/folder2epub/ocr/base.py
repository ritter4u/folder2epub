from __future__ import annotations

from pathlib import Path
from typing import Protocol


class OCRError(RuntimeError):
    """Raised when an OCR backend cannot be used or fails."""


class OCRBackend(Protocol):
    name: str

    def recognize(self, image: Path) -> str:
        """Recognize text from one page image."""

