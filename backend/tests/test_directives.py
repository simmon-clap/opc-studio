"""Role directive detection tests."""

from app.orchestrator.directives import detect_role_directives


def test_detect_legal_nda_directive():
    text = "你让法务先起草个 NDA 给我，项目涉及到保密了"
    directives = detect_role_directives(text)
    assert any(d.role_id == "legal" and d.kind == "nda" for d in directives)


def test_detect_legal_nda_followup():
    text = "法务开始就 NDA 写一下，后面还有跟进的事情，写好了发我"
    directives = detect_role_directives(text)
    assert any(d.role_id == "legal" for d in directives)


def test_detect_ops_and_legal_huawei():
    text = "让运营记录下，和华为有合作，法务先起草 NDA"
    directives = detect_role_directives(text)
    roles = {d.role_id for d in directives}
    assert "legal" in roles
    assert "ops" in roles
