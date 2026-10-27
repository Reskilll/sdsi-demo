"""M2: overlapping bookings rejected; back-to-back allowed."""
from conftest import make_booking


def test_overlap_rejected(client):
    client.post("/bookings", json=make_booking(start="2026-11-02T09:00:00", end="2026-11-02T10:00:00"))
    r = client.post("/bookings", json=make_booking(start="2026-11-02T09:30:00", end="2026-11-02T10:30:00"))
    assert r.status_code == 409
    assert any(c["reason"] == "overlap" for c in r.json()["detail"]["conflicts"])


def test_containment_rejected(client):
    client.post("/bookings", json=make_booking(start="2026-11-02T09:00:00", end="2026-11-02T11:00:00"))
    r = client.post("/bookings", json=make_booking(start="2026-11-02T09:30:00", end="2026-11-02T10:00:00"))
    assert r.status_code == 409


def test_back_to_back_allowed(client):
    client.post("/bookings", json=make_booking(start="2026-11-02T09:00:00", end="2026-11-02T10:00:00"))
    r = client.post("/bookings", json=make_booking(start="2026-11-02T10:00:00", end="2026-11-02T11:00:00"))
    assert r.status_code == 201


def test_different_room_no_conflict(client):
    client.post("/bookings", json=make_booking(room="r1"))
    r = client.post("/bookings", json=make_booking(room="r2"))
    assert r.status_code == 201


def test_update_self_not_conflict(client):
    bid = client.post("/bookings", json=make_booking()).json()["id"]
    r = client.put(f"/bookings/{bid}", json=make_booking(room="r1", attendees=["x"]))
    assert r.status_code == 200