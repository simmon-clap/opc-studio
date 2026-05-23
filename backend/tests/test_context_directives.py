"""Context-aware dispatch directive tests."""

from app.orchestrator.directives import (
    detect_context_directives,
    infer_directives_from_ceo_reply,
)


def _dashboard_with_nda_thread() -> dict:
    return {
        "ceoThread": [
            {
                "direction": "ceo_to_founder",
                "type": "analysis",
                "text": "华为 NDA 方向已对齐，请确认是否双向保密，确认后我让法务起草。",
            },
            {
                "direction": "founder_to_ceo",
                "type": "analysis",
                "text": "和华为是项目合作，保密两边都有，双向的。",
            },
        ],
    }


def test_context_bidirectional_nda_confirmation():
    text = "和华为是项目上的合作，保密是两边都有，双向的"
    directives = detect_context_directives(text, _dashboard_with_nda_thread(), "lead-华为")
    assert len(directives) == 1
    assert directives[0].role_id == "legal"
    assert directives[0].kind == "nda"


def test_context_stale_nda_complaint():
    dashboard = {
        "ceoThread": [
            {"direction": "founder_to_ceo", "text": "华为 NDA 写好了吗"},
            {"direction": "ceo_to_founder", "text": "我让法务起草 NDA"},
        ],
    }
    directives = detect_context_directives("NDA 没有更新，是怎么回事？", dashboard, "lead-华为")
    assert len(directives) == 1
    assert directives[0].kind == "nda"
    assert "重新" in directives[0].title


def test_context_regenerate_professional():
    dashboard = {
        "ceoThread": [
            {"direction": "founder_to_ceo", "text": "华为 NDA 太粗糙了"},
        ],
    }
    directives = detect_context_directives("重新生成一份专业的 NDA", dashboard, "lead-华为")
    assert len(directives) == 1
    assert directives[0].role_id == "legal"


def test_ceo_reply_commitment_fallback():
    reply = "不找借口。法务，现在立刻按华为项目合作、双向保密的标准重拟专业版双向NDA，今晚进工作室。"
    directives = infer_directives_from_ceo_reply(reply, "NDA 没有更新")
    assert len(directives) == 1
    assert directives[0].role_id == "legal"
    assert directives[0].kind == "nda"


def test_unrelated_chat_no_context_dispatch():
    dashboard = {"ceoThread": [{"direction": "founder_to_ceo", "text": "Beta 项目怎么样"}]}
    directives = detect_context_directives("你觉得靠谱吗", dashboard, "proj-beta")
    assert directives == []
