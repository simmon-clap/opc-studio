"""Workroom API endpoint tests."""

def test_workroom_aggregate(client):
    res = client.get("/api/v1/projects/proj-acme/workroom")
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    data = body["data"]
    assert data["header"]["projectId"] == "proj-acme"
    assert isinstance(data["groups"], list)
    assert "exportMenu" in data


def test_next_steps_focus_shape(client):
    res = client.get("/api/v1/projects/proj-acme/next-steps")
    assert res.status_code == 200
    data = res.json()["data"]
    assert "focus" in data
    assert "others" in data
    if data["focus"]:
        assert data["focus"]["type"] == "hitl"
