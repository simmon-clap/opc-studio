"""Aggregate recompute tests."""

from app.services.aggregates import recompute_all, recompute_role_live_state


def test_role_live_state_from_tasks():
    dashboard = {
        "projects": [
            {
                "id": "proj-x",
                "clientName": "测试客户",
                "pipelineColumn": "clarify",
                "assignees": ["product"],
            }
        ],
        "roles": [
            {
                "id": "product",
                "load": {"current": 0, "max": 2},
                "projectIds": [],
                "extras": {},
            }
        ],
        "tasks": [
            {
                "id": "t1",
                "roleId": "product",
                "projectId": "proj-x",
                "title": "撰写 PRD",
                "status": "running",
                "startedAt": "2026-05-21T12:00:00+08:00",
            },
            {
                "id": "t2",
                "roleId": "product",
                "projectId": "proj-x",
                "title": "验收 Rubric",
                "status": "pending",
            },
        ],
        "pulse": {},
        "stats": {
            "leads": {"label": "线索", "value": 0, "filter": "lead"},
            "active": {"label": "进行中", "value": 0, "filter": "active"},
            "clarify": {"label": "待澄清", "value": 0, "filter": "clarify"},
            "hitl": {"label": "待审批", "value": 0, "filter": "hitl"},
            "done": {"label": "已交付", "value": 0, "filter": "done"},
        },
    }
    recompute_all(dashboard)
    product = dashboard["roles"][0]
    assert product["workStatus"] == "working"
    assert product["runningCount"] == 1
    assert product["pendingCount"] == 1
    assert product["load"]["current"] == 2
    assert "撰写 PRD" in product["focus"]
    assert "proj-x" in product["projectIds"]


def test_legal_extras_and_focus_from_live_tasks():
    from datetime import datetime, timedelta, timezone

    recent_done = (
        datetime.now(timezone.utc).astimezone().replace(microsecond=0).isoformat(timespec="seconds")
    )
    dashboard = {
        "projects": [
            {"id": "proj-acme", "clientName": "Acme 科技", "assignees": ["legal"]},
            {"id": "lead-huawei", "clientName": "华为（线索）", "assignees": []},
        ],
        "roles": [
            {
                "id": "legal",
                "load": {"current": 0, "max": 2},
                "projectIds": ["proj-acme"],
                "extras": {
                    "quotesPending": 99,
                    "complianceFlags": ["旧 seed 数据"],
                },
            }
        ],
        "tasks": [
            {
                "id": "task-legal-1",
                "roleId": "legal",
                "projectId": "proj-acme",
                "title": "Acme 项目报价与 SOW 草案",
                "status": "pending",
                "dependsOn": ["task-product-1"],
                "waitingOn": "product",
            },
            {
                "id": "task-legal-huawei",
                "roleId": "legal",
                "projectId": "lead-huawei",
                "title": "华为 · 起草 NDA",
                "status": "done",
                "completedAt": recent_done,
                "activities": [{"at": recent_done, "message": "完成"}],
            },
        ],
        "pulse": {},
        "stats": {
            "leads": {"label": "线索", "value": 0, "filter": "lead"},
            "active": {"label": "进行中", "value": 0, "filter": "active"},
            "clarify": {"label": "待澄清", "value": 0, "filter": "clarify"},
            "hitl": {"label": "待审批", "value": 0, "filter": "hitl"},
            "done": {"label": "已交付", "value": 0, "filter": "done"},
        },
    }
    recompute_all(dashboard)
    legal = dashboard["roles"][0]
    assert "刚完成" in legal["focus"]
    assert "华为" in legal["focus"]
    assert legal["extras"]["quotesPending"] == 1
    assert any("华为" in flag for flag in legal["extras"]["complianceFlags"])
    assert legal["extras"]["taskDoneRecent"] == 1
    assert "lead-huawei" in legal["projectIds"]
