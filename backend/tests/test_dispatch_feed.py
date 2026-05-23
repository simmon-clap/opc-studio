"""Dispatch feed tests."""

from app.services.dispatch_feed import (
    bootstrap_dispatch_feed,
    compose_assign_dialogue,
    compose_deliver_dialogue,
    compose_reply_dialogue,
    is_dispatch_item_consistent,
    log_accept,
    log_assign,
    log_complete,
    log_task_failed,
    sync_dispatch_feed,
)


def test_assign_dialogue_is_conversational():
    dashboard = {
        "roles": [{"id": "ceo", "name": "沈策"}, {"id": "legal", "name": "唐律"}],
        "projects": [{"id": "p1", "clientName": "华为（线索）"}],
        "dispatchFeed": [],
    }
    log_assign(
        dashboard,
        to_role="legal",
        title="华为 · 起草 NDA",
        project_id="p1",
        task_id="task-legal-1",
    )
    item = dashboard["dispatchFeed"][0]
    assert item["tone"] == "assign"
    assert item["speakerRole"] == "ceo"
    assert "唐律" in item["text"]
    assert "华为" in item["text"]
    assert "NDA" in item["text"]
    assert "派活" not in item["text"]
    assert "接单" not in item["text"]


def test_reply_and_deliver_dialogue():
    dashboard = {
        "roles": [{"id": "legal", "name": "唐律"}],
        "projects": [{"id": "p1", "clientName": "华为"}],
        "dispatchFeed": [],
    }
    task = {"id": "task-legal-1", "title": "华为 · 起草 NDA"}
    log_accept(dashboard, role_id="legal", task=task, project_id="p1")
    reply = dashboard["dispatchFeed"][0]
    assert reply["tone"] == "reply"
    assert reply["speakerRole"] == "legal"
    assert "收到" in reply["text"] or "明白" in reply["text"] or "OK" in reply["text"]

    from app.services.dispatch_feed import log_complete

    log_complete(
        dashboard,
        role_id="legal",
        task=task,
        project_id="p1",
        note="条款已按双向模板补齐",
    )
    deliver = dashboard["dispatchFeed"][0]
    assert deliver["tone"] == "deliver"
    assert "NDA" in deliver["text"] or "起草" in deliver["text"]


def test_feed_hides_stale_lines_when_task_advances():
    dashboard = {
        "roles": [
            {"id": "ceo", "name": "沈策"},
            {"id": "legal", "name": "唐律"},
        ],
        "projects": [{"id": "p1", "clientName": "华为"}],
        "dispatchFeed": [],
        "tasks": [
            {
                "id": "task-legal-1",
                "roleId": "legal",
                "projectId": "p1",
                "title": "华为 · 起草 NDA",
                "status": "done",
                "activities": [{"message": "条款已补齐"}],
            }
        ],
    }
    log_assign(
        dashboard,
        to_role="legal",
        title="华为 · 起草 NDA",
        project_id="p1",
        task_id="task-legal-1",
    )
    log_accept(
        dashboard,
        role_id="legal",
        task={"id": "task-legal-1", "title": "华为 · 起草 NDA"},
        project_id="p1",
    )
    assign = dashboard["dispatchFeed"][-1]
    reply = dashboard["dispatchFeed"][-2]
    assert is_dispatch_item_consistent(dashboard, assign) is False
    assert is_dispatch_item_consistent(dashboard, reply) is False

    log_complete(
        dashboard,
        role_id="legal",
        task=dashboard["tasks"][0],
        project_id="p1",
        note="条款已补齐",
    )
    deliver = dashboard["dispatchFeed"][0]
    assert is_dispatch_item_consistent(dashboard, deliver) is True


def test_failed_task_shows_fail_not_deliver():
    dashboard = {
        "roles": [{"id": "legal", "name": "唐律"}],
        "projects": [{"id": "p1", "clientName": "华为"}],
        "dispatchFeed": [],
        "tasks": [
            {
                "id": "task-legal-2",
                "roleId": "legal",
                "projectId": "p1",
                "title": "华为 · 合同审查",
                "status": "done",
                "activities": [{"message": "失败：LLM 超时"}],
            }
        ],
    }
    task = dashboard["tasks"][0]
    log_task_failed(
        dashboard,
        role_id="legal",
        task=task,
        project_id="p1",
        reason="LLM 超时",
    )
    fail = dashboard["dispatchFeed"][0]
    assert fail["tone"] == "fail"
    assert is_dispatch_item_consistent(dashboard, fail) is True
    assert log_complete(dashboard, role_id="legal", task=task, project_id="p1") is None


def test_sync_migrates_legacy_feed_rows():
    dashboard = {
        "roles": [{"id": "product", "name": "林知"}],
        "projects": [{"id": "p1", "clientName": "Acme"}],
        "dispatchFeed": [
            {
                "id": "old-1",
                "kind": "assign",
                "fromRole": "ceo",
                "toRole": "product",
                "message": "林知，PRD 麻烦接一下",
                "taskId": "t1",
                "projectId": "p1",
                "at": "2026-01-01T10:00:00+08:00",
            }
        ],
        "tasks": [
            {
                "id": "t1",
                "roleId": "product",
                "projectId": "p1",
                "title": "Acme · PRD",
                "status": "running",
            }
        ],
    }
    sync_dispatch_feed(dashboard)
    tones = {item["tone"] for item in dashboard["dispatchFeed"]}
    assert "assign" in tones
    assign_item = next(i for i in dashboard["dispatchFeed"] if i["tone"] == "assign")
    assert assign_item["text"] == "林知，PRD 麻烦接一下"
    assert is_dispatch_item_consistent(dashboard, assign_item) is True


def test_compose_helpers():
    dashboard = {
        "roles": [{"id": "product", "name": "林知"}],
        "projects": [{"id": "p1", "clientName": "Acme"}],
    }
    assign = compose_assign_dialogue(
        dashboard,
        from_role="ceo",
        to_role="product",
        title="Acme · PRD",
        project_id="p1",
        task_id="t1",
    )
    assert "林知" in assign and "PRD" in assign
    reply = compose_reply_dialogue(
        dashboard, role_id="product", title="Acme · PRD", task_id="t1"
    )
    assert "PRD" in reply
    deliver = compose_deliver_dialogue(
        dashboard,
        role_id="product",
        title="Acme · PRD",
        note="验收标准已写进文档",
        task_id="t1",
    )
    assert "PRD" in deliver


def test_bootstrap_from_tasks():
    dashboard: dict = {
        "roles": [{"id": "product", "name": "林知"}],
        "projects": [{"id": "p1", "clientName": "Acme"}],
        "dispatchFeed": [],
        "tasks": [
            {
                "id": "t1",
                "roleId": "product",
                "projectId": "p1",
                "title": "Acme · PRD",
                "status": "running",
            }
        ],
    }
    bootstrap_dispatch_feed(dashboard)
    assert len(dashboard["dispatchFeed"]) >= 2
    assert all("text" in item for item in dashboard["dispatchFeed"])
    assert all(is_dispatch_item_consistent(dashboard, item) for item in dashboard["dispatchFeed"])
