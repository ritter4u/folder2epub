from pathlib import Path

import pytest

from folder2epub.ocr import (
    OCRError,
    cache_key,
    create_ocr_backend,
    ocr_image,
    ocr_images,
    resolve_ocr_engine,
)


def test_ocr_backend_factory_rejects_unknown_engine():
    with pytest.raises(OCRError, match="지원하지 않는 OCR engine"):
        create_ocr_backend("unknown", "ja")


def test_auto_engine_resolves_by_platform(monkeypatch):
    monkeypatch.setattr("folder2epub.ocr.sys", "platform", "win32")
    assert resolve_ocr_engine("auto") == "paddle"

    monkeypatch.setattr("folder2epub.ocr.sys", "platform", "darwin")
    monkeypatch.setattr("folder2epub.ocr.platform.machine", lambda: "arm64")
    assert resolve_ocr_engine("auto") == "mlx"


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


def test_cache_key_accepts_non_json_options(tmp_path: Path):
    image = tmp_path / "001.jpg"
    image.write_bytes(b"image")

    class Options:
        pass

    key = cache_key(image, "mock", "ja", {"custom": Options(), "path": image})
    assert len(key) == 12


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


def test_mock_batch_backend_uses_one_call_and_page_caches(tmp_path: Path):
    images = [tmp_path / "001.jpg", tmp_path / "002.jpg"]
    for image in images:
        image.write_bytes(b"image")

    class MockBatchBackend:
        name = "mock"

        def __init__(self):
            self.calls = 0

        def recognize_many(self, paths: list[Path]) -> dict[Path, str]:
            self.calls += 1
            return {path.resolve(): f"recognized: {path.name}" for path in paths}

        def recognize(self, path: Path) -> str:
            raise AssertionError("batch backend should not use recognize()")

    backend = MockBatchBackend()
    cache_dir = tmp_path / ".folder2epub-cache"

    assert ocr_images(images, cache_dir, engine="mock", backend=backend) == {
        image: f"recognized: {image.name}" for image in images
    }
    assert backend.calls == 1
    assert ocr_images(images, cache_dir, engine="mock", backend=backend) == {
        image: f"recognized: {image.name}" for image in images
    }
    assert backend.calls == 1
    cache_files = list(cache_dir.glob("*.mock-ja-*.txt"))
    assert len(cache_files) == 2
    assert {path.read_text(encoding="utf-8") for path in cache_files} == {
        "recognized: 001.jpg",
        "recognized: 002.jpg",
    }


def test_mock_batch_backend_only_processes_uncached_pages(tmp_path: Path):
    images = [tmp_path / "001.jpg", tmp_path / "002.jpg"]
    for image in images:
        image.write_bytes(b"image")

    class MockBatchBackend:
        name = "mock"

        def __init__(self):
            self.calls = 0
            self.seen_paths: list[Path] = []

        def recognize_many(self, paths: list[Path]) -> dict[Path, str]:
            self.calls += 1
            self.seen_paths.extend(paths)
            return {path.resolve(): f"recognized: {path.name}" for path in paths}

    backend = MockBatchBackend()
    cache_dir = tmp_path / ".folder2epub-cache"
    ocr_images([images[0]], cache_dir, engine="mock", backend=backend)
    assert backend.calls == 1

    backend.seen_paths.clear()
    results = ocr_images(images, cache_dir, engine="mock", backend=backend)

    assert results == {image: f"recognized: {image.name}" for image in images}
    assert backend.calls == 2
    assert backend.seen_paths == [images[1]]

    backend.seen_paths.clear()
    ocr_images(images, cache_dir, engine="mock", backend=backend)
    assert backend.calls == 2
    assert backend.seen_paths == []


def test_ocr_images_raises_when_batch_backend_omits_page(tmp_path: Path):
    images = [tmp_path / "001.jpg", tmp_path / "002.jpg"]
    for image in images:
        image.write_bytes(b"image")

    class MockBatchBackend:
        name = "mock"

        def recognize_many(self, paths: list[Path]) -> dict[Path, str]:
            return {
                path.resolve(): f"recognized: {path.name}"
                for path in paths[:-1]
            }

    with pytest.raises(OCRError, match="002.jpg"):
        ocr_images(
            images,
            tmp_path / ".folder2epub-cache",
            engine="mock",
            backend=MockBatchBackend(),
        )
