from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .base import OCRError


class MLXOCRBackend:
    name = "mlx"

    def __init__(self, language: str = "ja", options: dict[str, Any] | None = None):
        self.model = (options or {}).get("model", "mobile")
        self.language = language
        self.executable = shutil.which("mlx-ocr")
        if not self.executable:
            raise OCRError(
                "MLX OCR backend가 설치되어 있지 않습니다.\n"
                "uv tool install paddleocr-mlx"
            )

    def recognize(self, image: Path) -> str:
        process = subprocess.run(
            [
                self.executable,
                "--json",
                "--fields",
                "text",
                "--lang",
                _model_for_language(self.language, self.model),
                str(image),
            ],
            # Keep model download/conversion progress visible. Only JSON
            # stdout is captured for parsing; MLX diagnostics use stderr.
            stdout=subprocess.PIPE,
            text=True,
        )
        if process.returncode != 0:
            raise OCRError(f"MLX OCR 실패: {image.name}")
        return _extract_text(process.stdout)


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
