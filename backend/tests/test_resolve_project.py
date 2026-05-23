"""Project resolution from CEO thread context."""

from app.services.intake_service import resolve_project_id


def _dashboard_huawei_thread() -> dict:
    return {
        "clients": [
            {"name": "华为", "projectIds": ["lead-华为"]},
            {"name": "可口可乐", "projectIds": ["lead-可口可乐"]},
        ],
        "projects": [
            {"id": "lead-可口可乐", "pipelineColumn": "lead"},
            {"id": "lead-华为", "pipelineColumn": "clarify"},
        ],
        "artifacts": [
            {
                "id": "art-nda-4b3dfd",
                "projectId": "lead-华为",
                "title": "NDA 草稿",
                "kind": None,
            }
        ],
        "ceoThread": [
            {
                "direction": "founder_to_ceo",
                "text": "和华为是项目上的合作，保密是两边都有，双向的。",
            },
            {
                "direction": "ceo_to_founder",
                "text": "收到，华为的项目合作、双向保密我记准了。这就让法务重新起草 NDA。",
            },
            {"direction": "founder_to_ceo", "text": "NDA 没有更新，重新生成一份专业的双向 NDA"},
        ],
    }


def test_resolve_nda_followup_to_huawei_not_first_lead():
    dashboard = _dashboard_huawei_thread()
    pid = resolve_project_id(
        dashboard, "NDA 没有更新，重新生成一份专业的双向 NDA", "proj-beta"
    )
    assert pid == "lead-华为"


def test_resolve_nda_via_artifact_when_thread_has_no_client_name():
    dashboard = {
        "clients": [{"name": "可口可乐", "projectIds": ["lead-可口可乐"]}],
        "projects": [{"id": "lead-可口可乐", "pipelineColumn": "lead"}],
        "artifacts": [
            {"id": "art-nda-x", "projectId": "lead-华为", "title": "保密协议", "kind": "nda"}
        ],
        "ceoThread": [{"direction": "founder_to_ceo", "text": "NDA 还没更新"}],
    }
    assert resolve_project_id(dashboard, "NDA 还没更新", "proj-beta") == "lead-华为"
