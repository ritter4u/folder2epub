from __future__ import annotations

import json
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

from .base import OCRError


class MLXOCRBackend:
    name = "mlx"

    def __init__(self, language: str = "ja", options: dict[str, Any] | None = None):
        self.model = (options or {}).get("model", "mobile")
        if self.model not in {"auto", "mobile", "server"}:
            raise OCRError("지원하지 않는 MLX 모델입니다: auto, mobile, server 중 하나를 사용하세요.")
        self.language = language
        self.executable = shutil.which("mlx-ocr")
        if not self.executable or Path(self.executable).name != "mlx-ocr":
            raise OCRError(
                "MLX OCR backend가 설치되어 있지 않습니다.\n"
                "uv tool install mlx-ppocr"
            )
        self.executable = str(Path(self.executable).resolve())

    def recognize(self, image: Path) -> str:
        command = [
            self.executable,
            "--json",
            "--fields",
            "text",
            "--lang",
            _model_for_language(self.language, self.model),
            str(image.resolve()),
        ]
        # shell=False and an argv list ensure paths/model values are arguments,
        # never shell syntax. The executable is resolved from the fixed
        # `mlx-ocr` command above, not accepted as a CLI option.
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=False,
        )
        stderr_lines: list[str] = []

        def forward_stderr() -> None:
            if process.stderr is None:
                return
            for line in process.stderr:
                stderr_lines.append(line.rstrip())
                print(line, end="", file=sys.stderr, flush=True)

        stderr_thread = threading.Thread(target=forward_stderr, daemon=True)
        stderr_thread.start()
        stdout, _ = process.communicate()
        stderr_thread.join()

        if process.returncode != 0:
            snippet = "\n".join(stderr_lines[:10]).strip()
            details = f"\nstderr:\n{snippet}" if snippet else ""
            raise OCRError(
                f"MLX OCR 실패 (반환 코드 {process.returncode}): {image.name}{details}"
            )
        return _extract_text(stdout)


def _model_for_language(language: str, model: str) -> str:
    if model != "auto":
        return model
    first = language.split("+")[0].strip().lower()
    return "mobile" if first in {"ja", "jpn", "jpn_vert"} else "server"


def _extract_text(output: str) -> str:
    texts: list[str] = []
    for line in output.splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        results = value.get("results", []) if isinstance(value, dict) else []
        if isinstance(results, list):
            texts.extend(
                str(item["text"]).strip()
                for item in results
                if isinstance(item, dict) and item.get("text")
            )
    return "\n".join(texts).strip()
