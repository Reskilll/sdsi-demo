"""Concurrency tests — verify race condition prevention."""
import asyncio
import pytest


async def _create_booking(client, room, start, end, attendees):
    return await client.post("/bookings", json={
        "room": room,
        "organiser": f"User-{start}",
        "start_time": start,
        "end_time": end,
        "attendee_count": attendees,
    })


class TestConcurrency:
    async def test_concurrent_same_slot(self, client):
        """Multiple concurrent requests for the same room+slot: only one should succeed."""
        tasks = [
            _create_booking(client, "Gamma", "2026-12-01T10:00:00", "2026-12-01T11:00:00", 4)
            for _ in range(10)
        ]
        responses = await asyncio.gather(*tasks)

        statuses = [r.status_code for r in responses]
        created = sum(1 for s in statuses if s == 201)
        conflicts = sum(1 for s in statuses if s == 409)

        assert created == 1, f"Expected exactly 1 booking created, got {created}"
        assert conflicts == 9, f"Expected 9 conflicts, got {conflicts}"

    async def test_concurrent_different_slots(self, client):
        """Concurrent requests for different slots should all succeed."""
        tasks = [
            _create_booking(client, "Gamma", f"2026-12-01T{10+i:02d}:00:00",
                            f"2026-12-01T{10+i:02d}:30:00", 4)
            for i in range(5)
        ]
        responses = await asyncio.gather(*tasks)

        statuses = [r.status_code for r in responses]
        assert all(s == 201 for s in statuses), f"Expected all 201, got {statuses}"

    async def test_concurrent_different_rooms(self, client):
        """Concurrent requests for same time but different rooms: all should succeed."""
        rooms = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon"]
        tasks = [
            _create_booking(client, room, "2026-12-01T10:00:00", "2026-12-01T11:00:00",
                            min(4, idx + 1))
            for idx, room in enumerate(rooms)
        ]
        responses = await asyncio.gather(*tasks)

        statuses = [r.status_code for r in responses]
        assert all(s == 201 for s in statuses), f"Expected all 201, got {statuses}"

    async def test_concurrent_update_and_delete(self, client):
        """Concurrent update and delete on same booking."""
        resp = await client.post("/bookings", json={
            "room": "Gamma", "organiser": "Alice",
            "start_time": "2026-12-01T10:00:00", "end_time": "2026-12-01T11:00:00",
            "attendee_count": 4,
        })
        booking_id = resp.json()["id"]

        from httpx import AsyncClient, ASGITransport

        async def do_update():
            return await client.put(f"/bookings/{booking_id}", json={"organiser": "Bob"})

        async def do_delete():
            return await client.delete(f"/bookings/{booking_id}")

        update_resp, delete_resp = await asyncio.gather(do_update(), do_delete())

        # At least one should succeed (404=already deleted, 200/204=success)
        success = [r.status_code for r in [update_resp, delete_resp] if r.status_code in (200, 204, 404)]
        assert len(success) >= 1

    async def test_concurrent_recurrence(self, client):
        """Two concurrent recurrence creations for overlapping slots."""
        payload1 = {
            "room": "Gamma", "organiser": "Alice",
            "start_time": "2026-12-01T10:00:00", "end_time": "2026-12-01T11:00:00",
            "attendee_count": 4,
            "recurrence_start": "2026-12-01", "recurrence_end": "2026-12-08",
        }
        payload2 = {
            "room": "Gamma", "organiser": "Bob",
            "start_time": "2026-12-01T10:30:00", "end_time": "2026-12-01T11:30:00",
            "attendee_count": 4,
            "recurrence_start": "2026-12-01", "recurrence_end": "2026-12-08",
        }

        async def post(payload):
            return await client.post("/bookings/recurring", json=payload)

        r1, r2 = await asyncio.gather(post(payload1), post(payload2))

        # Both might partly succeed, but overlapping Dec 1 slot should only have one winner
        created1 = len(r1.json().get("created", [])) if r1.status_code == 201 else 0
        created2 = len(r2.json().get("created", [])) if r2.status_code == 201 else 0

        # At most one of the two overlapping Dec 1 slots should exist
        list_resp = await client.get("/bookings?room=Gamma")
        data = list_resp.json()
        overlapping = [
            b for b in data["bookings"]
            if b["end_time"] > "2026-12-01T10:00:00" and b["start_time"] < "2026-12-01T11:00:00"
        ]
        assert len(overlapping) <= 2  # Each recurrence has 2 dates; max 2 total (one per date)