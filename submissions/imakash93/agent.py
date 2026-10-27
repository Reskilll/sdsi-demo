"""Flash-sale inventory reservation agent — the ``run(task: str) -> dict`` entry point.

This is the thin interface layer required by the hackathon scaffold.  It parses
a JSON operation descriptor, dispatches it to the :mod:`engine`, and returns
the ``{"plan", "result", "escalated"}`` contract.  All business logic lives in
:class:`engine.ReservationSystem`; this module only decides *what* to call and
how to shape the response.

Usage (one command, from the repository root)::

    python submissions/imakash93/agent.py '{"action":"load","file":"submissions/imakash93/inventory.json"}'
    python submissions/imakash93/agent.py '{"action":"reserve","user":"alice","sku":"KB-MECH","qty":1}'
    python submissions/imakash93/agent.py '{"action":"report"}'
"""
from __future__ import annotations

import json

import sanitize
from engine import BusinessError, ReservationSystem, SystemError

_system = ReservationSystem()

VALID_ACTIONS = ("load", "reserve", "confirm", "cancel", "report")


def reset_state() -> None:
    """Clear in-memory state.  Exposed for tests to isolate cases."""
    _system.clear()


def run(task: str) -> dict:
    plan: list[dict] = []

    # ── Step 1 — parse the operation descriptor ──────────────────────
    try:
        request = json.loads(task)
    except (json.JSONDecodeError, TypeError):
        plan.append({"step": "parse", "status": "fail", "detail": "task is not valid JSON"})
        return {"plan": plan, "result": None, "escalated": True}
    plan.append({"step": "parse", "status": "ok"})

    if not isinstance(request, dict):
        plan.append({"step": "validate", "status": "fail",
                     "detail": "task must be a JSON object"})
        return {"plan": plan, "result": None, "escalated": True}

    action = request.get("action")
    plan.append({"step": "validate", "status": "ok",
                 "detail": f"action={sanitize.clean_display(action)}"})

    # ── Step 2 — dispatch and shape the response ─────────────────────
    try:
        result = _dispatch(action, request)
    except BusinessError as exc:
        plan.append({"step": "execute", "status": "rejected",
                     "detail": sanitize.clean_display(exc.message)})
        return {
            "plan": plan,
            "result": {
                "action": sanitize.clean_display(action),
                "status": "rejected",
                "code": exc.code,
                "reason": sanitize.clean_display(exc.message),
            },
            "escalated": False,
        }
    except SystemError as exc:
        plan.append({"step": "execute", "status": "fail",
                     "detail": sanitize.clean_display(exc.message)})
        return {
            "plan": plan,
            "result": {
                "action": sanitize.clean_display(action),
                "status": "error",
                "code": exc.code,
                "reason": sanitize.clean_display(exc.message),
            },
            "escalated": True,
        }

    plan.append({"step": "execute", "status": "ok"})
    return {"plan": plan, "result": result, "escalated": False}


def _dispatch(action, request: dict) -> dict:
    if action == "load":
        return _system.load(request.get("file"))
    if action == "reserve":
        return _system.reserve(
            request.get("user"),
            request.get("sku"),
            request.get("qty"),
            request.get("ttl", 120),
        )
    if action == "confirm":
        return _system.confirm(
            request.get("reservation_id"),
            request.get("user"),
            request.get("sku"),
        )
    if action == "cancel":
        return _system.cancel(
            request.get("reservation_id"),
            request.get("user"),
            request.get("sku"),
        )
    if action == "report":
        return _system.report(request.get("sku"))
    raise BusinessError(
        "UNKNOWN_ACTION",
        f"unknown action {sanitize.clean_display(action)}; "
        f"valid actions: {', '.join(VALID_ACTIONS)}",
    )


if __name__ == "__main__":
    import sys
    from pprint import pprint

    payload = sys.argv[1] if len(sys.argv) > 1 else '{"action":"report"}'
    pprint(run(payload))