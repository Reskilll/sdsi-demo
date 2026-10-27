"""End-to-end demonstration of the Meeting Room Booking Engine.

Runs through every mandatory requirement (M1–M5) against the sample
``rooms.json`` catalogue and prints a readable transcript of each result.

Usage:
    python run_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from engine import BookingEngine
from engine.models import BookingRequest

HERE = Path(__file__).resolve().parent
ROOMS_FILE = HERE / "rooms.json"

SEP = "=" * 70


def _req(id, room, start, end, attendees, until=None):
    return BookingRequest(
        id=id,
        room_id=room,
        organiser="demo",
        start_time=start,
        end_time=end,
        attendees=attendees,
        recurrence_weekly_until=until,
    )


def show_result(label, res):
    print(f"\n{SEP}\n{label}\n{SEP}")
    if res.success:
        b = res.booking
        print("  [OK] SUCCESS")
        print(f"    id={b.id} room={b.room_id} {b.start_time.isoformat()} → "
              f"{b.end_time.isoformat()} attendees={len(b.attendees)}")
    else:
        print("  [XX] REJECTED")
        if res.errors:
            print("    errors:")
            for e in res.errors:
                print(f"      - {e}")
        if res.conflicts:
            print("    conflicts:")
            for c in res.conflicts:
                print(f"      - [{c.occurrence_date}] {c.reason}")


def main() -> int:
    engine = BookingEngine(str(ROOMS_FILE))

    print("MEETING ROOM BOOKING ENGINE — DEMO")
    print(f"Loaded rooms: {[f'{r.id}({r.capacity})' for r in engine.list_rooms()]}")

    # ------------------------------------------------------------------
    # M1: CRUD
    # ------------------------------------------------------------------
    print(f"\n{SEP}\nM1 — Create / Read / Update / Delete\n{SEP}")

    r = engine.create_booking(_req("m1-a", "r1", "2026-10-27T09:00",
                                   "2026-10-27T10:00", ["alice", "bob"]))
    show_result("Create booking 'm1-a' in Alpha (09:00–10:00)", r)

    b = engine.read_booking("m1-a")
    print(f"  Read booking 'm1-a': organiser={b.organiser}, "
          f"attendees={b.attendees}")

    r = engine.update_booking(_req("m1-a", "r1", "2026-10-27T09:00",
                                   "2026-10-27T10:30", ["alice", "bob"]))
    show_result("Update 'm1-a' to end at 10:30", r)

    engine.delete_booking("m1-a")
    print("  Deleted 'm1-a'.")

    # ------------------------------------------------------------------
    # M2: overlap rejection + back-to-back
    # ------------------------------------------------------------------
    print(f"\n{SEP}\nM2 — Overlap rejection & back-to-back\n{SEP}")

    r = engine.create_booking(_req("m2-a", "r1", "2026-10-27T09:00",
                                   "2026-10-27T10:00", ["alice"]))
    show_result("Create 'm2-a' in Alpha (09:00–10:00)", r)

    r = engine.create_booking(_req("m2-back2back", "r1", "2026-10-27T10:00",
                                   "2026-10-27T11:00", ["bob"]))
    show_result("Back-to-back 'm2-back2back' (10:00–11:00) — should SUCCEED", r)

    r = engine.create_booking(_req("m2-overlap", "r1", "2026-10-27T10:30",
                                   "2026-10-27T11:30", ["carol"]))
    show_result("Overlap 'm2-overlap' (10:30–11:30) — should REJECT", r)

    # Different-room simultaneous bookings
    r = engine.create_booking(_req("m2-diff", "r2", "2026-10-27T09:00",
                                   "2026-10-27T10:00", ["dave"]))
    show_result("Different room 'm2-diff' in Beta (09:00–10:00) — should SUCCEED", r)

    # ------------------------------------------------------------------
    # M3: capacity validation
    # ------------------------------------------------------------------
    print(f"\n{SEP}\nM3 — Capacity validation\n{SEP}")

    r = engine.create_booking(_req("m3-ok", "r4", "2026-10-27T09:00",
                                   "2026-10-27T10:00", ["p1", "p2"]))
    show_result("Delta (cap 2) with 2 attendees — should SUCCEED", r)

    r = engine.create_booking(_req("m3-over", "r4", "2026-10-27T11:00",
                                   "2026-10-27T12:00", ["p1", "p2", "p3"]))
    show_result("Delta (cap 2) with 3 attendees — should REJECT", r)

    # ------------------------------------------------------------------
    # M4: find-slot
    # ------------------------------------------------------------------
    print(f"\n{SEP}\nM4 — find-slot\n{SEP}")

    slot = engine.find_slot(60, 3, "2026-10-27")
    print(f"  find_slot(60min, 3 people, 2026-10-27) → "
          f"{(slot.room.id, slot.start.isoformat(), slot.end.isoformat()) if slot else None}")

    slot = engine.find_slot(60, 10, "2026-10-27")
    print(f"  find_slot(60min, 10 people, 2026-10-27) → "
          f"{(slot.room.id, slot.start.isoformat(), slot.end.isoformat()) if slot else None}")

    slot = engine.find_slot(30, 1, "2026-10-27")
    print(f"  find_slot(30min, 1 person, 2026-10-27) → "
          f"{(slot.room.id, slot.start.isoformat(), slot.end.isoformat()) if slot else None}")

    # ------------------------------------------------------------------
    # M5: weekly recurrence + conflict reporting
    # ------------------------------------------------------------------
    print(f"\n{SEP}\nM5 — Weekly recurrence & conflict reporting\n{SEP}")

    r = engine.create_booking(_req(
        "m5-weekly", "r1", "2026-10-26T09:00", "2026-10-26T10:00",
        ["standup"], until="2026-11-30",
    ))
    show_result("Weekly 'm5-weekly' Mondays 09:00–10:00 (until 2026-11-30)", r)

    r = engine.create_booking(_req(
        "m5-conflict", "r1", "2026-11-02T09:30", "2026-11-02T10:30",
        ["clash"], until="2026-11-30",
    ))
    show_result("Weekly 'm5-conflict' Mondays 09:30–10:30 — should REJECT "
                "with per-occurrence conflicts", r)

    print(f"\n{SEP}\nFinal booking list\n{SEP}")
    for b in sorted(engine.list_bookings(), key=lambda x: x.id):
        rec = f" (weekly until {b.recurrence_weekly_until})" if b.is_recurring() else ""
        print(f"  {b.id}: {b.room_id} {b.start_time.isoformat()} → "
              f"{b.end_time.isoformat()} [{len(b.attendees)} attendees]{rec}")

    return 0


if __name__ == "__main__":
    sys.exit(main())