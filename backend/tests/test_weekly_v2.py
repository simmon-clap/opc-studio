def test_weekly_list(client):
    resp = client.get("/api/v1/weekly")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    items = body["data"]["items"]
    assert len(items) >= 1
    assert items[0].get("week")
    assert items[0].get("status") in ("draft", "sent")


def test_weekly_detail(client):
    resp = client.get("/api/v1/weekly/2026-W20")
    assert resp.status_code == 200
    report = resp.json()["data"]
    assert report["week"] == "2026-W20"
    assert report.get("blocks")
    kinds = {b["kind"] for b in report["blocks"]}
    assert "projects" in kinds
    assert "pendingDecisions" not in report
