from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import OCRError


class PaddleOCRBackend:
    name = "paddle"

    def __init__(self, language: str = "ja", options: dict[str, Any] | None = None):
        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:
            raise OCRError(
                "PaddleOCR backend가 설치되어 있지 않습니다.\n"
                "uv pip install -e '.[paddle]'"
            ) from exc

        self.language = _paddle_language(language)
        self.options = options or {}
        try:
            # PaddleOCR 3.x pipeline API. Text-line orientation helps with
            # rotated/vertical Japanese scans without requiring preprocessing.
            self._ocr = PaddleOCR(
                lang=self.language,
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=True,
            )
        except Exception as exc:
            raise OCRError(f"PaddleOCR 초기화에 실패했습니다: {exc}") from exc

    def recognize(self, image: Path) -> str:
        try:
            results = self._ocr.predict(input=str(image))
            return _result_text(results)
        except Exception as exc:
            raise OCRError(f"PaddleOCR 실패: {image.name}\n{exc}") from exc


def _paddle_language(language: str) -> str:
    first = language.split("+")[0].strip().lower()
    return {
        "ja": "japan",
        "jpn": "japan",
        "jpn_vert": "japan",
    }.get(first, first or "japan")


def _result_text(results: Any) -> str:
    """Extract PaddleOCR 3.x prediction text while tolerating result wrappers."""
    chunks: list[str] = []
    for result in results or []:
        data = getattr(result, "json", result)
        if callable(data):
            data = data()
        if isinstance(data, str):
            import json

            data = json.loads(data)
        if not isinstance(data, dict):
            continue
        data = data.get("res", data)
        texts = data.get("rec_texts", data.get("texts", []))
        if isinstance(texts, str):
            texts = [texts]
        chunks.extend(str(text).strip() for text in texts if str(text).strip())
    return "\n".join(chunks).strip()

