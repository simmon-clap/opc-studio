"""CEO review loop tests."""

from app.orchestrator.ceo_review import MAX_REVISION_ROUNDS, review_artifact


def test_bullet_nda_fails_review():
    dashboard = {
        "founderProfile": {
            "deliverables": {"legal": {"rejectBulletDraft": True}},
        }
    }
    art = {
        "id": "art-1",
        "kind": "nda",
        "templateId": "legal.nda_mutual_zh",
        "roleId": "legal",
        "title": "NDA 草稿",
        "content": "# NDA\n\n## 1. 保密\n- bullet\n## 2. 义务\n- bullet",
        "reviewNotes": [],
    }
    result = review_artifact(None, dashboard, art, project_id="lead-华为")
    assert result.action == "revision"
    assert art["status"] == "revision"


def test_escalate_after_max_rounds():
    dashboard = {"founderProfile": {}}
    art = {
        "id": "art-1",
        "kind": "nda",
        "templateId": "legal.nda_mutual_zh",
        "content": "short",
        "reviewNotes": [{"round": 1}, {"round": 2}],
    }
    result = review_artifact(None, dashboard, art, project_id="p1")
    assert result.action == "escalate"
    assert MAX_REVISION_ROUNDS == 2
