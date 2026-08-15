# folder2epub

이미지 폴더를 EPUB으로 만들고, 선택적으로 페이지별 OCR 텍스트를 넣는 Python CLI입니다. 기본 OCR engine은 Apple Silicon용 MLX OCR이며, PaddleOCR, manga-ocr와 Tesseract를 선택적으로 사용할 수 있습니다.

## MLX란?

MLX는 Apple이 Apple Silicon용으로 만든 머신러닝 프레임워크입니다. M1/M2/M3/M4의 unified memory와 Metal GPU를 활용해 모델을 Mac에서 로컬로 실행합니다.

이 프로젝트의 `mlx-ppocr`는 PaddleOCR의 PP-OCR 계열 모델을 MLX runtime에서 실행하도록 포팅한 별도 구현입니다. 따라서 `paddleocr` Python package와는 다른 backend이며, PaddlePaddle이나 PyTorch를 설치하지 않고 MLX 모델을 사용합니다.

MLX weight는 일반 PaddleOCR weight와 runtime과 파일 형식이 달라 직접 호환되지 않습니다. Intel Mac이나 Metal이 없는 headless 환경에서는 실행할 수 없습니다.

## macOS Quick Start

```bash
git clone <repository-url>
cd folder2epub
uv venv
source .venv/bin/activate
uv tool install mlx-ppocr
uv pip install -e ".[mlx]"
folder2epub ~/Books/my-book --ocr
```

일본어 책:

```bash
folder2epub ~/Books/my-book \
    --ocr \
    --ocr-engine mlx \
    --ocr-model mobile \
    --lang ja
```

MLX OCR은 Apple Silicon의 Metal GPU를 사용합니다. MLX 모델은 첫 실행 시 다운로드될 수 있으며, `mlx-ocr`가 이미 설치되어 있다면 별도 설치 없이 사용할 수 있습니다.

PaddleOCR 모델 다운로드가 끝나면 이후 실행에서는 로컬 캐시를 사용합니다. OCR을 중단한 경우 같은 명령을 다시 실행하면 이미 저장된 페이지 cache를 재사용합니다.

## 사용법

이미지만 EPUB으로 만들기:

```bash
folder2epub /path/to/book
```

OCR 기본값은 `mlx`, 언어 기본값은 `ja`입니다.

```bash
folder2epub book --ocr
folder2epub book --ocr --ocr-engine mlx --ocr-model mobile --lang ja
folder2epub book --ocr --ocr-engine manga --lang ja
folder2epub book --ocr --ocr-engine tesseract --lang jpn
```

### 영문 OCR 리소스 사용

MLX에서 영어 리소스를 사용하려면 `--lang en`과 `--ocr-model server`를 지정합니다. EPUB metadata도 영어로 맞추려면 `--epub-language en`을 함께 사용합니다.

```bash
folder2epub ~/Books/english-book \
    --ocr \
    --ocr-engine mlx \
    --ocr-model server \
    --lang en \
    --epub-language en
```

Tesseract를 사용할 때는 Tesseract 언어 코드인 `eng`를 사용합니다.

```bash
brew install tesseract
brew install tesseract-lang
folder2epub ~/Books/english-book \
    --ocr \
    --ocr-engine tesseract \
    --lang eng \
    --epub-language en
```

`manga-ocr` backend는 일본어 전용이므로 영문 OCR에는 사용할 수 없습니다. 현재 CLI 도움말과 오류 메시지는 한국어이며, `--lang`은 OCR 인식 언어를 지정하는 옵션입니다.

도움말:

```bash
folder2epub --help
folder2epub --ui-lang en --help
```

주요 옵션은 `--ocr`, `--ocr-engine mlx|paddle|manga|tesseract`, `--ocr-model auto|mobile|server`, `--lang`, `--ui-lang ko|en`, `--locale-dir`, `--mode hybrid|text|image`, `--force-ocr`, `--title`, `--author`, `--cover`, `--output`, `--output-dir`, `--recursive`입니다.

## 다국어 메시지와 외부 리소스

CLI 메시지와 `--help` 내용은 본체 코드에 하드코딩하지 않고 외부 JSON 리소스에서 읽습니다.

기본 리소스:

```text
resources/i18n/ko.json
resources/i18n/en.json
```

기본 언어는 `ko`이며 영어 메시지와 도움말은 다음처럼 사용할 수 있습니다.

```bash
folder2epub --ui-lang en --help
folder2epub ./book --ui-lang en --ocr --lang en
```

별도 리소스 디렉터리를 사용하려면 `--locale-dir`를 지정합니다.

```bash
folder2epub \
  ./book \
  --ui-lang en \
  --locale-dir /path/to/my-i18n \
  --help
```

리소스 파일명은 언어 코드와 일치해야 합니다. 예를 들어 `fr.json`을 추가하면 `--ui-lang fr`로 선택할 수 있습니다. 번역되지 않은 언어는 영어 리소스로 fallback합니다. `--lang`은 OCR 인식 언어이고 `--ui-lang`은 CLI 메시지 언어이므로 서로 다른 옵션입니다.

정확한 파일명을 지정하려면 `--output`을 사용합니다.

```bash
folder2epub /path/to/book --output ~/Books/my-book.epub
```

출력 디렉터리만 지정하면 책 폴더명을 EPUB 파일명으로 사용합니다.

```bash
folder2epub /path/to/book --output-dir ~/Books/epub
# 결과: ~/Books/epub/book.epub
```

`--output`과 `--output-dir`은 함께 사용할 수 없습니다. 하위 폴더를 각각 EPUB으로 만들 때는 다음처럼 실행합니다.

```bash
folder2epub ~/Books --recursive --output-dir ~/Books/epub
```

이미지가 있는 모든 하위 폴더를 찾아 개별 EPUB을 만들며, 중첩된 폴더 구조는 출력 위치에도 유지합니다.

## Recursive batch 처리

이미지가 있는 하위 폴더를 각각 EPUB으로 만들 수 있습니다.

```text
Books/
├── Book A/
│   ├── 001.jpg
│   └── 002.jpg
└── Extra/Book B/
    └── 001.png
```

```bash
folder2epub ./Books --recursive --output-dir ./epub
```

결과:

```text
epub/Book A.epub
epub/Extra/Book B.epub
```

이미지가 포함된 폴더명은 EPUB 파일명이 되고, 중첩된 상대 경로는 출력 위치에도 유지됩니다. `--output`과 `--output-dir`은 함께 사용할 수 없습니다.

## OCR backend 설치

선택한 backend가 없으면 실행이 중단되고 설치 명령을 안내합니다.

```bash
uv tool install mlx-ppocr       # 기본 MLX backend
uv pip install -e ".[paddle]"  # 선택적 PaddleOCR backend
uv pip install -e ".[manga]"   # manga-ocr
brew install tesseract
brew install tesseract-lang
uv pip install -e ".[tesseract]" # Python 추가 패키지는 없음
```

PaddleOCR, manga-ocr, Tesseract는 호환성을 위해 남아 있지만 기본 engine이 아닙니다. `--ocr-engine`으로 명시해야 합니다.

## EPUB 모드와 캐시

- `hybrid` (기본): 원본 스캔 이미지를 표시하면서 EPUB 내부에 OCR 텍스트를 넣어 검색 가능하게 합니다.
- `text`: OCR 텍스트 중심으로 페이지를 만듭니다.
- `image`: 원본 이미지만 표시합니다.

OCR 없이 실행하면 자동으로 `image` 모드가 됩니다. OCR 캐시는 각 책의 `.folder2epub-cache/`에 저장되며 이미지 metadata, engine, language, engine options를 cache key에 포함합니다. 따라서 PaddleOCR, manga-ocr, Tesseract 결과가 서로 충돌하지 않습니다.

## 이미지 순서와 지원 형식

파일명은 자연 정렬합니다.

```text
1.jpg
2.jpg
3.jpg
10.jpg
```

지원 형식은 `.jpg`, `.jpeg`, `.png`, `.webp`, `.tif`, `.tiff`, `.bmp`입니다.

## 일본어 스캔 참고

MLX backend는 Apple Silicon의 Metal GPU를 사용하며 `--ocr-model auto|mobile|server`로 모델 preset을 선택합니다. 일본어 세로쓰기, 후리가나, 오래된 스캔은 모델과 원본 품질에 따라 결과가 달라질 수 있습니다. 별도 전처리 pipeline은 다음 단계에서 backend 앞에 추가할 수 있도록 분리해 두었습니다.

## 개발

```bash
uv venv
source .venv/bin/activate
uv tool install mlx-ppocr
uv pip install -e .
uv pip install pytest
python -m compileall src
uv run pytest
```

## 프로젝트 구조

```text
src/folder2epub/
├── cli.py             # CLI와 단일/recursive 실행
├── epub_builder.py    # image/text/hybrid EPUB 생성
├── images.py          # 지원 확장자와 자연 정렬
├── models.py          # Page 모델
└── ocr/
    ├── base.py        # OCRBackend Protocol
    ├── mlx.py         # MLX OCR backend
    ├── paddle.py      # 선택적 PaddleOCR backend
    ├── manga.py       # 선택적 manga-ocr backend
    └── tesseract.py   # 호환성용 Tesseract backend
```

외부 메시지 리소스는 `resources/i18n/`에 둡니다. 새 언어를 추가할 때는 기존 JSON key를 유지한 `<language>.json` 파일을 추가합니다.

자세한 설계는 [`doc/design.ko.md`](doc/design.ko.md)와 [`doc/design.en.md`](doc/design.en.md)를 참고하세요.

---

# English

`folder2epub` converts folders of page images into EPUB files. MLX OCR is the default backend on Apple Silicon and Japanese (`ja`) is the default OCR language. PaddleOCR, `manga-ocr`, and Tesseract are optional backends.

## Quick start

```bash
uv venv
source .venv/bin/activate
uv tool install mlx-ppocr
uv pip install -e .
folder2epub ~/Books/my-book --ocr
```

Create an image-only EPUB:

```bash
folder2epub ~/Books/my-book
```

Use English OCR resources:

```bash
folder2epub ~/Books/english-book \
  --ocr \
  --ocr-engine mlx \
  --ocr-model server \
  --lang en \
  --epub-language en
```

## Recursive batch mode

Every directory containing supported images becomes a separate EPUB. The image directory name becomes the EPUB filename, and nested paths are preserved.

```bash
folder2epub ./Books --recursive --output-dir ./epub
```

For example, `Books/Extra/Book B/*.jpg` becomes `epub/Extra/Book B.epub`.

## Internationalized messages

CLI messages and `--help` are loaded from external JSON resources:

```text
resources/i18n/ko.json
resources/i18n/en.json
```

Use English messages and help:

```bash
folder2epub --ui-lang en --help
```

Use a custom resource directory:

```bash
folder2epub ./book \
  --ui-lang en \
  --locale-dir ./my-i18n \
  --help
```

Add another language by creating `<language>.json` with the existing resource keys. If the selected resource is missing, the CLI falls back to English.

## Development

```bash
python -m compileall src
uv run pytest
```

See [`doc/design.en.md`](doc/design.en.md) for the full English design document.
