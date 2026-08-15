# folder2epub Design Document

## 1. Purpose

`folder2epub` is a Python 3.10+ CLI that converts image folders into EPUB files. Its primary target is scanned Japanese books, so OCR is isolated behind replaceable backends.

The default OCR engine is platform-aware: MLX on Apple Silicon macOS, and PaddleOCR on Windows, Linux, and Intel Macs. `ja` remains the default language. MLX, PaddleOCR, `manga-ocr`, and Tesseract can also be selected explicitly.

## 2. Execution model

Single book:

```bash
folder2epub ./book --ocr
```

Recursive batch:

```bash
folder2epub ./Books --recursive --ocr --output-dir ./epub
```

In recursive mode, every directory containing at least one supported image is treated as an independent book. The EPUB filename comes from the image directory name, and nested relative paths are preserved below the output directory.

```text
Books/Extra/Book B/*.jpg
→ epub/Extra/Book B.epub
```

Both relative paths such as `./` and `../`, and absolute paths are supported.

## 3. Components

```text
CLI → image discovery/natural sorting → OCR factory → EPUB builder
                                      ↓
                              per-page OCR cache
```

Main files:

- `cli.py`: option validation, single-book processing, recursive batch processing
- `images.py`: image extension filtering and natural sorting
- `models.py`: `Page(index, image_path, text)` model
- `epub_builder.py`: EPUB images, XHTML, CSS, TOC, and spine
- `ocr/base.py`: `OCRBackend` Protocol and `OCRError`
- `ocr/__init__.py`: factory and cache orchestration
- `ocr/mlx.py`: `mlx-ocr` subprocess backend
- `ocr/paddle.py`: PaddleOCR 3.x backend
- `ocr/manga.py`: optional manga-ocr backend
- `ocr/tesseract.py`: compatibility subprocess backend

Image preprocessing can be added later as a separate pipeline before an OCR backend.

## 4. OCR backend contract

```python
class OCRBackend(Protocol):
    name: str

    def recognize(self, image: Path) -> str:
        ...
```

The CLI does not import individual OCR libraries directly. `create_ocr_backend(engine, language, options)` selects the engine, while library imports are deferred until backend initialization.

A backend is initialized once per engine/language/options combination in a CLI process and reused across all books and pages. MLX additionally sends all uncached pages of one book to a single `mlx-ocr` subprocess. Page-level cache files are preserved, so a resumed run skips pages that are already complete.

## 5. MLX OCR

MLX is Apple's machine-learning framework for Apple Silicon. It uses unified memory and Metal GPU to run models locally on a Mac. In this project, `mlx-ppocr` is a separate port of PaddleOCR's PP-OCR family for the MLX runtime.

MLX weights and standard PaddleOCR weights use different runtimes and file formats, so they are not directly interchangeable. Both implementations are selected as separate engines behind the same `OCRBackend` contract.

On Apple Silicon, `mlx-ocr` is the default backend. The CLI invokes the `mlx_ppocr.MLXOCR`-based command as a subprocess; models are selected with `--ocr-model`.

- `auto`: select a preset from the language
- `mobile`: Japanese and multilingual mobile model
- `server`: accuracy-oriented server model

The first run may download and convert MLX weights. stderr progress is forwarded to the terminal while JSON stdout is parsed as OCR output.

`recognize_many()` maps the JSON result for each page back to its individual cache file. If every page is cached, no MLX subprocess is started.

Install:

```bash
uv tool install mlx-ppocr
```

The target environment is Apple Silicon M1/M2/M3/M4 with Metal available. Headless environments without a Metal device cannot run actual inference.

## 6. PaddleOCR compatibility backend

The implementation uses the PaddleOCR 3.x `PaddleOCR(...).predict(...)` API. The language values `ja`, `jpn`, and `jpn_vert` map to PaddleOCR's `japan` setting.

Text-line orientation is enabled to help with horizontal Japanese text, vertical text, and mildly rotated pages. Recognition segments are joined with newlines in the order returned by PaddleOCR.

Paddle models are optional. Unit tests do not download or execute real OCR models.

## 7. Optional backends

### manga-ocr

`manga_ocr.MangaOcr` is imported lazily. If it is missing, the CLI provides this installation guidance:

```text
manga-ocr backend가 설치되어 있지 않습니다.
pip install manga-ocr
```

### Tesseract

Tesseract is retained for compatibility. It uses the system executable and installed language data, and must be selected explicitly with `--ocr-engine tesseract`. The `--psm` option is passed to this backend.

## 8. CLI and output rules

- `--ocr`: enable OCR
- `--ocr-engine auto|mlx|paddle|manga|tesseract`: select a backend
- `--ocr-model auto|mobile|server`: select the MLX model preset
- `--ocr-device auto|cpu|gpu`: select the PaddleOCR device
- `--lang ja`: OCR language, default `ja`
- `--recursive`: convert nested image directories into separate EPUBs
- `--output`: exact output path for a single EPUB
- `--output-dir`: EPUB output root directory
- `--mode hybrid|text|image`: EPUB presentation mode
- `--force-ocr`: ignore the cache
- `--title`, `--author`, `--cover`, `--epub-language`: book metadata

`--output` and `--output-dir` are mutually exclusive. Recursive mode uses `--output-dir`. The image directory name becomes the EPUB filename, while nested directory paths are preserved.

## 9. Internationalized messages and external resources

CLI messages and `--help` content are loaded from JSON resources outside the executable code.

```text
resources/i18n/ko.json
resources/i18n/en.json
```

Key options:

- `--ui-lang`: language for CLI messages and help
- `--locale-dir`: external i18n resource directory
- `--help`: print help text from the selected external resource

`--lang` selects the OCR recognition language, while `--ui-lang` selects the user-interface language. The default UI language is `ko`. If the selected resource is missing, the loader falls back to `en.json`. New languages are added as `<language>.json` files with the existing keys under `resources/i18n/` or a custom `--locale-dir`.

The application uses the external `help_text` resource instead of Typer's automatic help output, so these commands are supported:

```bash
folder2epub --help
folder2epub --ui-lang en --help
folder2epub --ui-lang fr --locale-dir ./my-i18n --help
```

## 10. OCR cache

The cache is stored in `.folder2epub-cache/` inside each book directory. The cache key includes:

- absolute image path
- image size and modification time
- OCR engine
- language
- engine options, including `psm`

Examples:

```text
001.paddle-ja-<key>.txt
001.manga-ja-<key>.txt
```

Changing the engine or its options cannot collide with an older result. Completed pages can be reused after an interrupted OCR run.

## 11. EPUB output

- `image`: display the original scanned image only
- `text`: text-centered OCR output
- `hybrid`: display the original image and include OCR text inside the EPUB

When OCR is disabled, the effective mode is automatically `image`. In hybrid mode, OCR text is included in XHTML for searchability and visually hidden to preserve the original layout.

Supported formats are `jpg`, `jpeg`, `png`, `webp`, `tif`, `tiff`, and `bmp`; filenames use natural sorting.

## 12. Dependencies and verification

```bash
uv venv
source .venv/bin/activate
uv tool install mlx-ppocr
uv pip install -e .
python -m compileall src
uv run pytest
```

- `[mlx]`: external `mlx-ppocr` tool
- `[paddle]`: `paddlepaddle`, `paddleocr` compatibility backend
- `[manga]`: `manga-ocr`
- `[tesseract]`: no additional Python package; install it with Homebrew on macOS
- `[all]`: PaddleOCR and manga-ocr

## 13. Limitations and next steps

- Recognition quality for vertical text and furigana depends on the source scan and OCR model.
- Deskewing, margin removal, and border removal are intentionally minimal.
- Model downloads and Python/PyTorch/PaddlePaddle compatibility depend on the execution environment.
- A `Preprocessor` Protocol can be added before OCR backends in a future iteration.
- New engines such as Apple Vision can be added by implementing `OCRBackend` and registering the engine in the factory.
- Translation quality and resource-key validation should be automated for additional UI languages.
