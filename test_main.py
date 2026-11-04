from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_create_and_list_habit():
    r = client.post("/habits", json={"name": "Read 20 minutes"})
    assert r.status_code == 200
    hid = r.json()["id"]
    r2 = client.get("/habits")
    assert r2.status_code == 200
    assert any(h["id"] == hid for h in r2.json())


def test_create_habit_rejects_empty_name():
    for bad_name in ["", "   "]:
        r = client.post("/habits", json={"name": bad_name})
        assert r.status_code == 422
        detail = r.json()["detail"]
        assert any("habit name must not be empty" in err["msg"] for err in detail)


def test_checkin_flow():
    hid = client.post("/habits", json={"name": "Stretch"}).json()["id"]
    r = client.post(f"/habits/{hid}/checkin", json={"day": "2026-09-22"})
    assert r.status_code == 200
    r2 = client.get(f"/habits/{hid}/checkins")
    assert r2.json() == ["2026-09-22"]


def test_checkin_rejects_malformed_day():
    hid = client.post("/habits", json={"name": "Meditation"}).json()["id"]
    for bad_day in ["", "not-a-date", "2026/09/22", "22-09-2026", "2026-02-30", "20260922"]:
        r = client.post(f"/habits/{hid}/checkin", json={"day": bad_day})
        assert r.status_code == 422
        detail = r.json()["detail"]
        assert any("day must be a valid ISO date (YYYY-MM-DD)" in err["msg"] for err in detail)


def test_checkin_unknown_habit_404():
    r = client.post("/habits/99999/checkin", json={"day": "2026-09-22"})
    assert r.status_code == 404
