"""CEO brief state machine tests."""

from app.services.state_machines import submit_ceo_brief


def test_submit_ceo_brief_appends_messages():
    dashboard = {"ceoThread": []}
    result = submit_ceo_brief(dashboard, "测试消息")
    assert len(dashboard["ceoThread"]) == 2
    assert dashboard["ceoThread"][0]["text"] == "测试消息"
    assert dashboard["ceoThread"][1]["type"] == "ack"
    assert len(result["messages"]) == 2
