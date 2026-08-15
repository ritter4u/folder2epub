# folder2epub 설계서

## 1. 목적

`folder2epub`는 이미지 폴더를 EPUB으로 변환하는 Python 3.10+ CLI다. 일본어 스캔 서적을 주요 대상으로 하며, OCR engine을 교체할 수 있도록 OCR 기능을 독립 backend로 분리한다.

OCR engine 기본값은 플랫폼 자동 선택이다. Apple Silicon macOS에서는 MLX OCR을, Windows·Linux·Intel Mac에서는 PaddleOCR을 선택한다. `mlx`, `paddle`, `manga`, `tesseract`를 명시적으로 선택할 수도 있다.

## 2. 실행 모델

단일 책:

```bash
folder2epub ./book --ocr
```

하위 폴더 batch:

```bash
folder2epub ./Books --recursive --ocr --output-dir ./epub
```

recursive 모드에서는 지원 이미지를 포함한 모든 폴더를 독립적인 책으로 취급한다. EPUB 파일명은 이미지 폴더명에서 만들고, 중첩된 상대 경로는 출력 디렉터리에도 유지한다.

```text
Books/Extra/Book B/*.jpg
→ epub/Extra/Book B.epub
```

입력과 출력 경로는 `./`, `../` 같은 상대 경로와 절대 경로를 모두 지원한다.

## 3. 구성 요소

```text
CLI → 이미지 탐색/자연 정렬 → OCR factory → EPUB builder
                         ↓
                 페이지별 OCR cache
```

주요 파일:

- `cli.py`: 옵션 검증, 단일 책 처리, recursive batch 처리
- `images.py`: 이미지 확장자 필터와 자연 정렬
- `models.py`: `Page(index, image_path, text)` 모델
- `epub_builder.py`: EPUB 이미지, XHTML, CSS, TOC, spine 생성
- `ocr/base.py`: `OCRBackend` Protocol과 `OCRError`
- `ocr/__init__.py`: factory와 cache orchestration
- `ocr/mlx.py`: `mlx-ocr` subprocess backend
- `ocr/paddle.py`: PaddleOCR 3.x backend
- `ocr/manga.py`: 선택적 manga-ocr backend
- `ocr/tesseract.py`: 호환성용 subprocess backend

이미지 전처리는 향후 OCR backend 앞에 별도 pipeline으로 추가할 수 있다.

## 4. OCR backend 계약

```python
class OCRBackend(Protocol):
    name: str

    def recognize(self, image: Path) -> str:
        ...
```

CLI는 개별 OCR 라이브러리를 직접 import하지 않는다. `create_ocr_backend(engine, language, options)`가 engine을 선택하고, 라이브러리 import는 backend 초기화 시점에 지연한다.

backend는 CLI 프로세스에서 engine/language/options 조합별로 한 번만 초기화하고 모든 책과 페이지에서 재사용한다. MLX는 여기에 더해 한 책에서 cache에 없는 페이지들을 한 번의 `mlx-ocr` subprocess로 전달한다. 페이지별 cache 파일은 계속 유지하므로 중단 후 재실행하면 완료된 페이지는 건너뛴다.

## 5. MLX OCR

MLX는 Apple이 Apple Silicon을 위해 만든 머신러닝 프레임워크다. unified memory와 Metal GPU를 사용해 모델을 Mac 로컬에서 실행한다. 이 프로젝트의 `mlx-ppocr`는 PaddleOCR의 PP-OCR 계열 모델을 MLX runtime에서 실행하도록 포팅한 별도 구현이다.

MLX weight와 일반 PaddleOCR weight는 runtime과 파일 형식이 다르므로 직접 교차 사용할 수 없다. 두 구현은 같은 `OCRBackend` 계약 아래에서 별도 engine으로 선택한다.

Apple Silicon에서는 `mlx-ocr`를 기본 backend로 사용한다. `mlx_ppocr.MLXOCR` 계열의 CLI를 subprocess로 호출하며, 모델은 `--ocr-model`로 선택한다.

- `auto`: 언어에 따라 preset 선택
- `mobile`: 일본어·다국어 mobile 모델
- `server`: 정확도 우선 server 모델

첫 실행 시 MLX weight 다운로드·변환이 발생할 수 있다. stderr 진행 로그는 사용자 터미널에 전달하고 JSON stdout만 OCR 결과 파싱에 사용한다.

`recognize_many()`가 반환하는 페이지별 JSON 결과를 개별 cache 파일로 저장한다. 모든 페이지가 cache에 있으면 MLX subprocess를 실행하지 않는다.

설치:

```bash
uv tool install mlx-ppocr
```

M1/M2/M3/M4 Apple Silicon의 Metal 환경을 대상으로 한다. headless 또는 Metal 장치가 없는 환경에서는 실제 추론을 실행할 수 없다.

## 6. PaddleOCR 호환 backend

PaddleOCR 3.x의 `PaddleOCR(...).predict(...)` API를 사용한다. `ja`, `jpn`, `jpn_vert`는 PaddleOCR의 `japan` 언어 설정으로 매핑한다.

text-line orientation을 활성화해 일본어 가로쓰기, 세로쓰기, 일부 회전 페이지에 대응한다. 인식 결과는 반환된 읽기 순서의 텍스트를 줄바꿈으로 합친다.

Paddle 모델은 선택적으로 설치할 수 있으며 실제 모델 다운로드가 필요한 테스트는 일반 unit test에서 실행하지 않는다.

## 7. 선택 backend

### manga-ocr

`manga_ocr.MangaOcr`를 지연 import한다. 패키지가 없으면 다음 설치 방법을 안내한다.

```text
manga-ocr backend가 설치되어 있지 않습니다.
pip install manga-ocr
```

### Tesseract

기존 호환성을 위해 유지한다. 시스템 실행 파일과 언어 데이터를 사용하며 `--ocr-engine tesseract`를 명시해야 한다. `--psm`은 Tesseract backend에 전달된다.

## 8. CLI와 출력 규칙

- `--ocr`: OCR 활성화
- `--ocr-engine auto|mlx|paddle|manga|tesseract`: backend 선택
- `--ocr-model auto|mobile|server`: MLX model preset 선택
- `--ocr-device auto|cpu|gpu`: PaddleOCR 실행 장치 선택
- `--lang ja`: OCR 언어, 기본값 `ja`
- `--recursive`: 하위 이미지 폴더를 개별 EPUB으로 변환
- `--output`: 단일 EPUB의 정확한 파일 경로
- `--output-dir`: EPUB 출력 루트 디렉터리
- `--mode hybrid|text|image`: EPUB 표시 모드
- `--force-ocr`: cache 무시
- `--title`, `--author`, `--cover`, `--epub-language`: 책 metadata

`--output`과 `--output-dir`은 함께 사용할 수 없다. recursive 모드에서는 `--output-dir`을 사용한다. 이미지 폴더명은 EPUB 파일명이 되며 nested 폴더 경로는 보존된다.

## 9. 다국어 메시지와 외부 리소스

CLI 메시지와 `--help` 내용은 실행 코드와 분리된 JSON 리소스에서 읽는다.

```text
resources/i18n/ko.json
resources/i18n/en.json
```

주요 옵션:

- `--ui-lang`: CLI 메시지와 도움말 언어
- `--locale-dir`: 외부 i18n 리소스 디렉터리
- `--help`: 선택한 언어의 외부 help 문구 출력

`--lang`은 OCR 인식 언어이고 `--ui-lang`은 사용자 interface 언어다. 기본 UI 언어는 `ko`다. `--ui-lang`으로 지정한 JSON이 없으면 `en.json`으로 fallback한다. 새 언어는 기존 key를 유지한 `<language>.json` 파일을 `resources/i18n/` 또는 `--locale-dir` 경로에 추가한다.

help는 Typer의 기본 자동 help 대신 외부 resource의 `help_text`를 사용한다. 따라서 다음 명령이 가능하다.

```bash
folder2epub --help
folder2epub --ui-lang en --help
folder2epub --ui-lang fr --locale-dir ./my-i18n --help
```

## 10. OCR cache

cache 위치는 각 책 폴더의 `.folder2epub-cache/`다. cache key에는 다음 정보가 포함된다.

- 이미지 절대 경로
- 이미지 크기와 modification time
- OCR engine
- language
- engine options (`psm` 포함)

예시:

```text
001.paddle-ja-<key>.txt
001.manga-ja-<key>.txt
```

engine이나 옵션이 바뀌면 기존 결과와 충돌하지 않는다. OCR이 중단되어도 완료된 페이지는 재사용할 수 있다.

## 11. EPUB 출력

- `image`: 원본 스캔 이미지만 표시
- `text`: OCR 텍스트 중심
- `hybrid`: 원본 이미지를 표시하고 OCR 텍스트를 EPUB 내부에 포함

OCR 없이 실행하면 자동으로 `image` 모드를 사용한다. hybrid 모드의 OCR 텍스트는 XHTML에 포함해 검색 가능하게 하고, 화면에서는 숨겨 원본 레이아웃을 유지한다.

지원 형식은 `jpg`, `jpeg`, `png`, `webp`, `tif`, `tiff`, `bmp`이며 파일명은 자연 정렬한다.

## 12. 의존성과 검증

```bash
uv venv
source .venv/bin/activate
uv tool install mlx-ppocr
uv pip install -e .
python -m compileall src
uv run pytest
```

- `[mlx]`: 외부 `mlx-ppocr` tool 사용
- `[paddle]`: `paddlepaddle`, `paddleocr` 호환 backend
- `[manga]`: `manga-ocr`
- `[tesseract]`: 추가 Python package 없음; macOS에서는 Homebrew 설치 필요
- `[all]`: PaddleOCR와 manga-ocr

## 13. 제한사항과 다음 단계

- 세로쓰기와 후리가나 품질은 원본 스캔과 OCR 모델에 좌우된다.
- deskew, 여백 제거, 테두리 제거 같은 전처리는 최소화되어 있다.
- 모델 다운로드와 Python/PyTorch/PaddlePaddle 호환성은 실행 환경의 영향을 받는다.
- 향후 `Preprocessor` Protocol을 OCR backend 앞에 추가할 수 있다.
- Apple Vision 등 새로운 engine은 `OCRBackend` 구현과 factory 등록으로 추가한다.
- 추가 UI 언어의 번역 품질과 resource key 검증을 자동화한다.
