"""Project PATCH and brief edit tests."""


def test_patch_project_priority_syncs_tasks_and_notifies_ceo(client):
    before = client.get("/api/v1/dashboard").json()["data"]
    acme = next(p for p in before["projects"] if p["id"] == "proj-acme")
    old_priority = acme["priority"]

    res = client.patch("/api/v1/projects/proj-acme", json={"priority": "P0"})
    assert res.status_code == 200
    body = res.json()["data"]
    assert body["priorityChanged"] is True
    assert body["tasksUpdated"] >= 1

    dash = client.get("/api/v1/dashboard").json()["data"]
    acme = next(p for p in dash["projects"] if p["id"] == "proj-acme")
    assert acme["priority"] == "P0"
    acme_tasks = [t for t in dash["tasks"] if t["projectId"] == "proj-acme" and t["status"] in {"running", "pending", "blocked"}]
    assert all(t["priority"] == "P0" for t in acme_tasks)

    inbox_hit = next(
        (i for i in dash["inbox"] if i.get("projectId") == "proj-acme" and "优先级" in (i.get("title") or "")),
        None,
    )
    assert inbox_hit is not None
    assert inbox_hit["category"] == "request"

    client.patch("/api/v1/projects/proj-acme", json={"priority": old_priority})


def test_patch_project_brief(client):
    res = client.patch(
        "/api/v1/projects/proj-acme/brief",
        json={"openQuestions": ["新待确认项？"], "scope": "审批流 Agent PoC"},
    )
    assert res.status_code == 200
    brief = res.json()["data"]["brief"]
    assert brief["openQuestions"] == ["新待确认项？"]
    assert brief["scope"] == "审批流 Agent PoC"

    workroom = client.get("/api/v1/projects/proj-acme/workroom").json()["data"]
    evaluate = next(g for g in workroom["groups"] if g["id"] == "evaluate")
    brief_fold = next(f for f in evaluate["fold"] if f["type"] == "brief")
    assert "新待确认项？" in brief_fold["openQuestions"]
