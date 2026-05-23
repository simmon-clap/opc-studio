"""Deliverable system tests."""

from app.deliverables.kinds import migrate_legacy_artifact, resolve_deliverable
from app.deliverables.templates import build_generation_prompt, get_template
from app.deliverables.validator import validate_content


def test_resolve_nda_from_directive():
    spec = resolve_deliverable("legal", "华为 · 起草 NDA", directive_kind="nda")
    assert spec.kind == "nda"
    assert spec.viewer == "contract"
    assert spec.template_id == "legal.nda_mutual_zh"


def test_nda_template_has_required_structure():
    tpl = get_template("legal.nda_mutual_zh")
    assert "签章" in tpl.skeleton
    assert "保密信息" in tpl.skeleton
    prompt, max_tokens, temp = build_generation_prompt(
        resolve_deliverable("legal", "起草 NDA", directive_kind="nda"),
        project_id="lead-x",
        client="华为",
        task_title="起草 NDA",
        context="需要双向 NDA",
    )
    assert "保密协议" in prompt
    assert max_tokens >= 5000


def test_nda_skeleton_scores_as_draft_not_empty():
    tpl = get_template("legal.nda_mutual_zh")
    q = validate_content("nda", tpl.template_id, tpl.skeleton)
    assert q["wordCount"] > 300
    assert q["score"] >= 50


def test_migrate_legacy_artifact_adds_kind():
    art = {"id": "a1", "type": "doc", "title": "NDA 草稿", "content": "# NDA"}
    migrate_legacy_artifact(art)
    assert art["kind"] == "nda"
    assert art["viewer"] == "contract"
    assert art["format"] == "markdown"
