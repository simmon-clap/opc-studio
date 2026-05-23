"""Epic 3 — Skill Hub tests."""

from __future__ import annotations

SAMPLE_SKILL = """---
id: custom_brand_moodboard
name: 品牌情绪板
version: 1.0.0
category: brand
requiredCapabilities: [text]
tools: [read_project_brief, write_artifact_file]
riskLevel: medium
---

# 品牌情绪板 Skill
解析 brief 并输出情绪板 Markdown。
"""


def test_skill_catalog_bootstrapped(client):
    dash = client.get("/api/v1/dashboard").json()["data"]
    catalog = dash["skillCatalog"]
    assert len(catalog) >= 8
    assert any(s["id"] == "nda_review_v2" for s in catalog)


def test_import_skill(client):
    res = client.post("/api/v1/skills/import", json={"markdown": SAMPLE_SKILL})
    assert res.status_code == 200
    skill = res.json()["data"]
    assert skill["id"] == "custom_brand_moodboard"
    assert skill["status"] == "draft"


def test_activate_skill(client):
    client.post("/api/v1/skills/import", json={"markdown": SAMPLE_SKILL})
    res = client.post("/api/v1/skills/custom_brand_moodboard/activate")
    assert res.status_code == 200
    assert res.json()["data"]["status"] == "active"


def test_skill_route_by_task_kind(client):
    from app.presentation.skills import route_skill

    dash = client.get("/api/v1/dashboard").json()["data"]
    skill = route_skill(dash, role_id="legal", task_kind="legal.nda_review")
    assert skill is not None
    assert skill["id"] == "nda_review_v2"


def test_skill_proposal_inbox_flow(client):
    from app.db import session_scope
    from app.services.dashboard_store import mutate

    item_id = "inbox-skill-test-001"
    with session_scope() as session:
        with mutate(session) as dashboard:
            dashboard.setdefault("inbox", []).insert(
                0,
                {
                    "id": item_id,
                    "category": "skill_proposal",
                    "title": "安装 Skill：品牌情绪板",
                    "preview": SAMPLE_SKILL[:200],
                    "status": "active",
                    "proposedSkill": {"rawMarkdown": SAMPLE_SKILL},
                },
            )

    res = client.post(f"/api/v1/inbox/{item_id}/skill-install")
    assert res.status_code == 200
    assert res.json()["data"]["skillId"] == "custom_brand_moodboard"

    catalog = client.get("/api/v1/skills").json()["data"]
    imported = next(s for s in catalog if s["id"] == "custom_brand_moodboard")
    assert imported["status"] == "active"


def test_role_enabled_skills_filter(client):
    client.post("/api/v1/skills/import", json={"markdown": SAMPLE_SKILL})
    client.post("/api/v1/skills/custom_brand_moodboard/activate")
    client.post(
        "/api/v1/roles/registry",
        json={"id": "brand", "name": "品牌", "capabilities": ["text"]},
    )
    client.put(
        "/api/v1/roles/config/brand",
        json={"enabledSkills": ["custom_brand_moodboard"]},
    )
    from app.presentation.skills import route_skill

    dash = client.get("/api/v1/dashboard").json()["data"]
    skill = route_skill(
        dash,
        role_id="brand",
        task_kind="brand.moodboard",
        skill_id="custom_brand_moodboard",
    )
    assert skill is not None
