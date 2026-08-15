# folder2epub

이미지 폴더를 EPUB으로 만들고, 선택적으로 페이지별 OCR 텍스트를 넣는 Python CLI입니다. 기본 OCR engine은 일본어에 맞춘 PaddleOCR이며, manga-ocr와 Tesseract를 선택적으로 사용할 수 있습니다.

## macOS Quick Start

```bash
git clone <repository-url>
cd folder2epub
uv venv
source .venv/bin/activate
uv pip install -e ".[paddle]"
folder2epub ~/Books/my-book --ocr
```

일본어 책:

```bash
folder2epub ~/Books/my-book \
    --ocr \
    --ocr-engine paddle \
    --lang ja
```

`uv pip install -e ".[all]"`을 사용하면 모든 Python OCR backend를 설치할 수 있습니다. PaddleOCR는 첫 실행 시 모델을 다운로드할 수 있으며, CPU에서도 동작합니다. Apple Silicon에서 PaddlePaddle wheel 설치가 실패하면 현재 Python 버전에 맞는 PaddlePaddle 배포 지원 여부를 확인해야 합니다.

PaddleOCR 모델 다운로드가 끝나면 이후 실행에서는 로컬 캐시를 사용합니다. OCR을 중단한 경우 같은 명령을 다시 실행하면 이미 저장된 페이지 cache를 재사용합니다.

## 사용법

이미지만 EPUB으로 만들기:

```bash
folder2epub /path/to/book
```

OCR 기본값은 `paddle`, 언어 기본값은 `ja`입니다.

```bash
folder2epub book --ocr
folder2epub book --ocr --ocr-engine paddle --lang ja
folder2epub book --ocr --ocr-engine manga --lang ja
folder2epub book --ocr --ocr-engine tesseract --lang jpn
```

도움말:

```bash
folder2epub --help
```

주요 옵션은 `--ocr`, `--ocr-engine paddle|manga|tesseract`, `--lang`, `--mode hybrid|text|image`, `--force-ocr`, `--title`, `--author`, `--cover`, `--output`, `--output-dir`, `--recursive`입니다.

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
uv pip install -e ".[paddle]"  # 기본 backend
uv pip install -e ".[manga]"   # manga-ocr
brew install tesseract
brew install tesseract-lang
uv pip install -e ".[tesseract]" # Python 추가 패키지는 없음
```

Tesseract는 호환성을 위해 남아 있지만 기본 engine이 아닙니다. `--ocr-engine tesseract`를 명시해야 합니다.

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

PaddleOCR backend는 일본어 가로쓰기와 세로쓰기, 약간 회전된 페이지를 고려해 text-line orientation을 활성화합니다. 후리가나, 오래된 스캔, 큰 여백과 테두리는 원본 이미지 상태에 따라 인식 결과가 달라질 수 있습니다. 별도 전처리 pipeline은 다음 단계에서 backend 앞에 추가할 수 있도록 분리해 두었습니다.

## 개발

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[paddle]"
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
    ├── paddle.py      # PaddleOCR backend
    ├── manga.py       # 선택적 manga-ocr backend
    └── tesseract.py   # 호환성용 Tesseract backend
```

자세한 설계는 [`doc/design.ko.md`](doc/design.ko.md)와 [`doc/design.en.md`](doc/design.en.md)를 참고하세요.
