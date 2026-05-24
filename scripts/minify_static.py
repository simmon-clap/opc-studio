#!/usr/bin/env python3
"""Lightweight static asset minifier (whitespace/comments) for dashboard JS/CSS."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS_DIR = ROOT / "dashboards" / "app" / "js"
CSS_DIR = ROOT / "dashboards" / "app" / "css"


def _minify_js(text: str) -> str:
    text = re.sub(r"/\*[\s\S]*?\*/", "", text)
    text = re.sub(r"(^|[^:])//.*$", r"\1", text, flags=re.MULTILINE)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _minify_css(text: str) -> str:
    text = re.sub(r"/\*[\s\S]*?\*/", "", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s*([{}:;,>+~])\s*", r"\1", text)
    return text.strip()


def _write_if_smaller(path: Path, content: str) -> int:
    original = path.read_text(encoding="utf-8")
    if len(content) >= len(original):
        return 0
    path.write_text(content + "\n", encoding="utf-8")
    return len(original) - len(content)


def main() -> None:
    saved = 0
    for path in sorted(JS_DIR.glob("*.js")):
        saved += _write_if_smaller(path, _minify_js(path.read_text(encoding="utf-8")))
    for path in sorted(CSS_DIR.glob("*.css")):
        saved += _write_if_smaller(path, _minify_css(path.read_text(encoding="utf-8")))
    print(f"minify_static: saved ~{saved} bytes")


if __name__ == "__main__":
    main()
