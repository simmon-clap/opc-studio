"""Register new clients / leads from CEO conversation."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.orchestrator import transitions


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _slug(name: str) -> str:
    ascii_part = re.sub(r"[^\w]+", "-", name.strip().lower()).strip("-")
    if ascii_part and len(ascii_part) >= 2:
        return ascii_part[:24]
    return hashlib.sha256(name.encode()).hexdigest()[:8]


def extract_client_name(text: str) -> str | None:
    patterns = (
        r"客户[是为：:\s]+([^，,。.\n；;]+)",
        r"和([^，,。.\n；;]{2,20})有合作",
        r"给([^，,。.\n]+?)做",
        r"([^\s，,。]{2,20})(?:公司|集团|贸易|科技)",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        name = match.group(1).strip()
        name = re.sub(r"(他们|要|想|需要|的).*$", "", name).strip()
        if len(name) >= 2 and name not in {"新", "新的", "一个", "我们"}:
            return name
    return None


def find_client_by_name(dashboard: dict[str, Any], name: str) -> dict[str, Any] | None:
    for client in dashboard.get("clients", []):
        cname = client.get("name") or ""
        if name in cname or cname in name:
            return client
    return None


def find_project(dashboard: dict[str, Any], project_id: str) -> dict[str, Any] | None:
    return next((p for p in dashboard.get("projects", []) if p.get("id") == project_id), None)


def _match_client_in_text(dashboard: dict[str, Any], haystack: str) -> str | None:
    for client in dashboard.get("clients", []):
        cname = (client.get("name") or "").strip()
        if len(cname) >= 2 and cname in haystack and client.get("projectIds"):
            return client["projectIds"][0]
    return None


def resolve_project_id(
    dashboard: dict[str, Any], text: str, fallback: str = "proj-beta"
) -> str:
    """从当前消息或最近对话推断关联项目。"""
    name = extract_client_name(text)
    if name:
        client = find_client_by_name(dashboard, name)
        if client and client.get("projectIds"):
            return client["projectIds"][0]

    matched = _match_client_in_text(dashboard, text)
    if matched:
        return matched

    for msg in reversed(dashboard.get("ceoThread", [])[-14:]):
        msg_text = msg.get("text") or ""
        matched = _match_client_in_text(dashboard, msg_text)
        if matched:
            return matched
        if msg.get("direction") != "founder_to_ceo":
            continue
        n = extract_client_name(msg_text)
        if not n:
            continue
        client = find_client_by_name(dashboard, n)
        if client and client.get("projectIds"):
            return client["projectIds"][0]

    thread_blob = "\n".join(
        (m.get("text") or "") for m in dashboard.get("ceoThread", [])[-14:]
    )
    lower = thread_blob.lower()
    if any(k in lower or k in thread_blob for k in ("nda", "保密协议", "保密")):
        for art in dashboard.get("artifacts", []):
            title = (art.get("title") or "").lower()
            if art.get("kind") == "nda" or "nda" in title or "保密" in title:
                pid = art.get("projectId")
                if pid:
                    return pid

    active = dashboard.get("meta", {}).get("activeProjectId")
    if active:
        return active

    for project in dashboard.get("projects", []):
        if project.get("pipelineColumn") == "lead":
            return project["id"]

    return fallback


def process_intake(dashboard: dict[str, Any], text: str) -> dict[str, Any] | None:
    """Create or update client + lead project when Founder asks to record a new need."""
    if not transitions.is_intake_request(text):
        return None

    client_name = extract_client_name(text)
    if not client_name:
        return None

    existing = find_client_by_name(dashboard, client_name)
    if existing:
        project_id = (existing.get("projectIds") or [None])[0]
        if project_id:
            project = find_project(dashboard, project_id)
            if project:
                project["summary"] = _merge_summary(project.get("summary", ""), text)
            existing.setdefault("notes", []).insert(
                0, {"at": _now_iso()[:10], "text": text[:120]}
            )
            return {
                "created": False,
                "clientId": existing["id"],
                "projectId": project_id,
                "clientName": existing.get("name", client_name),
                "summary": f"已更新线索 · {existing.get('name', client_name)}",
            }

    slug = _slug(client_name)
    client_id = f"client-{slug}"
    project_id = f"lead-{slug}"
    summary = text[:200]

    dashboard.setdefault("clients", []).insert(
        0,
        {
            "id": client_id,
            "name": client_name,
            "contact": "待联系",
            "industry": "待确认",
            "status": "lead",
            "projectIds": [project_id],
            "totalRevenue": 0,
            "received": 0,
            "notes": [{"at": _now_iso()[:10], "text": text[:160]}],
        },
    )

    dashboard.setdefault("projects", []).insert(
        0,
        {
            "id": project_id,
            "clientId": client_id,
            "clientName": f"{client_name}（线索）",
            "summary": summary,
            "agentDeliverable": "待产品结构化 · Agent 交付范围",
            "pipelineColumn": "lead",
            "priority": "P2",
            "stage": "阶段1 · 线索",
            "progress": 8,
            "assignees": ["ceo", "product"],
            "hitlPending": None,
        },
    )

    costs = dashboard.setdefault("costs", {})
    by_project = costs.setdefault("byProject", [])
    if not any(r.get("projectId") == project_id for r in by_project):
        by_project.append(
            {
                "projectId": project_id,
                "label": client_name,
                "tokens": 0,
                "cost": 0,
                "sharePct": 0,
                "revenue": 0,
                "received": 0,
                "margin": 0,
                "health": "pipeline",
            }
        )

    dashboard.setdefault("inbox", []).insert(
        0,
        {
            "id": f"inbox-{uuid4().hex[:8]}",
            "category": "must_read",
            "from": "ceo",
            "channel": "web",
            "title": f"新线索 · {client_name}",
            "preview": summary[:80],
            "projectId": project_id,
            "at": _now_iso(),
            "read": False,
            "status": "active",
        },
    )

    dashboard.setdefault("alerts", []).insert(
        0,
        {
            "id": f"alert-{uuid4().hex[:6]}",
            "level": "info",
            "message": f"新线索 {client_name} 已登记 Pipeline",
            "projectId": project_id,
            "roleId": "ceo",
        },
    )

    return {
        "created": True,
        "clientId": client_id,
        "projectId": project_id,
        "clientName": client_name,
        "summary": f"已登记线索 · {client_name}（{project_id}）",
    }


def _merge_summary(existing: str, text: str) -> str:
    snippet = text[:120]
    if snippet in existing:
        return existing
    return f"{existing}\n\n[更新] {snippet}" if existing else snippet
