"""Weekly v2 bootstrap from mock when DB has legacy shape."""

from copy import deepcopy

from app.presentation.weekly import sync_weekly_reports


def test_bootstrap_replaces_legacy_weekly_from_mock():
    dashboard = {
        "weeklyReport": {
            "week": "2026-W20",
            "status": "sent",
            "summary": "legacy",
            "pipelineSnapshot": [{"label": "X", "progress": 1}],
            "pendingDecisions": [{"id": "d1"}],
        }
    }
    sync_weekly_reports(dashboard)
    reports = dashboard["weeklyReports"]
    assert len(reports) >= 2
    draft = next(r for r in reports if r.get("week") == "2026-W20")
    assert draft["status"] == "draft"
    assert draft.get("blocks")
    assert "pipelineSnapshot" not in draft
    assert dashboard["weeklyReport"]["status"] == "draft"


def test_bootstrap_skips_when_already_v2():
    dashboard = {
        "weeklyReports": [
            {
                "id": "2026-W20",
                "week": "2026-W20",
                "status": "draft",
                "blocks": [{"kind": "projects", "items": []}],
            }
        ]
    }
    before = deepcopy(dashboard)
    sync_weekly_reports(dashboard)
    assert dashboard["weeklyReports"][0]["blocks"] == before["weeklyReports"][0]["blocks"]
