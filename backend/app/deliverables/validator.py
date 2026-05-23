"""Post-generation quality checks for deliverables."""

from __future__ import annotations

import re
from typing import Any

from app.deliverables.templates import get_template


def validate_content(kind: str, template_id: str, content: str) -> dict[str, Any]:
    tpl = get_template(template_id)
    text = content or ""
    lower = text.lower()

    pending_fields = len(re.findall(r"\[待填写[：:][^\]]*\]", text))
    pending_fields += len(re.findall(r"\[待填写\]", text))

    missing: list[str] = []
    for section in tpl.required_sections:
        if section.lower() not in lower and section not in text:
            missing.append(section)

    sections_ok = len(missing) == 0
    word_count = len(re.sub(r"\s+", "", text))

    score = 100
    if word_count < 400 and kind in ("nda", "sow", "contract"):
        score -= 40
    elif word_count < 200 and kind == "prd":
        score -= 30
    score -= min(len(missing) * 8, 40)
    score -= min(pending_fields * 2, 20)
    score = max(0, min(100, score))

    issues: list[str] = []
    if missing:
        issues.append(f"缺少章节：{', '.join(missing[:5])}")
    if word_count < 300 and kind == "nda":
        issues.append("NDA 篇幅过短，可能仅为提纲")
    if pending_fields > 8:
        issues.append(f"待填写项过多（{pending_fields} 处）")

    status = "draft"
    if score >= 75 and sections_ok:
        status = "review"
    if score < 50:
        status = "draft"

    return {
        "score": score,
        "status": status,
        "sectionsOk": sections_ok,
        "missingSections": missing,
        "pendingFields": pending_fields,
        "wordCount": word_count,
        "issues": issues,
    }
