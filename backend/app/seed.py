"""Database seeding from mock/dashboard.json."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlmodel import Session, select

from app.config import MOCK_DASHBOARD_PATH
from app.models.role_secrets import RoleSecret
from app.models.schema_version import SchemaVersion
from app.models.workflow_templates import WorkflowTemplate
from app.services.dashboard_normalize import normalize_dashboard_domains
from app.services.dashboard_store import DASHBOARD_KEY, has_dashboard, save
from app.services.project_store import sync_artifacts_from_dashboard

ACME_WORKFLOW = {
    "id": "wf-acme-default",
    "name": "Acme 5-Stage Delivery",
    "projectType": "agent_delivery",
    "isDefault": True,
    "transitions": [
        {"from": "lead", "to": "clarify", "stage": "阶段1 · 线索"},
        {"from": "clarify", "to": "active", "stage": "阶段2 · 评估立项", "hitl": "HITL-1"},
        {"from": "active", "to": "active", "stage": "阶段3 · 方案签约", "hitl": "HITL-2"},
        {"from": "active", "to": "active", "stage": "阶段4 · 开发交付", "hitl": "HITL-3"},
        {"from": "active", "to": "done", "stage": "阶段5 · 结项交付", "hitl": "HITL-4"},
    ],
}


def seed_if_needed(session: Session) -> None:
    if not session.exec(select(SchemaVersion)).first():
        session.add(SchemaVersion(version=1))
        session.commit()

    if not has_dashboard(session):
        dashboard = _load_mock_dashboard()
        normalize_dashboard_domains(dashboard)
        save(session, dashboard)
        sync_artifacts_from_dashboard(dashboard)

    _seed_role_secrets(session)
    _seed_workflow_templates(session)


def _load_mock_dashboard() -> dict:
    with MOCK_DASHBOARD_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def _seed_role_secrets(session: Session) -> None:
    from app.services.dashboard_store import load

    dashboard = load(session)
    now = datetime.now(timezone.utc)
    for cfg in dashboard.get("roleConfig", []):
        role_id = cfg.get("roleId")
        if not role_id:
            continue
        existing = session.get(RoleSecret, role_id)
        if existing:
            continue
        session.add(
            RoleSecret(
                role_id=role_id,
                api_base_url=cfg.get("apiBaseUrl", "https://openrouter.ai/api/v1"),
                api_key_encrypted=None,
                updated_at=now,
            )
        )
    session.commit()


def _seed_workflow_templates(session: Session) -> None:
    if session.get(WorkflowTemplate, ACME_WORKFLOW["id"]):
        return
    session.add(
        WorkflowTemplate(
            id=ACME_WORKFLOW["id"],
            name=ACME_WORKFLOW["name"],
            project_type=ACME_WORKFLOW["projectType"],
            transitions_json=json.dumps(ACME_WORKFLOW["transitions"], ensure_ascii=False),
            is_default=ACME_WORKFLOW["isDefault"],
        )
    )
    session.commit()
