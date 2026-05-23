"""Finance export tests."""

def test_finance_export_xlsx(client):
    resp = client.get("/api/v1/finance/export?format=xlsx&scope=full")
    assert resp.status_code == 200
    assert "spreadsheetml" in resp.headers.get("content-type", "")
    assert len(resp.content) > 500
    assert resp.content[:2] == b"PK"
