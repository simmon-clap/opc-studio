"""Artifact versioning and workflow tests."""

from app.services.artifact_versions import append_version, bump_version, diff_versions, init_version
from app.services.artifact_workflow import approve_artifact, maybe_submit_artifact_review


def test_bump_version():
    assert bump_version("0.1") == "0.2"
    assert bump_version("1.3") == "1.4"


def test_init_and_diff_versions():
    art = {"id": "art-1", "version": "0.1", "roleId": "legal"}
    init_version(art, "# v1\n\n内容A", author="legal", project_id="proj-x")
    assert len(art["versions"]) == 1

    append_version(
        art, "# v2\n\n内容B", author="legal", note="修订", project_id="proj-x"
    )
    assert art["version"] == "0.2"
    diff = diff_versions("proj-x", "art-1", "0.1", "0.2")
    assert diff["added"] >= 1


def test_maybe_submit_artifact_review_creates_hitl():
    dashboard = {
        "projects": [{"id": "lead-x", "clientName": "测试（线索）"}],
        "artifacts": [],
        "hitlQueue": [],
        "inbox": [],
    }
    art = {
        "id": "art-nda-1",
        "kind": "nda",
        "title": "NDA 草稿",
        "roleId": "legal",
        "version": "0.1",
        "content": "# NDA\n\n" + ("条款 " * 100),
        "quality": {"score": 80},
    }
    result = maybe_submit_artifact_review(dashboard, art, "lead-x")
    assert result is not None
    assert art["status"] == "review"
    assert art["hitlId"]
    assert any(h["type"] == "HITL-Artifact" for h in dashboard["hitlQueue"])
    assert any(i["category"] == "approval" for i in dashboard["inbox"])


def test_approve_artifact():
    dashboard = {
        "artifacts": [
            {"id": "a1", "status": "review", "hitlId": "hitl-art-1"}
        ],
        "hitlQueue": [{"id": "hitl-art-1", "artifactId": "a1"}],
        "inbox": [{"hitlId": "hitl-art-1", "status": "active"}],
    }
    approve_artifact(dashboard, "a1", hitl_id="hitl-art-1")
    assert dashboard["artifacts"][0]["status"] == "approved"
