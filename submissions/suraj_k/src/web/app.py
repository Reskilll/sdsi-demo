"""
FastAPI web application for the Splitwise-Lite expense settler.

Routes:
  GET  /                    — landing / group creation
  GET  /group/{group_id}    — main dashboard (balances, settlements, add expense)
  POST /group/{group_id}/expense   — add an expense via form
  POST /group/{group_id}/deactivate/{name} — soft-delete a member
  POST /group/{group_id}/upload — upload a JSON file of expenses
  GET  /group/{group_id}/api/summary — JSON summary endpoint
"""

from __future__ import annotations

import json
import uuid
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.errors import (
    InactiveMemberError,
    MemberNotFoundError,
    SplitValidationError,
    SplitwiseError,
    ValidationError,
)
from src.models.split import validate_amount
from src.web.store import store

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

_BASE = Path(__file__).resolve().parent

app = FastAPI(title="Splitwise-Lite", version="1.0.0")

# Serve static files (CSS).
app.mount("/static", StaticFiles(directory=str(_BASE / "static")), name="static")

templates = Jinja2Templates(directory=str(_BASE / "templates"))

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _gm(group_id: str):
    """Fetch GroupManager or 404."""
    try:
        return store.get(group_id)
    except MemberNotFoundError:
        raise HTTPException(status_code=404, detail="Group not found")


def _render_dashboard(request: Request, group_id: str, error: str = ""):
    """Render the main dashboard template with all state."""
    gm = _gm(group_id)
    balances = gm.net_balances()
    settlements = gm.simplify_debts()
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "group_id": group_id,
            "group_name": gm.name,
            "active_members": gm.active_members,
            "all_members": gm.members,
            "member_count": gm.active_member_count,
            "total_member_count": gm.member_count,
            "expense_count": gm.expense_count,
            "total_spent": str(gm.total_spent),
            "balances": [
                {
                    "name": b.member.name,
                    "paid": str(b.paid),
                    "owed": str(b.owed),
                    "net": str(b.net),
                    "active": b.member.is_active,
                    "is_creditor": b.net > Decimal("0"),
                    "is_debtor": b.net < Decimal("0"),
                    "is_settled": b.net == Decimal("0"),
                }
                for b in balances
            ],
            "settlements": [
                {"from": t.from_member.name, "to": t.to_member.name, "amount": str(t.amount)}
                for t in settlements
            ],
            "expenses": [
                {
                    "desc": e.description,
                    "payer": e.payer.name,
                    "amount": str(e.total_amount),
                }
                for e in gm.expenses[-10:]  # last 10 for readability
            ],
            "error": error,
        },
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    """Landing page — create or select a group."""
    return templates.TemplateResponse(
        "landing.html",
        {"request": request},
    )


@app.post("/", response_class=HTMLResponse)
async def create_group(request: Request, name: str = Form("My Group")):
    """Create a new group."""
    gid = store.create(name)
    return RedirectResponse(url=f"/group/{gid}", status_code=303)


@app.get("/group/{group_id}", response_class=HTMLResponse)
async def dashboard(request: Request, group_id: str):
    """Main dashboard for a group."""
    return _render_dashboard(request, group_id)


@app.post("/group/{group_id}/member", response_class=HTMLResponse)
async def add_member(request: Request, group_id: str, member_name: str = Form(...)):
    """Add a new member to the group."""
    gm = _gm(group_id)
    name = member_name.strip()
    if not name:
        return _render_dashboard(request, group_id, error="Member name cannot be empty")
    if len(name) > 100:
        return _render_dashboard(request, group_id, error="Member name too long (max 100 characters)")
    try:
        gm.add_member(name)
    except MemberNotFoundError as e:
        return _render_dashboard(request, group_id, error=str(e))
    return RedirectResponse(url=f"/group/{group_id}", status_code=303)


@app.post("/group/{group_id}/expense", response_class=HTMLResponse)
async def add_expense(
    request: Request,
    group_id: str,
    description: str = Form(...),
    payer: str = Form(...),
    amount: str = Form(...),
    split_type: str = Form("equal"),
    # We receive participants and split_values as comma-separated or JSON-ish strings.
    participants: str = Form(""),
    split_values: str = Form(""),
):
    """Add an expense via form submission."""
    gm = _gm(group_id)

    # Validate amount.
    try:
        amt = validate_amount(amount)
    except ValidationError as e:
        return _render_dashboard(request, group_id, error=str(e))

    # Parse participants.
    participant_list = [p.strip() for p in participants.split(",") if p.strip()]
    if not participant_list:
        return _render_dashboard(request, group_id, error="Must select at least one participant")

    # Build split_data.
    split_data: dict = {"type": split_type, "participants": participant_list}

    if split_type == "exact":
        # split_values format: "Alice=15.00,Bob=15.00,Charlie=15.00"
        amounts = {}
        for pair in split_values.split(","):
            pair = pair.strip()
            if "=" not in pair:
                return _render_dashboard(request, group_id, error=f"Invalid exact amount format: {pair}")
            k, v = pair.split("=", 1)
            amounts[k.strip()] = float(v.strip())
        split_data["amounts"] = amounts

    elif split_type == "percentage":
        # split_values format: "Alice=40,Bob=60"
        percentages = {}
        for pair in split_values.split(","):
            pair = pair.strip()
            if "=" not in pair:
                return _render_dashboard(request, group_id, error=f"Invalid percentage format: {pair}")
            k, v = pair.split("=", 1)
            percentages[k.strip()] = float(v.strip())
        split_data["percentages"] = percentages

    try:
        gm.add_expense(
            description=description.strip(),
            payer_name=payer.strip(),
            amount=amt,
            split_data=split_data,
        )
    except (MemberNotFoundError, InactiveMemberError, SplitValidationError, ValidationError) as e:
        return _render_dashboard(request, group_id, error=str(e))

    return RedirectResponse(url=f"/group/{group_id}", status_code=303)


@app.post("/group/{group_id}/deactivate/{name}", response_class=HTMLResponse)
async def deactivate_member(request: Request, group_id: str, name: str):
    """Soft-delete a member."""
    gm = _gm(group_id)
    try:
        gm.deactivate_member(name)
    except (MemberNotFoundError, InactiveMemberError) as e:
        return _render_dashboard(request, group_id, error=str(e))
    return RedirectResponse(url=f"/group/{group_id}", status_code=303)


@app.post("/group/{group_id}/reactivate/{name}", response_class=HTMLResponse)
async def reactivate_member(request: Request, group_id: str, name: str):
    """Re-activate a previously deactivated member."""
    gm = _gm(group_id)
    try:
        gm.reactivate_member(name)
    except (MemberNotFoundError, InactiveMemberError) as e:
        return _render_dashboard(request, group_id, error=str(e))
    return RedirectResponse(url=f"/group/{group_id}", status_code=303)


@app.post("/group/{group_id}/upload", response_class=HTMLResponse)
async def upload_json(request: Request, group_id: str, file: UploadFile = File(...)):
    """Upload a JSON file of expenses to add to the group."""
    gm = _gm(group_id)

    if not file.filename or not file.filename.endswith(".json"):
        return _render_dashboard(request, group_id, error="Only .json files are accepted")

    contents = await file.read()
    if len(contents) > 50 * 1024 * 1024:
        return _render_dashboard(request, group_id, error="File too large (max 50 MiB)")

    try:
        data = json.loads(contents.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return _render_dashboard(request, group_id, error=f"Invalid JSON: {e}")

    if not isinstance(data, dict):
        return _render_dashboard(request, group_id, error="JSON must be a top-level object")

    expenses_data = data.get("expenses", [])
    if not isinstance(expenses_data, list):
        return _render_dashboard(request, group_id, error="'expenses' must be a list")

    errors = []
    for i, exp in enumerate(expenses_data):
        if not isinstance(exp, dict):
            errors.append(f"expense[{i}]: not an object")
            continue

        desc = exp.get("description", f"Uploaded expense {i+1}")
        payer_name = exp.get("payer", "")
        raw_amt = exp.get("amount")
        split_data = exp.get("split", {})

        if not payer_name or raw_amt is None:
            errors.append(f"expense[{i}]: missing payer or amount")
            continue

        try:
            amt = validate_amount(raw_amt)
            gm.add_expense(
                description=desc,
                payer_name=str(payer_name),
                amount=amt,
                split_data=split_data,
            )
        except SplitwiseError as e:
            errors.append(f"expense[{i}] ({desc}): {e}")

    if errors:
        return _render_dashboard(
            request, group_id,
            error=f"Uploaded with {len(expenses_data) - len(errors)} successes, {len(errors)} errors: {'; '.join(errors[:5])}",
        )

    return RedirectResponse(url=f"/group/{group_id}", status_code=303)


@app.get("/group/{group_id}/api/summary")
async def api_summary(group_id: str):
    """JSON API endpoint — returns full summary."""
    gm = _gm(group_id)
    return JSONResponse(content=gm.summary())


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return templates.TemplateResponse(
        "landing.html",
        {"request": request, "error": "Group not found — it may have been deleted or never existed."},
        status_code=404,
    )