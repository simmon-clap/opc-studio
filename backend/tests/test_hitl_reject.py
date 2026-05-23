def test_hitl_reject(client):
    before = len(client.get("/api/v1/reject-history").json()["data"])
    response = client.post(
        "/api/v1/hitl/hitl-3-acme/reject",
        json={"note": "报价区间需下调 10%"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["note"] == "报价区间需下调 10%"

    history = client.get("/api/v1/reject-history").json()["data"]
    assert len(history) == before + 1
    assert history[0]["hitlId"] == "hitl-3-acme"
    assert history[0]["note"] == "报价区间需下调 10%"

    dashboard = client.get("/api/v1/dashboard").json()["data"]
    inbox = next(i for i in dashboard["inbox"] if i.get("hitlId") == "hitl-3-acme")
    assert inbox["status"] == "done"
    assert inbox["resolution"] == "rejected"
