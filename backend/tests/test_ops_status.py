"""Operational status summary tests."""

from app.services.ops_status import is_status_query, summarize_active_work


def test_is_status_query():
    assert is_status_query("我们现在有哪些任务在进行？")
    assert is_status_query("团队在做什么")
    assert not is_status_query("让法务写 NDA")


def test_summarize_active_work():
    dashboard = {
        "roles": [
            {"id": "legal", "name": "唐律"},
            {"id": "product", "name": "林知"},
        ],
        "projects": [
            {"id": "p1", "clientName": "华为（线索）"},
            {"id": "p2", "clientName": "Acme 科技"},
        ],
        "tasks": [
            {
                "id": "t1",
                "roleId": "legal",
                "projectId": "p1",
                "title": "华为 · 起草 NDA",
                "status": "running",
            },
            {
                "id": "t2",
                "roleId": "product",
                "projectId": "p2",
                "title": "Acme · PRD",
                "status": "pending",
            },
        ],
        "meta": {},
    }
    text = summarize_active_work(dashboard)
    assert "1" in text and "执行" in text
    assert "唐律" in text or "法务" in text
    assert "华为" in text
    assert "Acme" in text
