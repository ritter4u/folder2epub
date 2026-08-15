from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.progress import track

from .epub_builder import build_epub
from .images import find_images
from .models import Page
from .ocr import OCRError, SUPPORTED_ENGINES, create_ocr_backend, ocr_image

app = typer.Typer(
    add_completion=False,
    help="이미지 폴더를 EPUB으로 변환하고 선택적으로 OCR을 실행합니다.",
)
console = Console()


def _default_epub_language(ocr_lang: str) -> str:
    first = ocr_lang.split("+")[0].strip()
    return {
        "jpn": "ja",
        "jpn_vert": "ja",
        "kor": "ko",
        "eng": "en",
        "chi_sim": "zh-CN",
        "chi_tra": "zh-TW",
    }.get(first, "und")


@app.command()
def main(
    folder: Annotated[
        Path,
        typer.Argument(
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            resolve_path=True,
            help="페이지 이미지가 들어 있는 폴더",
        ),
    ],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="출력 EPUB 경로"),
    ] = None,
    output_dir: Annotated[
        Path | None,
        typer.Option("--output-dir", help="출력 EPUB을 저장할 디렉터리"),
    ] = None,
    recursive: Annotated[
        bool,
        typer.Option("--recursive", help="하위 폴더의 이미지 폴더도 각각 EPUB으로 변환"),
    ] = False,
    ocr: Annotated[
        bool,
        typer.Option("--ocr/--no-ocr", help="OCR 실행 (기본 engine: paddle)"),
    ] = False,
    lang: Annotated[
        str,
        typer.Option("--lang", "-l", help="OCR 언어. 기본값: ja"),
    ] = "ja",
    ocr_engine: Annotated[
        str,
        typer.Option(
            "--ocr-engine",
            help="OCR engine: paddle | manga | tesseract",
            case_sensitive=False,
        ),
    ] = "paddle",
    psm: Annotated[
        int,
        typer.Option("--psm", help="Tesseract Page Segmentation Mode"),
    ] = 3,
    mode: Annotated[
        str,
        typer.Option("--mode", help="hybrid | text | image"),
    ] = "hybrid",
    title: Annotated[
        str | None,
        typer.Option("--title", help="책 제목"),
    ] = None,
    author: Annotated[
        str,
        typer.Option("--author", help="저자"),
    ] = "",
    epub_language: Annotated[
        str | None,
        typer.Option("--epub-language", help="EPUB 언어 코드. 예: ja, ko, en"),
    ] = None,
    cover: Annotated[
        Path | None,
        typer.Option("--cover", help="표지 이미지"),
    ] = None,
    force_ocr: Annotated[
        bool,
        typer.Option("--force-ocr", help="OCR 캐시를 무시하고 다시 인식"),
    ] = False,
):
    if recursive:
        if output is not None:
            console.print("[red]--recursive에서는 --output 대신 --output-dir을 사용하세요.[/red]")
            raise typer.Exit(2)

        candidates = [folder]
        candidates.extend(
            sorted(
                (path for path in folder.rglob("*") if path.is_dir()),
                key=lambda path: str(path).lower(),
            )
        )
        book_folders = [path for path in candidates if find_images(path)]
        if not book_folders:
            console.print(f"[red]이미지 폴더를 찾을 수 없습니다: {folder}[/red]")
            raise typer.Exit(1)

        target_root = output_dir.expanduser().resolve() if output_dir else folder.parent
        for book_folder in book_folders:
            relative = book_folder.relative_to(folder)
            target = target_root / relative.parent / f"{book_folder.name}.epub"
            main(
                book_folder,
                output=target,
                output_dir=None,
                recursive=False,
                ocr=ocr,
                lang=lang,
                ocr_engine=ocr_engine,
                psm=psm,
                mode=mode,
                title=title,
                author=author,
                epub_language=epub_language,
                cover=cover,
                force_ocr=force_ocr,
            )
        return

    if mode not in {"hybrid", "text", "image"}:
        console.print("[red]--mode는 hybrid, text, image 중 하나여야 합니다.[/red]")
        raise typer.Exit(2)

    ocr_engine = ocr_engine.lower()
    if ocr_engine not in SUPPORTED_ENGINES:
        console.print(
            "[red]--ocr-engine은 paddle, manga, tesseract 중 하나여야 합니다.[/red]"
        )
        raise typer.Exit(2)

    images = find_images(folder)
    if not images:
        console.print(f"[red]이미지를 찾을 수 없습니다: {folder}[/red]")
        raise typer.Exit(1)

    if output is not None and output_dir is not None:
        console.print("[red]--output과 --output-dir은 함께 사용할 수 없습니다.[/red]")
        raise typer.Exit(2)

    if output is None:
        target_dir = output_dir.expanduser().resolve() if output_dir else folder.parent
        output = target_dir / f"{folder.name}.epub"
    output = output.expanduser().resolve()

    book_title = title or folder.name
    effective_mode = mode if ocr else "image"
    language_code = epub_language or _default_epub_language(lang)

    cache_dir = folder / ".folder2epub-cache"
    pages: list[Page] = []
    backend = None
    if ocr:
        try:
            backend = create_ocr_backend(
                engine=ocr_engine,
                language=lang,
                options={"psm": psm},
            )
        except OCRError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(1)

    console.print(
        f"[bold]folder2epub[/bold]  "
        f"{len(images)} pages → {output.name}"
    )

    for idx, image in enumerate(
        track(images, description="페이지 처리 중..."),
        start=1,
    ):
        text = ""
        if ocr:
            try:
                text = ocr_image(
                    image=image,
                    cache_dir=cache_dir,
                    lang=lang,
                    psm=psm,
                    force=force_ocr,
                    engine=ocr_engine,
                    backend=backend,
                )
            except OCRError as exc:
                console.print(f"\n[red]{exc}[/red]")
                raise typer.Exit(1)

        pages.append(Page(index=idx, image_path=image, text=text))

    if cover is not None:
        cover = cover.expanduser().resolve()

    build_epub(
        pages=pages,
        output=output,
        title=book_title,
        author=author,
        language=language_code,
        mode=effective_mode,
        cover=cover,
    )

    console.print(f"[green]완료:[/green] {output}")
    if ocr:
        console.print(f"[dim]OCR cache: {cache_dir}[/dim]")


if __name__ == "__main__":
    app()
