"""Brief classification tests."""

from app.orchestrator.transitions import (
    is_casual_message,
    is_complete_brief,
    is_intake_request,
    is_vague_brief,
    is_workflow_command,
    should_enter_workflow,
)


def test_halo_is_casual_not_vague():
    assert is_casual_message("halo")
    assert not is_vague_brief("halo")
    assert not should_enter_workflow("halo")


def test_hello_is_casual():
    assert is_casual_message("你好")
    assert not is_vague_brief("你好")
    assert not should_enter_workflow("你好")


def test_vague_business_brief_chat_only():
    assert not is_casual_message("做个系统")
    assert is_vague_brief("做个系统")
    assert not should_enter_workflow("做个系统")


def test_intake_alone_does_not_trigger_workflow():
    text = "客户是可口可乐，装瓶厂数据分析，纳入 Pipeline 并记录好"
    assert is_intake_request(text)
    assert not should_enter_workflow(text, intake_created=True)


def test_workflow_command_on_vague():
    assert is_workflow_command("做个系统，安排立项")
    assert should_enter_workflow("做个系统，安排立项")


def test_nda_directive_triggers_workflow():
    text = "法务开始就 NDA 写一下，写好了发我"
    assert should_enter_workflow(text)


def test_clear_brief_not_vague():
    text = "Beta 贸易想做发票 OCR，预算 8-10 万，验收准确率 95%，先 PoC"
    assert not is_casual_message(text)
    assert not is_vague_brief(text)
    assert is_complete_brief(text)
    assert should_enter_workflow(text)
