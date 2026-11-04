import pytest
from fastapi.testclient import TestClient

from main import BAD_DAY_MESSAGE, app

client = TestClient(app)


def test_create_and_list_habit():
    r = client.post("/habits", json={"name": "Read 20 minutes"})
    assert r.status_code == 200
    hid = r.json()["id"]
    r2 = client.get("/habits")
    assert r2.status_code == 200
    assert any(h["id"] == hid for h in r2.json())


@pytest.mark.parametrize("bad_name", ["", "   ", "\t\n"])
def test_create_habit_rejects_empty_name(bad_name):
    r = client.post("/habits", json={"name": bad_name})
    assert r.status_code == 422
    assert any("habit name must not be empty" in err["msg"] for err in r.json()["detail"])


def test_create_habit_trims_name():
    r = client.post("/habits", json={"name": "  Read 20 minutes  "})
    assert r.status_code == 200
    assert r.json()["name"] == "Read 20 minutes"
    stored = [h for h in client.get("/habits").json() if h["id"] == r.json()["id"]]
    assert stored == [{"id": r.json()["id"], "name": "Read 20 minutes"}]


def test_checkin_flow():
    hid = client.post("/habits", json={"name": "Stretch"}).json()["id"]
    r = client.post(f"/habits/{hid}/checkin", json={"day": "2026-09-22"})
    assert r.status_code == 200
    r2 = client.get(f"/habits/{hid}/checkins")
    assert r2.json() == ["2026-09-22"]


@pytest.mark.parametrize(
    "bad_day",
    [
        "",
        "not-a-date",
        "2026/09/22",
        "22-09-2026",
        "2026-02-30",
        "2026-9-22",
        "20260922",  # accepted by date.fromisoformat on 3.11+, but not YYYY-MM-DD
        "2026-W39-2",  # ISO week date, same
        " 2026-09-22",
    ],
)
def test_checkin_rejects_malformed_day(bad_day):
    hid = client.post("/habits", json={"name": "Meditation"}).json()["id"]
    r = client.post(f"/habits/{hid}/checkin", json={"day": bad_day})
    assert r.status_code == 422
    assert any(BAD_DAY_MESSAGE in err["msg"] for err in r.json()["detail"])


def test_checkin_accepts_leap_day():
    hid = client.post("/habits", json={"name": "Leap"}).json()["id"]
    r = client.post(f"/habits/{hid}/checkin", json={"day": "2028-02-29"})
    assert r.status_code == 200
    assert client.get(f"/habits/{hid}/checkins").json() == ["2028-02-29"]


def test_checkin_unknown_habit_404():
    r = client.post("/habits/99999/checkin", json={"day": "2026-09-22"})
    assert r.status_code == 404
