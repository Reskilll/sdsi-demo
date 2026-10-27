"""M5: weekly recurring bookings with per-occurrence conflict reports."""
from conftest import make_booking


def test_recurring_created(client):
    r = client.post("/bookings", json=make_booking(recurrence={"count": 3}))
    assert r.status_code == 201
    assert r.json()["recurrence"]["count"] == 3


def test_recurring_conflict_reported_per_occurrence(client):
    # Occurs 09:00-10:00 on Nov 2, 9, 16.
    client.post("/bookings", json=make_booking(recurrence={"count": 3}))
    # Single clash on the 2nd occurrence (Nov 9).
    r = client.post(
        "/bookings",
        json=make_booking(start="2026-11-09T09:00:00", end="2026-11-09T10:00:00"),
    )
    assert r.status_code == 409
    conflicts = r.json()["detail"]["conflicts"]
    assert any(c["occurrence_start"].startswith("2026-11-09") for c in conflicts)


def test_recurring_against_recurring_per_occurrence(client):
    # Series A: Mon 09:00. Series B: starts one week later at 09:00 → clashes at overlap point.
    client.post("/bookings", json=make_booking(recurrence={"count": 4}))
    r = client.post("/bookings", json=make_booking(
        start="2026-11-09T09:00:00", end="2026-11-09T10:00:00", recurrence={"count": 2}))
    assert r.status_code == 409


def test_recurring_until(client):
    r = client.post("/bookings", json=make_booking(recurrence={"until": "2026-11-16T09:00:00"}))
    assert r.status_code == 201


def test_recurrence_requires_one_of_count_or_until(client):
    assert client.post("/bookings", json=make_booking(recurrence={})).status_code == 422
    assert client.post(
        "/bookings",
        json=make_booking(recurrence={"count": 2, "until": "2026-11-16T09:00:00"}),
    ).status_code == 422