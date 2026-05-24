"""Founder attachment ingress — Markdown and PDF text extraction."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.config import DATA_DIR

UPLOADS_DIR = DATA_DIR / "uploads"
MAX_BYTES = 10 * 1024 * 1024


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def uploads_root() -> Path:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    return UPLOADS_DIR


def ingest_bytes(
    dashboard: dict[str, Any],
    *,
    filename: str,
    content: bytes,
    content_type: str | None = None,
) -> dict[str, Any]:
    if len(content) > MAX_BYTES:
        raise ValueError("FILE_TOO_LARGE")

    ext = Path(filename).suffix.lower()
    if ext not in {".md", ".markdown", ".pdf"}:
        raise ValueError("UNSUPPORTED_FORMAT")

    att_id = f"att-{uuid4().hex[:8]}"
    dest_dir = uploads_root() / att_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    original_path = dest_dir / f"original{ext}"
    original_path.write_bytes(content)

    extracted = _extract_text(ext, content)
    extracted_path = dest_dir / "extracted.md"
    extracted_path.write_text(extracted, encoding="utf-8")

    summary = _summarize(extracted)
    record = {
        "id": att_id,
        "filename": filename,
        "contentType": content_type or ext,
        "sizeBytes": len(content),
        "extractedSummary": summary,
        "extractedText": extracted[:8000],
        "actionItems": _extract_action_items(extracted),
        "createdAt": _now_iso(),
    }
    dashboard.setdefault("attachments", []).insert(0, record)
    from app.services.skill_attachment_proposal import maybe_propose_skill_from_attachment

    maybe_propose_skill_from_attachment(dashboard, record)
    return record


def attachment_context_for_prompt(records: list[dict[str, Any]]) -> str:
    if not records:
        return ""
    parts = ["附件摘要："]
    for rec in records:
        parts.append(f"· {rec.get('filename')}: {rec.get('extractedSummary', '')[:400]}")
        items = rec.get("actionItems") or []
        if items:
            parts.append(f"  待办: {'; '.join(items[:5])}")
    return "\n".join(parts)


def _extract_text(ext: str, content: bytes) -> str:
    if ext in {".md", ".markdown"}:
        return content.decode("utf-8", errors="replace")
    if ext == ".pdf":
        try:
            from pypdf import PdfReader
            from io import BytesIO

            reader = PdfReader(BytesIO(content))
            pages = []
            for page in reader.pages[:30]:
                text = page.extract_text() or ""
                if text.strip():
                    pages.append(text)
            return "\n\n".join(pages) if pages else "（PDF 未能提取文本，可能是扫描件）"
        except Exception as exc:  # noqa: BLE001
            return f"（PDF 解析失败: {exc}）"
    raise ValueError("UNSUPPORTED_FORMAT")


def _summarize(text: str, limit: int = 500) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1] + "…"


def _extract_action_items(text: str) -> list[str]:
    items: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if re.match(r"^[-*•]\s*(TODO|待办|行动|Action)", line, re.I):
            items.append(line[:120])
        elif re.match(r"^[-*•]\d+[.)]", line):
            items.append(line[:120])
    return items[:10]
