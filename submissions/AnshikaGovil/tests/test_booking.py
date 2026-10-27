"""M1: CRUD, M3: capacity, and input validation."""
from conftest import make_booking


def test_create_and_get(client):
    r = client.post("/bookings", json=make_booking())
    assert r.status_code == 201
    bid = r.json()["id"]
    g = client.get(f"/bookings/{bid}")
    assert g.status_code == 200
    assert g.json()["room_id"] == "r1"
    assert g.json()["attendees"] == ["alice@corp.com"]


def test_list_and_filter(client):
    client.post("/bookings", json=make_booking())
    client.post("/bookings", json=make_booking(room="r2"))
    r = client.get("/bookings")
    assert r.status_code == 200
    assert len(r.json()) == 2
    r = client.get("/bookings?room_id=r2")
    assert len(r.json()) == 1
    assert r.json()[0]["room_id"] == "r2"


def test_update(client):
    bid = client.post("/bookings", json=make_booking()).json()["id"]
    r = client.put(f"/bookings/{bid}", json=make_booking(room="r2"))
    assert r.status_code == 200
    assert r.json()["room_id"] == "r2"


def test_delete(client):
    bid = client.post("/bookings", json=make_booking()).json()["id"]
    assert client.delete(f"/bookings/{bid}").status_code == 204
    assert client.get(f"/bookings/{bid}").status_code == 404


def test_capacity_exceeded(client):
    # r1 (Focus Pod) capacity = 2; 3 attendees.
    r = client.post("/bookings", json=make_booking(attendees=["a", "b", "c"]))
    assert r.status_code == 409
    assert any(c["reason"] == "capacity" for c in r.json()["detail"]["conflicts"])


def test_capacity_ok_complex_updates(client):
    client.post("/bookings", json=make_booking(room="r3", attendees=["a", "b", "c"]))
    r = client.get("/bookings")
    assert r.status_code == 200


def test_unknown_room(client):
    assert client.post("/bookings", json=make_booking(room="nope")).status_code == 404


def test_invalid_times(client):
    # start >= end
    assert client.post("/bookings", json=make_booking(end="2026-11-02T09:00:00")).status_code == 422
    # after hours (19:00)
    assert client.post("/bookings", json=make_booking(end="2026-11-02T19:00:00")).status_code == 422
    # empty attendees
    assert client.post("/bookings", json=make_booking(attendees=[])).status_code == 422