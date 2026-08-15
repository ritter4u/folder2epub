from pathlib import Path
from zipfile import ZipFile

from folder2epub.epub_builder import build_epub
from folder2epub.models import Page


def test_build_image_epub_without_ocr(tmp_path: Path):
    image = tmp_path / "001.jpg"
    image.write_bytes(b"not-a-real-jpeg")
    output = tmp_path / "book.epub"

    build_epub(
        pages=[Page(index=1, image_path=image)],
        output=output,
        title="Book",
        author="Author",
        mode="image",
    )

    with ZipFile(output) as archive:
        chapter = archive.read("EPUB/text/page-00001.xhtml").decode("utf-8")
        assert "page-00001.jpg" in chapter
        assert ">recognized" not in chapter


def test_build_hybrid_epub_contains_searchable_ocr(tmp_path: Path):
    image = tmp_path / "001.jpg"
    image.write_bytes(b"not-a-real-jpeg")
    output = tmp_path / "book.epub"

    build_epub(
        pages=[Page(index=1, image_path=image, text="日本語の本文")],
        output=output,
        title="Book",
        author="Author",
        mode="hybrid",
        language="ja",
    )

    with ZipFile(output) as archive:
        chapter = archive.read("EPUB/text/page-00001.xhtml").decode("utf-8")
        assert "ocr-hidden" in chapter
        assert "日本語の本文" in chapter
