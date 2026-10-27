"""Scaffold-compatible wrapper around :class:`engine.BookingEngine`.

Preserves the ``run(task: str) -> dict`` interface from
``agent-template/agent.py`` so the submission remains compatible with any
harness that expects that contract.

``task`` must be a JSON object string with at minimum an ``action`` key.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ENGINE = None


def _get_engine():
    global _ENGINE
    if _ENGINE is None:
        from engine import BookingEngine
        rooms_file = os.environ.get("ROOMS_FILE", str(_HERE / "rooms.json"))
        data_file = os.environ.get("DATA_FILE", str(_HERE / "bookings.json"))
        _ENGINE = BookingEngine(rooms_file, data_file=data_file)
    return _ENGINE


def _serialize(obj):
    """JSON serialisation helper for dates, datetimes, and Slot."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if hasattr(obj, "room") and hasattr(obj, "start") and hasattr(obj, "end"):
        return {
            "room": {"id": obj.room.id, "name": obj.room.name, "capacity": obj.room.capacity},
            "start": obj.start.isoformat() if hasattr(obj.start, "isoformat") else obj.start,
            "end": obj.end.isoformat() if hasattr(obj.end, "isoformat") else obj.end,
        }
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    raise TypeError(f"Cannot serialize {type(obj).__name__}")


def run(task: str) -> dict:
    """Process a JSON booking command and return the scaffold contract.

    Parameters
    ----------
    task : str
        A JSON object string.  The ``action`` field selects the operation:

        - ``"create"`` — requires ``booking`` (BookingRequest object).
        - ``"read"`` — requires ``booking_id``.
        - ``"update"`` — requires ``booking`` (BookingRequest object).
        - ``"delete"`` — requires ``booking_id``.
        - ``"find-slot"`` — requires ``duration_minutes``, ``attendee_count``,
          ``date``.
        - ``"list-bookings"`` — optional ``room_id`` and/or ``date``.
        - ``"list-rooms"`` — no extra fields required.

    Returns
    -------
    dict
        Always ``{"plan": [...], "result": ..., "escalated": bool}``.
        On errors ``result`` contains the error details and ``escalated`` is
        ``True`` when human review is warranted (overlaps, capacity issues).
    """
    from engine.models import BookingRequest

    plan: list[str] = []
    result: dict = {}
    escalated = False

    try:
        payload = json.loads(task)
    except json.JSONDecodeError as exc:
        return {
            "plan": ["parse task JSON"],
            "result": {"error": f"invalid JSON: {exc}"},
            "escalated": True,
        }

    action = payload.get("action", "").strip().lower()
    engine = _get_engine()

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------
    if action == "create":
        plan.append("validate and create booking")
        try:
            req = _booking_request_from_payload(payload["booking"])
        except KeyError as exc:
            return {
                "plan": plan,
                "result": {"error": f"missing field: {exc}"},
                "escalated": True,
            }

        res = engine.create_booking(req)
        result = {
            "success": res.success,
            "booking": _booking_to_dict(res.booking) if res.booking else None,
        }
        if res.errors:
            result["errors"] = res.errors
            escalated = True
        if res.conflicts:
            result["conflicts"] = [{
                "booking_id": c.booking_id,
                "occurrence_date": c.occurrence_date.isoformat(),
                "reason": c.reason,
            } for c in res.conflicts]
            escalated = True
        return {"plan": plan, "result": result, "escalated": escalated}

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------
    elif action == "read":
        plan.append("read booking")
        bid = payload.get("booking_id")
        if not bid:
            return {"plan": plan, "result": {"error": "booking_id required"}, "escalated": True}
        try:
            b = engine.read_booking(bid)
            return {"plan": plan, "result": {"booking": _booking_to_dict(b)}, "escalated": False}
        except KeyError:
            return {
                "plan": plan,
                "result": {"error": f"booking '{bid}' not found"},
                "escalated": True,
            }

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------
    elif action == "update":
        plan.append("validate and update booking")
        try:
            req = _booking_request_from_payload(payload["booking"])
        except KeyError as exc:
            return {
                "plan": plan,
                "result": {"error": f"missing field: {exc}"},
                "escalated": True,
            }

        res = engine.update_booking(req)
        result = {
            "success": res.success,
            "booking": _booking_to_dict(res.booking) if res.booking else None,
        }
        if res.errors:
            result["errors"] = res.errors
            escalated = True
        if res.conflicts:
            result["conflicts"] = [{
                "booking_id": c.booking_id,
                "occurrence_date": c.occurrence_date.isoformat(),
                "reason": c.reason,
            } for c in res.conflicts]
            escalated = True
        return {"plan": plan, "result": result, "escalated": escalated}

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------
    elif action == "delete":
        plan.append("delete booking")
        bid = payload.get("booking_id")
        if not bid:
            return {"plan": plan, "result": {"error": "booking_id required"}, "escalated": True}
        try:
            engine.delete_booking(bid)
            return {"plan": plan, "result": {"deleted": bid}, "escalated": False}
        except KeyError:
            return {
                "plan": plan,
                "result": {"error": f"booking '{bid}' not found"},
                "escalated": True,
            }

    # ------------------------------------------------------------------
    # FIND-SLOT
    # ------------------------------------------------------------------
    elif action == "find-slot":
        plan.append("find available slot")
        try:
            dur = int(payload["duration_minutes"])
            cnt = int(payload["attendee_count"])
            dstr = payload["date"]
        except (KeyError, ValueError) as exc:
            return {
                "plan": plan,
                "result": {"error": f"invalid find-slot parameters: {exc}"},
                "escalated": True,
            }
        slot = engine.find_slot(dur, cnt, dstr)
        if slot:
            res_slot = json.loads(json.dumps(slot, default=_serialize))
        else:
            res_slot = None
        return {
            "plan": plan,
            "result": {"slot": res_slot},
            "escalated": slot is None,
        }

    # ------------------------------------------------------------------
    # LIST-BOOKINGS
    # ------------------------------------------------------------------
    elif action == "list-bookings":
        plan.append("list bookings")
        room_id = payload.get("room_id")
        date_str = payload.get("date")
        bookings = engine.list_bookings(room_id=room_id, date_str=date_str)
        return {
            "plan": plan,
            "result": {"bookings": [_booking_to_dict(b) for b in bookings]},
            "escalated": False,
        }

    # ------------------------------------------------------------------
    # LIST-ROOMS
    # ------------------------------------------------------------------
    elif action == "list-rooms":
        plan.append("list rooms")
        rooms = engine.list_rooms()
        return {
            "plan": plan,
            "result": {
                "rooms": [
                    {"id": r.id, "name": r.name, "capacity": r.capacity}
                    for r in rooms
                ]
            },
            "escalated": False,
        }

    else:
        return {
            "plan": plan,
            "result": {"error": f"unknown action: {action!r}"},
            "escalated": True,
        }


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

def _booking_request_from_payload(data: dict) -> "BookingRequest":
    from engine.models import BookingRequest
    return BookingRequest(
        id=data["id"],
        room_id=data["room_id"],
        organiser=data["organiser"],
        start_time=data["start_time"],
        end_time=data["end_time"],
        attendees=data["attendees"],
        recurrence_weekly_until=data.get("recurrence_weekly_until"),
    )


def _booking_to_dict(b) -> dict:
    return {
        "id": b.id,
        "room_id": b.room_id,
        "organiser": b.organiser,
        "start_time": b.start_time.isoformat() if hasattr(b.start_time, "isoformat") else str(b.start_time),
        "end_time": b.end_time.isoformat() if hasattr(b.end_time, "isoformat") else str(b.end_time),
        "attendees": b.attendees,
        "recurrence_weekly_until": (
            b.recurrence_weekly_until.isoformat()
            if b.recurrence_weekly_until else None
        ),
    }


# -----------------------------------------------------------------------
# CLI entry point
# -----------------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python agent.py '<json-command>'", file=sys.stderr)
        print('Example: python agent.py \'{"action":"list-rooms"}\'', file=sys.stderr)
        sys.exit(1)
    import json as _json
    print(_json.dumps(run(sys.argv[1]), indent=2, default=_serialize))