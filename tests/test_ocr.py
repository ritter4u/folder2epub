from pathlib import Path

import pytest

from folder2epub.ocr import OCRError, cache_key, create_ocr_backend, ocr_image


def test_ocr_backend_factory_rejects_unknown_engine():
    with pytest.raises(OCRError, match="지원하지 않는 OCR engine"):
        create_ocr_backend("unknown", "ja")


def test_optional_paddle_package_has_actionable_error(monkeypatch):
    monkeypatch.setitem(__import__("sys").modules, "paddleocr", None)
    with pytest.raises(OCRError, match=r"uv pip install -e '\.\[paddle\]'"):
        create_ocr_backend("paddle", "ja")


def test_cache_key_changes_with_engine_and_options(tmp_path: Path):
    image = tmp_path / "001.jpg"
    image.write_bytes(b"image")

    paddle_key = cache_key(image, "paddle", "ja", {"psm": 3})
    manga_key = cache_key(image, "manga", "ja", {"psm": 3})
    changed_key = cache_key(image, "paddle", "ja", {"psm": 6})

    assert len({paddle_key, manga_key, changed_key}) == 3


def test_mock_backend_uses_separate_cache_file(tmp_path: Path, monkeypatch):
    image = tmp_path / "001.jpg"
    image.write_bytes(b"image")

    class MockBackend:
        name = "mock"

        def recognize(self, path: Path) -> str:
            return f"recognized: {path.name}"

    monkeypatch.setattr(
        "folder2epub.ocr.create_ocr_backend",
        lambda engine, language, options: MockBackend(),
    )
    cache_dir = tmp_path / ".folder2epub-cache"
    assert ocr_image(image, cache_dir, engine="mock") == "recognized: 001.jpg"
    assert ocr_image(image, cache_dir, engine="mock") == "recognized: 001.jpg"
    files = list(cache_dir.glob("001.mock-ja-*.txt"))
    assert len(files) == 1
