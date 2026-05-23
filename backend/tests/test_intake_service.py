"""Intake service tests."""

from app.services.intake_service import extract_client_name, process_intake


def test_extract_coca_cola():
    text = "客户是可口可乐，他们要统计装瓶厂数据，这个需求纳入一下，把客户也记录好"
    assert extract_client_name(text) == "可口可乐"


def test_extract_huawei():
    text = "和华为有合作，需要先签 NDA，让运营记录下"
    assert extract_client_name(text) == "华为"


def test_intake_creates_client_and_project():
    dashboard = {"clients": [], "projects": [], "inbox": [], "alerts": [], "costs": {"byProject": []}}
    text = "客户是可口可乐，装瓶厂数据分析，纳入 Pipeline 并记录好"
    result = process_intake(dashboard, text)
    assert result is not None
    assert result["created"] is True
    assert any(c["name"] == "可口可乐" for c in dashboard["clients"])
    assert any(p["id"] == result["projectId"] for p in dashboard["projects"])
    assert dashboard["inbox"]
