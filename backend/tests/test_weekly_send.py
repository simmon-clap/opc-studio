def test_weekly_send(client):
    response = client.post("/api/v1/weekly/current/send")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["weeklyReport"]["status"] == "sent"

    dashboard = client.get("/api/v1/dashboard").json()["data"]
    assert dashboard["weeklyReport"]["status"] == "sent"
    weekly_inbox = [i for i in dashboard["inbox"] if i.get("weeklyReportId")]
    assert weekly_inbox
    assert all(i["status"] == "done" and i["read"] is True for i in weekly_inbox)

    ceo = next(r for r in dashboard["roles"] if r["id"] == "ceo")
    assert ceo["extras"]["reportStatus"] == "本周周报已发送"

    again = client.post("/api/v1/weekly/current/send")
    assert again.status_code == 409
