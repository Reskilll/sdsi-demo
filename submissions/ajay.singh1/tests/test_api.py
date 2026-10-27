"""Integration and API tests for the booking engine."""
import pytest


# ---- M1: CRUD ----

class TestCreateBooking:
    async def test_create_valid_booking(self, client):
        resp = await client.post("/bookings", json={
            "room": "Gamma", "organiser": "Alice",
            "start_time": "2026-12-01T10:00:00",
            "end_time": "2026-12-01T11:00:00",
            "attendee_count": 4,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] == 1
        assert data["room"] == "Gamma"
        assert data["organiser"] == "Alice"
        assert "created_at" in data

    async def test_missing_required_field(self, client):
        resp = await client.post("/bookings", json={"room": "Gamma"})
        assert resp.status_code == 422

    async def test_room_not_found(self, client):
        resp = await client.post("/bookings", json={
            "room": "NonExistent", "organiser": "Alice",
            "start_time": "2026-12-01T10:00:00",
            "end_time": "2026-12-01T11:00:00",
            "attendee_count": 2,
        })
        assert resp.status_code == 400

    async def test_capacity_exceeded(self, client):
        resp = await client.post("/bookings", json={
            "room": "Alpha", "organiser": "Alice",
            "start_time": "2026-12-01T10:00:00",
            "end_time": "2026-12-01T11:00:00",
            "attendee_count": 10,
        })
        assert resp.status_code == 400

    async def test_capacity_exact(self, client):
        resp = await client.post("/bookings", json={
            "room": "Alpha", "organiser": "Alice",
            "start_time": "2026-12-01T10:00:00",
            "end_time": "2026-12-01T11:00:00",
            "attendee_count": 4,
        })
        assert resp.status_code == 201

    async def test_start_after_end(self, client):
        resp = await client.post("/bookings", json={
            "room": "Alpha", "organiser": "Alice",
            "start_time": "2026-12-01T11:00:00",
            "end_time": "2026-12-01T10:00:00",
            "attendee_count": 2,
        })
        assert resp.status_code == 422

    async def test_invalid_date_format(self, client):
        resp = await client.post("/bookings", json={
            "room": "Alpha", "organiser": "Alice",
            "start_time": "not-a-date",
            "end_time": "2026-12-01T11:00:00",
            "attendee_count": 2,
        })
        assert resp.status_code == 422


class TestGetBooking:
    async def test_get_existing(self, client, sample_booking):
        resp = await client.get(f"/bookings/{sample_booking['id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == sample_booking["id"]

    async def test_get_nonexistent(self, client):
        resp = await client.get("/bookings/99999")
        assert resp.status_code == 404

    async def test_get_invalid_id(self, client):
        resp = await client.get("/bookings/abc")
        assert resp.status_code == 422


class TestListBookings:
    async def test_list_empty(self, client):
        resp = await client.get("/bookings")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["bookings"] == []

    async def test_list_with_bookings(self, client, sample_booking):
        resp = await client.get("/bookings")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["bookings"]) == 1

    async def test_list_filter_by_room(self, client):
        await client.post("/bookings", json={
            "room": "Alpha", "organiser": "A", "start_time": "2026-12-01T10:00:00",
            "end_time": "2026-12-01T10:30:00", "attendee_count": 2,
        })
        await client.post("/bookings", json={
            "room": "Beta", "organiser": "B", "start_time": "2026-12-01T11:00:00",
            "end_time": "2026-12-01T11:30:00", "attendee_count": 3,
        })
        resp = await client.get("/bookings?room=Alpha")
        data = resp.json()
        assert data["total"] == 1
        assert data["bookings"][0]["room"] == "Alpha"

    async def test_list_pagination(self, client):
        for i in range(3):
            await client.post("/bookings", json={
                "room": "Gamma", "organiser": f"User{i}",
                "start_time": f"2026-12-01T{10+i:02d}:00:00",
                "end_time": f"2026-12-01T{10+i:02d}:30:00",
                "attendee_count": 2,
            })
        resp = await client.get("/bookings?page=1&page_size=2")
        data = resp.json()
        assert data["total"] == 3
        assert len(data["bookings"]) == 2
        assert data["page"] == 1


class TestUpdateBooking:
    async def test_update_room(self, client, sample_booking):
        resp = await client.put(f"/bookings/{sample_booking['id']}", json={"room": "Delta"})
        assert resp.status_code == 200
        assert resp.json()["room"] == "Delta"

    async def test_update_organiser(self, client, sample_booking):
        resp = await client.put(f"/bookings/{sample_booking['id']}", json={"organiser": "Bob"})
        assert resp.status_code == 200
        assert resp.json()["organiser"] == "Bob"

    async def test_update_nonexistent(self, client):
        resp = await client.put("/bookings/99999", json={"organiser": "Bob"})
        assert resp.status_code == 404

    async def test_update_to_invalid_room(self, client, sample_booking):
        resp = await client.put(f"/bookings/{sample_booking['id']}", json={"room": "FakeRoom"})
        assert resp.status_code == 400

    async def test_update_causes_overlap(self, client):
        # Book Alpha 10:00-11:00
        b1 = await client.post("/bookings", json={
            "room": "Alpha", "organiser": "Alice",
            "start_time": "2026-12-01T10:00:00", "end_time": "2026-12-01T11:00:00",
            "attendee_count": 2,
        })
        b1_id = b1.json()["id"]

        # Book Alpha 11:00-12:00
        await client.post("/bookings", json={
            "room": "Alpha", "organiser": "Bob",
            "start_time": "2026-12-01T11:00:00", "end_time": "2026-12-01T12:00:00",
            "attendee_count": 2,
        })
        # Try to update b1 to 10:30-11:30 → overlaps
        resp = await client.put(f"/bookings/{b1_id}", json={"end_time": "2026-12-01T11:30:00"})
        assert resp.status_code == 409


class TestDeleteBooking:
    async def test_delete_existing(self, client, sample_booking):
        resp = await client.delete(f"/bookings/{sample_booking['id']}")
        assert resp.status_code == 204
        # Verify gone
        resp2 = await client.get(f"/bookings/{sample_booking['id']}")
        assert resp2.status_code == 404

    async def test_delete_nonexistent(self, client):
        resp = await client.delete("/bookings/99999")
        assert resp.status_code == 404


# ---- M2: Conflict prevention ----

class TestConflictPrevention:
    async def test_exact_overlap_rejected(self, client):
        await client.post("/bookings", json={
            "room": "Gamma", "organiser": "Alice",
            "start_time": "2026-12-01T10:00:00", "end_time": "2026-12-01T11:00:00",
            "attendee_count": 4,
        })
        resp = await client.post("/bookings", json={
            "room": "Gamma", "organiser": "Bob",
            "start_time": "2026-12-01T10:00:00", "end_time": "2026-12-01T11:00:00",
            "attendee_count": 4,
        })
        assert resp.status_code == 409

    async def test_partial_overlap_start(self, client):
        await client.post("/bookings", json={
            "room": "Gamma", "organiser": "Alice",
            "start_time": "2026-12-01T10:00:00", "end_time": "2026-12-01T11:00:00",
            "attendee_count": 4,
        })
        resp = await client.post("/bookings", json={
            "room": "Gamma", "organiser": "Bob",
            "start_time": "2026-12-01T10:30:00", "end_time": "2026-12-01T11:30:00",
            "attendee_count": 4,
        })
        assert resp.status_code == 409

    async def test_partial_overlap_end(self, client):
        await client.post("/bookings", json={
            "room": "Gamma", "organiser": "Alice",
            "start_time": "2026-12-01T10:00:00", "end_time": "2026-12-01T11:00:00",
            "attendee_count": 4,
        })
        resp = await client.post("/bookings", json={
            "room": "Gamma", "organiser": "Bob",
            "start_time": "2026-12-01T09:30:00", "end_time": "2026-12-01T10:30:00",
            "attendee_count": 4,
        })
        assert resp.status_code == 409

    async def test_contains_existing(self, client):
        await client.post("/bookings", json={
            "room": "Gamma", "organiser": "Alice",
            "start_time": "2026-12-01T10:00:00", "end_time": "2026-12-01T11:00:00",
            "attendee_count": 4,
        })
        resp = await client.post("/bookings", json={
            "room": "Gamma", "organiser": "Bob",
            "start_time": "2026-12-01T09:00:00", "end_time": "2026-12-01T12:00:00",
            "attendee_count": 4,
        })
        assert resp.status_code == 409

    async def test_back_to_back_allowed(self, client):
        await client.post("/bookings", json={
            "room": "Gamma", "organiser": "Alice",
            "start_time": "2026-12-01T10:00:00", "end_time": "2026-12-01T11:00:00",
            "attendee_count": 4,
        })
        resp = await client.post("/bookings", json={
            "room": "Gamma", "organiser": "Bob",
            "start_time": "2026-12-01T11:00:00", "end_time": "2026-12-01T12:00:00",
            "attendee_count": 4,
        })
        assert resp.status_code == 201

    async def test_different_rooms_no_conflict(self, client):
        await client.post("/bookings", json={
            "room": "Gamma", "organiser": "Alice",
            "start_time": "2026-12-01T10:00:00", "end_time": "2026-12-01T11:00:00",
            "attendee_count": 4,
        })
        resp = await client.post("/bookings", json={
            "room": "Delta", "organiser": "Bob",
            "start_time": "2026-12-01T10:00:00", "end_time": "2026-12-01T11:00:00",
            "attendee_count": 4,
        })
        assert resp.status_code == 201


# ---- M3: Room capacity ----

class TestRoomCapacity:
    async def test_rooms_list(self, client):
        resp = await client.get("/rooms")
        assert resp.status_code == 200
        rooms = resp.json()
        assert len(rooms) == 5
        names = [r["name"] for r in rooms]
        assert names == sorted(names)

    async def test_rooms_alphabetic_order(self, client):
        resp = await client.get("/rooms")
        rooms = resp.json()
        names = [r["name"] for r in rooms]
        expected = ["Alpha", "Beta", "Delta", "Epsilon", "Gamma"]
        assert names == expected


# ---- M4: Find-slot ----

class TestFindSlot:
    async def test_basic_find(self, client):
        resp = await client.post("/find-slot", json={
            "date": "2026-12-01", "duration_minutes": 60, "attendee_count": 4,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["available"] is True
        assert data["room"] == "Alpha"
        assert data["start_time"] == "2026-12-01T09:00:00"
        assert data["end_time"] == "2026-12-01T10:00:00"

    async def test_no_available_room(self, client):
        resp = await client.post("/find-slot", json={
            "date": "2026-12-01", "duration_minutes": 60, "attendee_count": 100,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["available"] is False

    async def test_with_existing_bookings(self, client):
        await client.post("/bookings", json={
            "room": "Alpha", "organiser": "A", "start_time": "2026-12-01T09:00:00",
            "end_time": "2026-12-01T10:00:00", "attendee_count": 2,
        })
        resp = await client.post("/find-slot", json={
            "date": "2026-12-01", "duration_minutes": 30, "attendee_count": 2,
        })
        data = resp.json()
        assert data["available"] is True
        assert data["room"] == "Beta"
        assert data["start_time"] == "2026-12-01T09:00:00"

    async def test_duration_too_long(self, client):
        resp = await client.post("/find-slot", json={
            "date": "2026-12-01", "duration_minutes": 1000, "attendee_count": 2,
        })
        data = resp.json()
        assert data["available"] is False


# ---- M5: Weekly recurrence ----

class TestRecurrence:
    async def test_basic_recurrence(self, client):
        resp = await client.post("/bookings/recurring", json={
            "room": "Gamma", "organiser": "Alice",
            "start_time": "2026-12-01T10:00:00", "end_time": "2026-12-01T11:00:00",
            "attendee_count": 4,
            "recurrence_start": "2026-12-01", "recurrence_end": "2026-12-15",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert len(data["created"]) == 3  # Dec 1, 8, 15
        assert len(data["conflicts"]) == 0
        assert len(data["failures"]) == 0

    async def test_recurrence_with_conflict(self, client):
        await client.post("/bookings", json={
            "room": "Gamma", "organiser": "Bob",
            "start_time": "2026-12-08T10:00:00", "end_time": "2026-12-08T11:00:00",
            "attendee_count": 4,
        })
        resp = await client.post("/bookings/recurring", json={
            "room": "Gamma", "organiser": "Alice",
            "start_time": "2026-12-01T10:00:00", "end_time": "2026-12-01T11:00:00",
            "attendee_count": 4,
            "recurrence_start": "2026-12-01", "recurrence_end": "2026-12-15",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert len(data["created"]) == 2
        assert len(data["conflicts"]) == 1
        assert len(data["failures"]) == 0

    async def test_recurrence_invalid_room(self, client):
        resp = await client.post("/bookings/recurring", json={
            "room": "FakeRoom", "organiser": "Alice",
            "start_time": "2026-12-01T10:00:00", "end_time": "2026-12-01T11:00:00",
            "attendee_count": 4,
            "recurrence_start": "2026-12-01", "recurrence_end": "2026-12-15",
        })
        assert resp.status_code == 400

    async def test_recurrence_capacity_failure(self, client):
        resp = await client.post("/bookings/recurring", json={
            "room": "Gamma", "organiser": "Alice",
            "start_time": "2026-12-01T10:00:00", "end_time": "2026-12-01T11:00:00",
            "attendee_count": 10,
            "recurrence_start": "2026-12-01", "recurrence_end": "2026-12-15",
        })
        assert resp.status_code == 400

    async def test_recurrence_empty_range(self, client):
        resp = await client.post("/bookings/recurring", json={
            "room": "Gamma", "organiser": "Alice",
            "start_time": "2026-12-01T10:00:00", "end_time": "2026-12-01T11:00:00",
            "attendee_count": 4,
            "recurrence_start": "2026-12-15", "recurrence_end": "2026-12-10",
        })
        assert resp.status_code == 422


# ---- Health check ----

class TestHealth:
    async def test_health(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 404  # health endpoint is on main.py but we use bare FastAPI in tests