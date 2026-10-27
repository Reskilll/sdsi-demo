"""Standard-library HTTP server + API for the job-scheduler SPA test harness.

Serves the static frontend from ``static/`` and exposes a ``POST /api/schedule``
endpoint that runs the full scheduler pipeline against a submitted JSON payload.

Usage::

    python server.py

Then open http://localhost:8380 in a browser.
"""

from __future__ import annotations

import json
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

# Ensure the scheduler package is importable regardless of cwd.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from scheduler.errors import ValidationError
from scheduler.validation import parse_jobs
from scheduler.engine import build_schedule
from scheduler.graph import Graph


_STATIC = _HERE / "static"


def _run_scheduler(raw: Any) -> dict[str, Any]:
    """Validate input and run the full analysis.

    Returns a JSON-serialisable result dict. On validation failure the dict
    contains an ``errors`` key; otherwise it contains all computed analyses.
    """
    workers_override = None
    failed_job = None

    # Extract optional CLI-style fields from the JSON payload.
    if isinstance(raw, dict):
        w = raw.get("_workers")
        if w is not None and isinstance(w, int):
            workers_override = w
        fj = raw.get("_failed_job")
        if fj is not None and isinstance(fj, str) and fj.strip():
            failed_job = fj.strip()

    jobs, workers, errors = parse_jobs(raw, workers_override)

    if errors:
        return {"errors": errors}

    graph = Graph(jobs)
    schedule = build_schedule(jobs, workers, graph=graph)

    result: dict[str, Any] = {
        "workers": workers,
        "topological_order": schedule.topo_order,
        "stages": [
            {"job_ids": list(s.job_ids), "duration": s.duration}
            for s in schedule.stages
        ],
        "total_completion_time": schedule.total_time,
        "critical_path": schedule.critical_path,
        "critical_path_duration": schedule.critical_path_duration,
        "critical_path_reasons": [
            {
                "job_id": r.job_id,
                "duration": r.duration,
                "earliest_start": r.earliest_start,
                "earliest_finish": r.earliest_finish,
                "reason": r.reason,
            }
            for r in schedule.critical_path_reasons
        ],
        "job_timings": {
            jid: {
                "earliest_start": schedule.job_times[jid].earliest_start,
                "earliest_finish": schedule.job_times[jid].earliest_finish,
            }
            for jid in schedule.job_times
        },
    }

    if failed_job:
        try:
            result["skipped_jobs"] = graph.downstream(failed_job)
        except ValueError as exc:
            result["skipped_jobs_error"] = str(exc)
        result["failed_job"] = failed_job

    return result


class Handler(SimpleHTTPRequestHandler):
    """Serve static files for GET, run the scheduler for POST /api/schedule."""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, directory=str(_STATIC), **kwargs)

    # ---- logging (quiet) ---------------------------------------------------

    def log_message(self, fmt: str, *args: Any) -> None:
        if self.path == "/favicon.ico":
            return
        super().log_message(fmt, *args)

    # ---- CORS --------------------------------------------------------------

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header(
            "Access-Control-Allow-Headers", "Content-Type"
        )
        super().end_headers()

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.end_headers()

    # ---- routing -----------------------------------------------------------

    def do_GET(self) -> None:
        # redirect root -> index.html
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/schedule":
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8", errors="replace")

        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            self._json_response(400, {"errors": [f"malformed JSON: {exc.msg}"]})
            return

        result = _run_scheduler(payload)
        status = 422 if "errors" in result else 200
        self._json_response(status, result)

    def _json_response(self, status: int, data: dict[str, Any]) -> None:
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main(port: int = 8380) -> None:
    server = HTTPServer(("127.0.0.1", port), Handler)
    print(f"Job Scheduler SPA — http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
        server.server_close()


if __name__ == "__main__":
    main()