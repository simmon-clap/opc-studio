"""Founder profile suggestion tests."""

from app.services.founder_profile import (
    adopt_suggestion,
    compose_profile_document,
    get_profile,
    profile_summary_for_prompt,
    suggest_profile_delta,
    update_profile,
)


def test_profile_update():
    dashboard: dict = {}
    update_profile(dashboard, {"communication": {"preferConcise": True}})
    assert get_profile(dashboard)["communication"]["preferConcise"] is True
    assert "Founder Profile" in get_profile(dashboard)["document"]


def test_profile_document_save():
    dashboard: dict = {}
    custom = "# Founder Profile\n\n## 沟通\n- 只说结论\n"
    update_profile(dashboard, {"document": custom})
    assert get_profile(dashboard)["document"] == custom
    assert profile_summary_for_prompt(dashboard).strip() == custom.strip()


def test_suggestion_requires_adopt():
    dashboard: dict = {"inbox": [], "profileSuggestions": []}
    sug = suggest_profile_delta(dashboard, note="偏好双向 NDA", source="test")
    assert sug["status"] == "pending"
    assert dashboard["inbox"]
    adopt_suggestion(dashboard, sug["id"])
    assert sug["status"] == "adopted"
    profile = get_profile(dashboard)
    notes = profile.get("learnedNotes") or []
    assert notes and "双向" in notes[0]["note"]
    assert "双向" in profile["document"]


def test_compose_profile_document():
    doc = compose_profile_document(
        {
            "communication": {"preferConcise": True, "maxReplySentences": 6},
            "deliverables": {"legal": {"preferMutualNdaTemplate": True}},
            "escalation": {"alwaysHitlFor": ["contract"]},
            "learnedNotes": [{"note": "先报价再开工"}],
        }
    )
    assert "6 句" in doc
    assert "先报价再开工" in doc
