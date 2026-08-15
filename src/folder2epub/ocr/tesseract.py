from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from .base import OCRError


class TesseractOCRBackend:
    name = "tesseract"

    def __init__(self, language: str = "ja", options: dict[str, Any] | None = None):
        self.language = language
        self.psm = int((options or {}).get("psm", 3))
        self.executable = shutil.which("tesseract")
        if not self.executable:
            raise OCRError(
                "tesseract를 찾을 수 없습니다. macOS에서는 "
                "`brew install tesseract && brew install tesseract-lang` 후 다시 실행하세요."
            )
        self._validate_language()

    def _validate_language(self) -> None:
        proc = subprocess.run(
            [self.executable, "--list-langs"],
            capture_output=True,
            text=True,
            check=True,
        )
        available = {
            line.strip()
            for line in proc.stdout.splitlines()
            if line.strip() and not line.lower().startswith("list of available")
        }
        requested = {item.strip() for item in self.language.split("+") if item.strip()}
        missing = sorted(requested - available)
        if missing:
            raise OCRError(
                "설치되지 않은 Tesseract 언어입니다: "
                + ", ".join(missing)
                + "\n`tesseract --list-langs`로 현재 언어를 확인하세요."
            )

    def recognize(self, image: Path) -> str:
        proc = subprocess.run(
            [
                self.executable,
                str(image),
                "stdout",
                "-l",
                self.language,
                "--psm",
                str(self.psm),
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise OCRError(f"OCR 실패: {image.name}\n{proc.stderr.strip()}")
        return proc.stdout.replace("\x0c", "").strip()

