from datetime import date, timedelta

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


def test_checkin_flow():
    hid = client.post("/habits", json={"name": "Stretch"}).json()["id"]
    r = client.post(f"/habits/{hid}/checkin", json={"day": "2026-09-22"})
    assert r.status_code == 200
    r2 = client.get(f"/habits/{hid}/checkins")
    assert r2.json() == ["2026-09-22"]


def test_checkin_unknown_habit_404():
    r = client.post("/habits/99999/checkin", json={"day": "2026-09-22"})
    assert r.status_code == 404


def test_streak_consecutive_days():
    hid = client.post("/habits", json={"name": "Meditate"}).json()["id"]
    today = date.today()
    for offset in (0, 1, 2, 4):
        day_str = (today - timedelta(days=offset)).isoformat()
        client.post(f"/habits/{hid}/checkin", json={"day": day_str})
    # Duplicate check-in on today should not inflate streak
    client.post(f"/habits/{hid}/checkin", json={"day": today.isoformat()})

    r = client.get(f"/habits/{hid}/streak")
    assert r.status_code == 200
    assert r.json() == {"habit_id": hid, "streak": 3}


def test_streak_zero_when_missing_today():
    hid = client.post("/habits", json={"name": "Journal"}).json()["id"]
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    client.post(f"/habits/{hid}/checkin", json={"day": yesterday})

    r = client.get(f"/habits/{hid}/streak")
    assert r.status_code == 200
    assert r.json() == {"habit_id": hid, "streak": 0}


def test_streak_unknown_habit_404():
    r = client.get("/habits/99999/streak")
    assert r.status_code == 404
