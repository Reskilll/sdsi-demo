"""
HTTP API server for the Expense Splitter web UI.

Start with:
    python -m expense_splitter.server
    python -m expense_splitter.server --port 9000

Serves the static frontend (static/) and a JSON REST API on /api/*.
Uses only Python stdlib – no external dependencies.
"""

from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

from .engine import process_group
from .models import (
    DEFAULT_CURRENCY,
    Expense,
    ExpenseGroup,
    Member,
    SplitEntry,
    SplitType,
)
from .validation import validate_input

# ── In-memory store ──────────────────────────────────────────────────────────

STORE: dict = {"members": [], "expenses": []}

# Resolve static directory relative to this module
STATIC_DIR = Path(__file__).parent.parent / "static"


def seed_demo_data() -> None:
    """Populate the store with sample data."""
    STORE["members"] = [
        {"id": "alice", "name": "Alice"},
        {"id": "bob", "name": "Bob"},
        {"id": "charlie", "name": "Charlie"},
        {"id": "diana", "name": "Diana"},
        {"id": "eve", "name": "Eve"},
    ]
    STORE["expenses"] = [
        {
            "expense_id": "exp1", "description": "Dinner at Taj",
            "amount": 1000.00, "currency": "INR", "payer": "alice",
            "participants": ["alice", "bob", "charlie"], "split_type": "equal",
            "timestamp": "2025-01-10T20:00:00Z",
        },
        {
            "expense_id": "exp2", "description": "Movie tickets",
            "amount": 600.00, "currency": "INR", "payer": "bob",
            "participants": ["alice", "bob", "diana"], "split_type": "exact",
            "split_details": [
                {"member_id": "alice", "value": 150.00},
                {"member_id": "bob", "value": 200.00},
                {"member_id": "diana", "value": 250.00},
            ],
            "timestamp": "2025-01-12T18:30:00Z",
        },
        {
            "expense_id": "exp3", "description": "Groceries",
            "amount": 800.00, "currency": "INR", "payer": "charlie",
            "participants": ["alice", "bob", "charlie", "diana"],
            "split_type": "percentage",
            "split_details": [
                {"member_id": "alice", "value": 20},
                {"member_id": "bob", "value": 30},
                {"member_id": "charlie", "value": 50},
                {"member_id": "diana", "value": 0},
            ],
            "timestamp": "2025-01-15T14:00:00Z",
        },
        {
            "expense_id": "exp4", "description": "Cab ride",
            "amount": 300.00, "currency": "INR", "payer": "diana",
            "participants": ["alice", "charlie"], "split_type": "equal",
            "timestamp": "2025-01-18T22:00:00Z",
        },
        {
            "expense_id": "exp5", "description": "Diana pays for Eve's lunch",
            "amount": 450.50, "currency": "INR", "payer": "diana",
            "participants": ["eve"], "split_type": "equal",
            "timestamp": "2025-01-20T12:30:00Z",
        },
    ]


# ── helpers ───────────────────────────────────────────────────────────────────

def _build_group() -> ExpenseGroup:
    return ExpenseGroup(
        members=tuple(Member(id=m["id"], name=m.get("name")) for m in STORE["members"]),
        expenses=tuple(
            Expense(
                expense_id=e["expense_id"],
                description=e.get("description", ""),
                amount=Decimal(str(e["amount"])),
                currency=e.get("currency", DEFAULT_CURRENCY),
                payer_id=e["payer"],
                participant_ids=tuple(e["participants"]),
                split_type=SplitType(e["split_type"]),
                split_details=tuple(
                    SplitEntry(d["member_id"], Decimal(str(d["value"])))
                    for d in e.get("split_details", [])
                ),
                timestamp=e.get("timestamp"),
            )
            for e in STORE["expenses"]
        ),
    )


def _result_json() -> dict:
    group = _build_group()
    result = process_group(group)
    member_map = {m["id"]: m for m in STORE["members"]}
    return {
        "members": STORE["members"],
        "total_expenses": len(STORE["expenses"]),
        "total_amount": str(sum(Decimal(str(e["amount"])) for e in STORE["expenses"])),
        "balances": [
            {
                "member_id": b.member_id,
                "name": member_map.get(b.member_id, {}).get("name", b.member_id),
                "total_paid": str(b.total_paid),
                "total_share": str(b.total_share),
                "net_balance": str(b.net_balance),
            }
            for b in result.balances
        ],
        "settlements": [
            {
                "from": s.from_member_id,
                "from_name": member_map.get(s.from_member_id, {}).get("name", s.from_member_id),
                "to": s.to_member_id,
                "to_name": member_map.get(s.to_member_id, {}).get("name", s.to_member_id),
                "amount": str(s.amount),
            }
            for s in result.settlements
        ],
        "expenses": STORE["expenses"],
    }


def _json(handler, data, status=200):
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _err(handler, msg, status=400):
    _json(handler, {"error": msg}, status)


# ── Request handler ───────────────────────────────────────────────────────────

class RequestHandler(SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    # ── routing ──────────────────────────────────────────────────────────

    def do_GET(self):
        path = urlparse(self.path).path
        if path.startswith("/api/"):
            self._api_get(path)
        elif path == "/" or self._is_spa_route(path):
            self._serve_index()
        else:
            super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        if path.startswith("/api/"):
            self._api_post(path)
        else:
            _err(self, "Not found", 404)

    def do_DELETE(self):
        path = urlparse(self.path).path
        if path.startswith("/api/"):
            self._api_delete(path)
        else:
            _err(self, "Not found", 404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        if "/api/" in str(args[0] if args else ""):
            sys.stderr.write(f"  {args[0]}\n")

    # ── static serving ───────────────────────────────────────────────────

    def _is_spa_route(self, path: str) -> bool:
        """Heuristic: paths without a file extension are SPA routes."""
        return "." not in path.rstrip("/").rsplit("/", 1)[-1] and path != "/"

    def _serve_index(self):
        idx = STATIC_DIR / "index.html"
        if not idx.exists():
            return _err(self, "Frontend not found. Run from project root.", 500)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(idx.read_bytes())

    # ── API: GET ─────────────────────────────────────────────────────────

    def _api_get(self, path: str):
        try:
            if path == "/api/group":
                _json(self, _result_json())
            elif path == "/api/balances":
                group = _build_group()
                result = process_group(group)
                mm = {m["id"]: m for m in STORE["members"]}
                _json(self, {"balances": [
                    {"member_id": b.member_id,
                     "name": mm.get(b.member_id, {}).get("name", b.member_id),
                     "total_paid": str(b.total_paid),
                     "total_share": str(b.total_share),
                     "net_balance": str(b.net_balance)}
                    for b in result.balances
                ]})
            elif path == "/api/settlements":
                group = _build_group()
                result = process_group(group)
                mm = {m["id"]: m for m in STORE["members"]}
                _json(self, {"settlements": [
                    {"from": s.from_member_id,
                     "from_name": mm.get(s.from_member_id, {}).get("name", s.from_member_id),
                     "to": s.to_member_id,
                     "to_name": mm.get(s.to_member_id, {}).get("name", s.to_member_id),
                     "amount": str(s.amount)}
                    for s in result.settlements
                ]})
            elif path == "/api/members":
                _json(self, {"members": STORE["members"]})
            elif path == "/api/expenses":
                _json(self, {"expenses": STORE["expenses"]})
            else:
                _err(self, "Unknown API endpoint", 404)
        except Exception as e:
            _err(self, str(e), 500)

    # ── API: POST ────────────────────────────────────────────────────────

    def _api_post(self, path: str):
        try:
            cl = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(cl)) if cl > 0 else {}
            if path == "/api/expenses":
                self._add_expense(data)
            elif path == "/api/members":
                self._add_member(data)
            elif path == "/api/import":
                self._import_batch(data)
            elif path == "/api/reset":
                seed_demo_data()
                _json(self, {"status": "ok", "message": "Store reset to demo data"})
            else:
                _err(self, "Unknown API endpoint", 404)
        except json.JSONDecodeError as e:
            _err(self, f"Invalid JSON: {e}")
        except Exception as e:
            _err(self, str(e), 500)

    # ── API: DELETE ──────────────────────────────────────────────────────

    def _api_delete(self, path: str):
        try:
            parts = path.split("/")
            if len(parts) >= 4 and parts[1] == "api":
                if parts[2] == "expenses":
                    eid = parts[3]
                    before = len(STORE["expenses"])
                    STORE["expenses"] = [e for e in STORE["expenses"] if e["expense_id"] != eid]
                    if len(STORE["expenses"]) == before:
                        return _err(self, f"Expense '{eid}' not found", 404)
                    return _json(self, {"status": "ok"})
                elif parts[2] == "members":
                    mid = parts[3]
                    before = len(STORE["members"])
                    STORE["members"] = [m for m in STORE["members"] if m["id"] != mid]
                    if len(STORE["members"]) == before:
                        return _err(self, f"Member '{mid}' not found", 404)
                    return _json(self, {"status": "ok"})
            _err(self, "Unknown API endpoint", 404)
        except Exception as e:
            _err(self, str(e), 500)

    # ── business logic ───────────────────────────────────────────────────

    def _add_expense(self, data: dict):
        for f in ["description", "amount", "payer", "participants", "split_type"]:
            if f not in data:
                return _err(self, f"Missing required field: {f}")

        eid = data.get("expense_id") or f"exp-{uuid.uuid4().hex[:8]}"
        if any(e["expense_id"] == eid for e in STORE["expenses"]):
            return _err(self, f"Duplicate expense ID: {eid}")

        member_ids = {m["id"] for m in STORE["members"]}
        if data["payer"] not in member_ids:
            return _err(self, f"Unknown payer: {data['payer']}")
        for pid in data["participants"]:
            if pid not in member_ids:
                return _err(self, f"Unknown participant: {pid}")

        expense = {
            "expense_id": eid,
            "description": data["description"],
            "amount": float(data["amount"]),
            "currency": data.get("currency", "INR"),
            "payer": data["payer"],
            "participants": data["participants"],
            "split_type": data["split_type"],
            "timestamp": data.get("timestamp") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        if data.get("split_details"):
            expense["split_details"] = data["split_details"]

        # Validate with backend
        test = {"members": STORE["members"], "expenses": STORE["expenses"] + [expense]}
        try:
            validate_input(test)
        except Exception as e:
            return _err(self, str(e))

        STORE["expenses"].append(expense)
        _json(self, _result_json(), 201)

    def _add_member(self, data: dict):
        if "id" not in data:
            return _err(self, "Missing required field: id")
        mid = data["id"].strip()
        if not mid:
            return _err(self, "Member ID must not be empty")
        if any(m["id"] == mid for m in STORE["members"]):
            return _err(self, f"Duplicate member ID: {mid}")
        member = {"id": mid, "name": data.get("name", mid)}
        STORE["members"].append(member)
        _json(self, {"status": "ok", "member": member}, 201)

    def _import_batch(self, data: dict):
        if not isinstance(data, dict):
            return _err(self, "Input must be a JSON object")
        try:
            validate_input(data)
        except Exception as e:
            return _err(self, str(e))
        STORE["members"] = list(data.get("members", []))
        STORE["expenses"] = list(data.get("expenses", []))
        _json(self, _result_json())


# ── Entry point ───────────────────────────────────────────────────────────────

def run_server(host: str = "0.0.0.0", port: int = 8080):
    seed_demo_data()

    if not STATIC_DIR.exists():
        print(f"Error: static/ directory not found at {STATIC_DIR}", file=sys.stderr)
        sys.exit(1)

    server = HTTPServer((host, port), RequestHandler)
    url = f"http://localhost:{port}"
    print()
    print("=" * 55)
    print("  SplitWise Lite — Server Running")
    print(f"  {url}")
    print("  Press Ctrl+C to stop")
    print("=" * 55)
    print()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="SplitWise Lite server")
    ap.add_argument("--port", "-p", type=int, default=8080, help="Port (default: 8080)")
    ap.add_argument("--host", default="0.0.0.0", help="Host (default: 0.0.0.0)")
    args = ap.parse_args()
    run_server(host=args.host, port=args.port)