from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

import main
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


FIXED_TODAY = date(2026, 10, 2)


@pytest.fixture
def pinned_today(monkeypatch):
    monkeypatch.setattr(main, "today", lambda: FIXED_TODAY)
    return FIXED_TODAY


def checkin(hid, day):
    r = client.post(f"/habits/{hid}/checkin", json={"day": day.isoformat()})
    assert r.status_code == 200


def test_streak_counts_consecutive_days_across_month_boundary(pinned_today):
    hid = client.post("/habits", json={"name": "Meditate"}).json()["id"]
    # Oct 2, Oct 1, Sep 30 in a row, then a gap before Sep 28.
    for offset in (0, 1, 2, 4):
        checkin(hid, pinned_today - timedelta(days=offset))
    checkin(hid, pinned_today)  # a duplicate check-in must not inflate the streak

    r = client.get(f"/habits/{hid}/streak")
    assert r.status_code == 200
    assert r.json() == {"habit_id": hid, "streak": 3}


def test_streak_is_one_with_only_today(pinned_today):
    hid = client.post("/habits", json={"name": "Walk"}).json()["id"]
    checkin(hid, pinned_today)
    assert client.get(f"/habits/{hid}/streak").json()["streak"] == 1


def test_streak_zero_when_today_missing(pinned_today):
    hid = client.post("/habits", json={"name": "Journal"}).json()["id"]
    checkin(hid, pinned_today - timedelta(days=1))
    assert client.get(f"/habits/{hid}/streak").json()["streak"] == 0


def test_streak_ignores_future_checkins(pinned_today):
    hid = client.post("/habits", json={"name": "Run"}).json()["id"]
    checkin(hid, pinned_today + timedelta(days=1))
    checkin(hid, pinned_today)
    assert client.get(f"/habits/{hid}/streak").json()["streak"] == 1


def test_streak_zero_for_habit_without_checkins():
    hid = client.post("/habits", json={"name": "Floss"}).json()["id"]
    assert client.get(f"/habits/{hid}/streak").json() == {"habit_id": hid, "streak": 0}


def test_streak_unknown_habit_404():
    r = client.get("/habits/99999/streak")
    assert r.status_code == 404
