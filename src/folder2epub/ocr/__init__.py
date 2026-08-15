from __future__ import annotations

import hashlib
import json
import platform
import re
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .base import OCRError, OCRBackend
from .manga import MangaOCRBackend
from .mlx import MLXOCRBackend
from .paddle import PaddleOCRBackend
from .tesseract import TesseractOCRBackend

SUPPORTED_ENGINES = ("auto", "mlx", "paddle", "manga", "tesseract")
_BACKEND_CACHE: dict[tuple[str, str, Any], OCRBackend] = {}


def create_ocr_backend(
    engine: str = "paddle",
    language: str = "ja",
    options: dict[str, Any] | None = None,
) -> OCRBackend:
    normalized = resolve_ocr_engine(engine)
    cache_key_value = (normalized, language, _normalize_option(options or {}))
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


def resolve_ocr_engine(engine: str) -> str:
    """Resolve the platform-aware default without probing optional packages."""
    normalized = engine.strip().lower()
    if normalized != "auto":
        return normalized
    if sys.platform == "darwin" and platform.machine().lower() in {"arm64", "aarch64"}:
        return "mlx"
    return "paddle"


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
        "options": _normalize_option(options or {}),
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha1(encoded).hexdigest()[:12]


def _normalize_option(value: Any) -> Any:
    """Convert backend options into deterministic, hashable/JSON-safe values."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Path):
        return ("path", str(value))
    if isinstance(value, Mapping):
        return tuple(
            sorted(
                (str(key), _normalize_option(item))
                for key, item in value.items()
            )
        )
    if isinstance(value, (list, tuple)):
        return tuple(_normalize_option(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return tuple(sorted((_normalize_option(item) for item in value), key=repr))
    return ("object", type(value).__qualname__, repr(value))


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
    cache_file = _cache_file(image, cache_dir, engine, lang, effective_options)
    if cache_file.exists() and not force:
        return cache_file.read_text(encoding="utf-8")

    backend = backend or create_ocr_backend(engine, lang, effective_options)
    cache_dir.mkdir(parents=True, exist_ok=True)
    text = backend.recognize(image)
    cache_file.write_text(text, encoding="utf-8")
    return text


def ocr_images(
    images: list[Path],
    cache_dir: Path,
    lang: str = "ja",
    psm: int = 3,
    force: bool = False,
    engine: str = "paddle",
    options: dict[str, Any] | None = None,
    backend: OCRBackend | None = None,
) -> dict[Path, str]:
    """OCR a book's pages, using a backend batch API when available."""
    effective_options = {"psm": psm, **(options or {})}
    results: dict[Path, str] = {}
    pending: list[Path] = []
    for image in images:
        cache_file = _cache_file(image, cache_dir, engine, lang, effective_options)
        if cache_file.exists() and not force:
            results[image] = cache_file.read_text(encoding="utf-8")
        else:
            pending.append(image)

    if not pending:
        return results

    selected_backend = backend or create_ocr_backend(engine, lang, effective_options)
    cache_dir.mkdir(parents=True, exist_ok=True)
    recognize_many = getattr(selected_backend, "recognize_many", None)
    if callable(recognize_many):
        recognized = recognize_many(pending)
        for image in pending:
            if image.resolve() not in recognized:
                raise OCRError(f"OCR 결과가 없습니다: {image.name}")
            text = recognized[image.resolve()]
            _cache_file(image, cache_dir, engine, lang, effective_options).write_text(
                text,
                encoding="utf-8",
            )
            results[image] = text
        return results

    for image in pending:
        results[image] = ocr_image(
            image=image,
            cache_dir=cache_dir,
            lang=lang,
            psm=psm,
            force=force,
            engine=engine,
            options=options,
            backend=selected_backend,
        )
    return results


def _cache_file(
    image: Path,
    cache_dir: Path,
    engine: str,
    language: str,
    options: dict[str, Any],
) -> Path:
    key = cache_key(image, engine, language, options)
    safe_lang = re.sub(r"[^A-Za-z0-9_-]+", "-", language)
    return cache_dir / f"{image.stem}.{engine}-{safe_lang}-{key}.txt"


__all__ = [
    "OCRError",
    "OCRBackend",
    "SUPPORTED_ENGINES",
    "cache_key",
    "create_ocr_backend",
    "ocr_image",
    "ocr_images",
    "resolve_ocr_engine",
]
