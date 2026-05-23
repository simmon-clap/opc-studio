"""Overview live presentation tests."""

from app.services.aggregates import recompute_all
from app.services.overview_presenter import compute_overview_live


def _dashboard():
    return {
        "roles": [
            {"id": "ceo", "name": "沈策"},
            {"id": "ops", "name": "苏行"},
        ],
        "projects": [{"id": "p1", "clientName": "Beta 贸易"}],
        "tasks": [
            {
                "id": "t1",
                "roleId": "ops",
                "projectId": "p1",
                "title": "Beta · Pipeline 台账",
                "status": "running",
                "startedAt": "2026-05-23T12:00:00+08:00",
            }
        ],
        "dispatchFeed": [
            {
                "id": "df1",
                "tone": "assign",
                "speakerRole": "ceo",
                "peerRole": "ops",
                "taskId": "t1",
                "text": "苏行，Pipeline 麻烦接一下",
                "at": "2026-05-23T12:00:01+08:00",
            },
            {
                "id": "df2",
                "tone": "reply",
                "speakerRole": "ops",
                "peerRole": "ceo",
                "taskId": "t1",
                "text": "收到，我这就开始",
                "at": "2026-05-23T12:00:02+08:00",
            },
        ],
        "meta": {},
    }


def test_running_task_shows_reply_only_not_assign():
    live = compute_overview_live(_dashboard())
    assert live["version"] == 1
    tones = [d["tone"] for d in live["dialogues"]]
    assert tones == ["reply"]
    assert live["activeEdges"]
    assert live["activeEdges"][0]["fromRole"] == "ceo"


def test_recompute_all_sets_overview_live():
    dashboard = _dashboard()
    recompute_all(dashboard)
    assert "presentation" in dashboard
    assert "overviewLive" in dashboard
    assert dashboard["overviewLive"] is dashboard["presentation"]["overview"]
    assert dashboard["overviewLive"]["dialogues"]
