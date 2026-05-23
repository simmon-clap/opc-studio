def test_hitl_approve(client):
    response = client.post("/api/v1/hitl/hitl-3-acme/approve")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["projectId"] == "proj-acme"
    assert body["data"]["nextAction"] == "open_workroom"

    dashboard = client.get("/api/v1/dashboard").json()["data"]
    hitl = next(h for h in dashboard["hitlQueue"] if h["id"] == "hitl-3-acme")
    assert hitl["approved"] is True
    assert dashboard["pulse"]["hitlPending"] == 0
    assert dashboard["stats"]["hitl"]["value"] == 0

    acme = next(p for p in dashboard["projects"] if p["id"] == "proj-acme")
    assert acme["hitlPending"] is None
    assert acme["progress"] >= 85
    assert acme.get("progressDetail")
    assert acme["closureStatus"] == "in_closure"

    closure = dashboard["closure"]["proj-acme"]
    assert closure["status"] == "in_closure"
    hitl_item = next(x for x in closure["checklist"] if "HITL-3" in x["label"])
    assert hitl_item["done"] is True

    again = client.post("/api/v1/hitl/hitl-3-acme/approve")
    assert again.status_code == 409
