"""
FastAPI web app for SLA Tracker.
Endpoints: GET / (dashboard), GET /api/report (JSON), GET /api/summary (JSON)
"""

import json
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from engine import SLAEngine

ROOT  = Path(__file__).parent
DATA  = ROOT / "data"
TMPL  = ROOT / "templates"

# ---- load data -----------------------------------------------------------
with open(DATA / "sla_policy.json") as f:
    SLA_POLICY = json.load(f)
with open(DATA / "holidays.json") as f:
    HOLIDAYS = json.load(f)

engine = SLAEngine(SLA_POLICY, HOLIDAYS)

# ---- FastAPI app ---------------------------------------------------------
app = FastAPI(title="SLA Tracker", version="1.0.0")
templates = Jinja2Templates(directory=str(TMPL))


def _load_tickets() -> list[dict]:
    try:
        with open(DATA / "tickets.json") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise HTTPException(500, f"Cannot load tickets: {e}")


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    tickets = _load_tickets()
    reports = [engine.compute(t) for t in tickets]
    summary = engine.summary(reports)
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "reports": reports, "summary": summary, "tickets": tickets},
    )


@app.get("/api/report")
async def api_report():
    tickets = _load_tickets()
    return [engine.compute(t) for t in tickets]


@app.get("/api/summary")
async def api_summary():
    tickets = _load_tickets()
    reports = [engine.compute(t) for t in tickets]
    return engine.summary(reports)


@app.get("/api/ticket/{ticket_id}")
async def api_ticket(ticket_id: str):
    tickets = _load_tickets()
    for t in tickets:
        if t["id"].upper() == ticket_id.upper():
            return engine.compute(t)
    raise HTTPException(404, f"Ticket {ticket_id} not found")


if __name__ == "__main__":
#    import uvicorn
#    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)