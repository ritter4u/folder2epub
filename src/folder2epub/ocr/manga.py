from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import OCRError


class MangaOCRBackend:
    name = "manga"

    def __init__(self, language: str = "ja", options: dict[str, Any] | None = None):
        if language.split("+")[0].strip().lower() not in {"ja", "jpn", "jpn_vert"}:
            raise OCRError("manga-ocr backend는 일본어(`--lang ja`)만 지원합니다.")
        try:
            from manga_ocr import MangaOcr
        except ImportError as exc:
            raise OCRError(
                "manga-ocr backend가 설치되어 있지 않습니다.\n"
                "uv pip install -e '.[manga]'"
            ) from exc
        try:
            self._ocr = MangaOcr()
        except Exception as exc:
            raise OCRError(f"manga-ocr 초기화에 실패했습니다: {exc}") from exc

    def recognize(self, image: Path) -> str:
        try:
            return str(self._ocr(str(image))).strip()
        except Exception as exc:
            raise OCRError(f"manga-ocr 실패: {image.name}\n{exc}") from exc
