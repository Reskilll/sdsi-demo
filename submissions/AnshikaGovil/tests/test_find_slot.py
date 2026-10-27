"""M4: find-slot."""
from conftest import make_booking


def test_empty_day_returns_smallest_room_at_9am(client):
    r = client.get("/slots/find", params={"duration_mins": 60, "attendees": 1, "date": "2026-11-02"})
    assert r.status_code == 200
    body = r.json()
    assert body["room"]["id"] == "r1"  # smallest room that fits
    assert body["start"] == "2026-11-02T09:00:00"
    assert body["end"] == "2026-11-02T10:00:00"


def test_attendees_force_larger_room(client):
    r = client.get("/slots/find", params={"duration_mins": 30, "attendees": 3, "date": "2026-11-02"})
    assert r.json()["room"]["id"] == "r2"  # r1 capacity 2 < 3


def test_respects_existing_booking(client):
    client.post("/bookings", json=make_booking(room="r1", start="2026-11-02T09:00:00", end="2026-11-02T10:00:00"))
    r = client.get("/slots/find", params={"duration_mins": 60, "attendees": 1, "date": "2026-11-02"})
    # r1 busy 09-10; r2 is free from 09:00
    assert r.json()["room"]["id"] == "r2"
    assert r.json()["start"] == "2026-11-02T09:00:00"


def test_no_capacity_room(client):
    r = client.get("/slots/find", params={"duration_mins": 60, "attendees": 99, "date": "2026-11-02"})
    assert r.status_code == 404


def test_duration_exceeds_business_hours(client):
    r = client.get("/slots/find", params={"duration_mins": 600, "attendees": 1, "date": "2026-11-02"})
    assert r.status_code == 404


def test_invalid_params(client):
    assert client.get("/slots/find", params={"duration_mins": 0, "attendees": 1, "date": "2026-11-02"}).status_code == 422
    assert client.get("/slots/find", params={"duration_mins": 30, "attendees": 0, "date": "2026-11-02"}).status_code == 422