"""Finance v2 API tests."""

def test_finance_summary(client):
    resp = client.get("/api/v1/finance/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    data = body["data"]
    assert data["periodType"] in ("month", "quarter")
    assert "statement" in data
    assert "revenue" in data["statement"]


def test_finance_projects(client):
    resp = client.get("/api/v1/finance/projects")
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    assert "health" in items[0]
    assert "advisory" in items[0]


def test_finance_project_detail(client):
    resp = client.get("/api/v1/finance/projects/proj-acme")
    assert resp.status_code == 200
    row = resp.json()["data"]
    assert row["projectId"] == "proj-acme"
    assert row.get("byRole")
    assert row.get("costBreakdown")


def test_finance_period_quarter(client):
    resp = client.patch("/api/v1/finance/period", json={"periodType": "quarter", "period": "2026-Q2"})
    assert resp.status_code == 200
    finance = resp.json()["data"]["finance"]
    assert finance["periodType"] == "quarter"
    assert finance["period"] == "2026-Q2"

    dash = client.get("/api/v1/dashboard").json()["data"]
    assert dash["costs"]["periodType"] == "quarter"

    client.patch("/api/v1/finance/period", json={"periodType": "month", "period": "2026-05"})


def test_finance_patch_project_tax(client):
    resp = client.patch(
        "/api/v1/finance/projects/proj-acme",
        json={"costBreakdown": {"tax": 120}, "advisory": "法务已录入税费", "advisorySource": "legal"},
    )
    assert resp.status_code == 200
    row = resp.json()["data"]["project"]
    assert row["costBreakdown"]["tax"] == 120
    assert row["advisorySource"] == "legal"
