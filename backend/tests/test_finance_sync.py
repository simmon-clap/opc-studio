"""Finance sync from payments."""

from app.presentation.finance import sync_finance


def test_sync_rollup_payments():
    dashboard = {
        "payments": [
            {"projectId": "proj-x", "amount": 10000, "status": "received", "at": "2026-05-02"},
            {"projectId": "proj-x", "amount": 5000, "status": "pending", "at": None},
        ],
        "projects": [{"id": "proj-x", "pipelineColumn": "active"}],
        "costs": {
            "period": "2026-05",
            "periodType": "month",
            "summary": {"monthlyBudget": 10000, "totalTokens": 0},
            "byProject": [
                {
                    "projectId": "proj-x",
                    "cost": 200,
                    "costBreakdown": {"token": 200, "external": 0, "tax": 0, "other": 0},
                    "byRole": [{"roleId": "dev", "tokens": 1000, "cost": 200, "runs": 1}],
                }
            ],
            "byRole": [],
            "weekly": [{"week": "2026-W20", "cost": 200}],
        },
    }
    sync_finance(dashboard)
    row = dashboard["costs"]["byProject"][0]
    assert row["received"] == 10000
    assert row["pending"] == 5000
    assert row["revenue"] == 15000
    assert row["margin"] == 14800
    assert row["health"] == "healthy"
    assert dashboard["costs"]["statement"]["revenue"] == 15000
