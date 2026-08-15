from __future__ import annotations

import html
import mimetypes
import uuid
from pathlib import Path

from ebooklib import epub
from PIL import Image

from .models import Page


CSS = """
html, body {
    margin: 0;
    padding: 0;
}
.page {
    break-after: page;
    page-break-after: always;
}
.page-image {
    display: block;
    max-width: 100%;
    max-height: 98vh;
    width: auto;
    height: auto;
    margin: 0 auto;
}
.ocr {
    margin: 1.2rem;
    line-height: 1.75;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
}
.ocr-hidden {
    position: absolute;
    left: -99999px;
    width: 1px;
    height: 1px;
    overflow: hidden;
}
"""


def _media_type(path: Path) -> str:
    media, _ = mimetypes.guess_type(path.name)
    if media:
        return media
    return "image/jpeg"


def _image_item(page: Page) -> epub.EpubImage:
    ext = page.image_path.suffix.lower().lstrip(".") or "jpg"
    item = epub.EpubImage()
    item.file_name = f"images/page-{page.index:05d}.{ext}"
    item.media_type = _media_type(page.image_path)
    item.content = page.image_path.read_bytes()
    return item


def _chapter_content(
    page: Page,
    image_href: str,
    mode: str,
    language: str,
) -> str:
    safe_text = html.escape(page.text or "")
    image_html = (
        f'<img class="page-image" src="{html.escape(image_href)}" '
        f'alt="Page {page.index}" />'
    )

    if mode == "image":
        body = image_html
    elif mode == "text":
        body = f'<div class="ocr" lang="{html.escape(language)}">{safe_text}</div>'
    else:
        # 검색 가능하면서 원본 페이지 모양은 그대로 유지.
        body = (
            image_html
            + f'<div class="ocr-hidden" lang="{html.escape(language)}">'
            + safe_text
            + "</div>"
        )

    return f"""
    <html xmlns="http://www.w3.org/1999/xhtml">
      <head>
        <title>Page {page.index}</title>
        <link rel="stylesheet" type="text/css" href="../styles/style.css"/>
      </head>
      <body>
        <section class="page">
          {body}
        </section>
      </body>
    </html>
    """


def _image_dimensions(path: Path) -> tuple[int, int]:
    with Image.open(path) as im:
        return im.size


def build_epub(
    pages: list[Page],
    output: Path,
    title: str,
    author: str,
    language: str = "ja",
    mode: str = "hybrid",
    cover: Path | None = None,
) -> None:
    book = epub.EpubBook()
    book.set_identifier(str(uuid.uuid4()))
    book.set_title(title)
    book.set_language(language)
    if author:
        book.add_author(author)

    css = epub.EpubItem(
        uid="style",
        file_name="styles/style.css",
        media_type="text/css",
        content=CSS.encode("utf-8"),
    )
    book.add_item(css)

    chapters = []

    for page in pages:
        img_item = _image_item(page)
        book.add_item(img_item)

        chapter = epub.EpubHtml(
            title=f"Page {page.index}",
            file_name=f"text/page-{page.index:05d}.xhtml",
            lang=language,
        )
        chapter.content = _chapter_content(
            page=page,
            image_href=f"../{img_item.file_name}",
            mode=mode,
            language=language,
        )
        book.add_item(chapter)
        chapters.append(chapter)

    if cover and cover.exists():
        book.set_cover(
            f"cover{cover.suffix.lower()}",
            cover.read_bytes(),
        )

    book.toc = tuple(chapters)
    book.spine = ["nav", *chapters]

    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    output.parent.mkdir(parents=True, exist_ok=True)
    epub.write_epub(str(output), book)
