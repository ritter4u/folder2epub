from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class I18n:
    def __init__(self, language: str = "ko", resource_dir: Path | None = None):
        self.language = language.lower().replace("_", "-")
        directory = resource_dir or _default_resource_dir()
        path = directory / f"{self.language}.json"
        if not path.exists():
            self.language = "en"
            path = directory / "en.json"
        self.messages: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))

    def get(self, key: str, **values: object) -> str:
        template = str(self.messages.get(key, key))
        return template.format(**values)


def _default_resource_dir() -> Path:
    configured = os.environ.get("FOLDER2EPUB_LOCALE_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    cwd_dir = Path.cwd() / "resources" / "i18n"
    if cwd_dir.exists():
        return cwd_dir
    return Path(__file__).resolve().parents[2] / "resources" / "i18n"


def raw_ui_language() -> str:
    arguments = os.environ.get("FOLDER2EPUB_UI_LANG", "ko")
    # --ui-lang is read here because --help is intentionally eager.
    import sys

    for index, argument in enumerate(sys.argv):
        if argument == "--ui-lang" and index + 1 < len(sys.argv):
            return sys.argv[index + 1]
        if argument.startswith("--ui-lang="):
            return argument.split("=", 1)[1]
    return arguments


def raw_resource_dir() -> Path | None:
    import sys

    for index, argument in enumerate(sys.argv):
        if argument == "--locale-dir" and index + 1 < len(sys.argv):
            return Path(sys.argv[index + 1]).expanduser().resolve()
        if argument.startswith("--locale-dir="):
            return Path(argument.split("=", 1)[1]).expanduser().resolve()
    return None
