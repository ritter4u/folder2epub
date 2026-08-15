from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .base import OCRError, OCRBackend
from .manga import MangaOCRBackend
from .mlx import MLXOCRBackend
from .paddle import PaddleOCRBackend
from .tesseract import TesseractOCRBackend

SUPPORTED_ENGINES = ("mlx", "paddle", "manga", "tesseract")
_BACKEND_CACHE: dict[tuple[str, str, str], OCRBackend] = {}


def create_ocr_backend(
    engine: str = "paddle",
    language: str = "ja",
    options: dict[str, Any] | None = None,
) -> OCRBackend:
    normalized = engine.strip().lower()
    cache_options = json.dumps(options or {}, ensure_ascii=False, sort_keys=True)
    cache_key_value = (normalized, language, cache_options)
    cached = _BACKEND_CACHE.get(cache_key_value)
    if cached is not None:
        return cached

    if normalized == "mlx":
        backend = MLXOCRBackend(language, options)
    elif normalized == "paddle":
        backend = PaddleOCRBackend(language, options)
    elif normalized == "manga":
        backend = MangaOCRBackend(language, options)
    elif normalized == "tesseract":
        backend = TesseractOCRBackend(language, options)
    else:
        supported = ", ".join(SUPPORTED_ENGINES)
        raise OCRError(f"지원하지 않는 OCR engine입니다: {engine}. 사용 가능: {supported}")

    _BACKEND_CACHE[cache_key_value] = backend
    return backend


def cache_key(
    image: Path,
    engine: str,
    language: str,
    options: dict[str, Any] | None = None,
) -> str:
    stat = image.stat()
    payload = {
        "image": {"path": str(image.resolve()), "size": stat.st_size, "mtime_ns": stat.st_mtime_ns},
        "engine": engine,
        "language": language,
        "options": options or {},
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha1(encoded).hexdigest()[:12]


def ocr_image(
    image: Path,
    cache_dir: Path,
    lang: str = "ja",
    psm: int = 3,
    force: bool = False,
    engine: str = "paddle",
    options: dict[str, Any] | None = None,
    backend: OCRBackend | None = None,
) -> str:
    effective_options = {"psm": psm, **(options or {})}
    key = cache_key(image, engine, lang, effective_options)
    safe_lang = re.sub(r"[^A-Za-z0-9_-]+", "-", lang)
    cache_file = cache_dir / f"{image.stem}.{engine}-{safe_lang}-{key}.txt"
    if cache_file.exists() and not force:
        return cache_file.read_text(encoding="utf-8")

    backend = backend or create_ocr_backend(engine, lang, effective_options)
    cache_dir.mkdir(parents=True, exist_ok=True)
    text = backend.recognize(image)
    cache_file.write_text(text, encoding="utf-8")
    return text


__all__ = [
    "OCRError",
    "OCRBackend",
    "SUPPORTED_ENGINES",
    "cache_key",
    "create_ocr_backend",
    "ocr_image",
]
