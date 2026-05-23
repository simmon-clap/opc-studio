"""Ingress document tests."""

from app.services.ingress_documents import ingest_bytes


def test_ingest_markdown():
    dashboard: dict = {"attachments": []}
    rec = ingest_bytes(
        dashboard,
        filename="notes.md",
        content=b"# Meeting\n\n- TODO: NDA for Huawei",
    )
    assert rec["id"].startswith("att-")
    assert "Meeting" in rec["extractedSummary"]
    assert dashboard["attachments"]


def test_reject_unsupported_format():
    dashboard: dict = {"attachments": []}
    try:
        ingest_bytes(dashboard, filename="x.docx", content=b"data")
        assert False, "should raise"
    except ValueError as exc:
        assert str(exc) == "UNSUPPORTED_FORMAT"
