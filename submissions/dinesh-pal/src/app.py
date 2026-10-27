"""
FastAPI application — REST API for the Inventory Reservation System.

Routes:
  POST /reserve        — Reserve stock (M2)
  POST /confirm        — Confirm reservation → permanent deduct (M3)
  POST /cancel         — Cancel reservation → release stock (M3)
  GET  /report/{sku}   — Single-SKU report (M5)
  GET  /report         — All-SKU report (M5)
  GET  /reservation/{id} — Look up one reservation
  GET  /health         — Health check

All endpoints include input validation via Pydantic.
The global engine is a module-level singleton initialised in the lifespan handler.
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from .engine import ReservationEngine
from .models import ErrorCode
from .schemas import (
    CancelRequest,
    ConfirmCancelRequest,
    ErrorDetail,
    InventoryReportResponse,
    ReservationResponse,
    ReserveRequest,
    SkuReportResponse,
)

# ── Global engine singleton ────────────────────────────────────────
_engine: ReservationEngine | None = None


def get_engine() -> ReservationEngine:
    """Safe accessor — fails fast if called before lifespan starts."""
    if _engine is None:
        raise RuntimeError("Engine not initialised — application did not start properly.")
    return _engine


# ── Lifespan ───────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _engine
    _engine = ReservationEngine()

    # Try to load inventory from a few standard locations
    candidates = [
        Path("inventory.json"),
        Path(__file__).resolve().parent.parent / "inventory.json",
    ]
    loaded = False
    for p in candidates:
        if p.exists():
            _engine.load_inventory(p)
            loaded = True
            break
    if not loaded:
        print("[app] WARNING: No inventory.json found; store is empty. Load via POST /admin/load-inventory or start from the project root.")

    _engine.start_sweeper()
    print("[app] Ready.")
    yield
    if _engine:
        _engine.stop()
        print("[app] Shutdown complete.")


# ── App ────────────────────────────────────────────────────────────


def create_app() -> FastAPI:
    app = FastAPI(
        title="Inventory Reservation System — Flash Sale Engine",
        version="1.0.0",
        description=(
            "Production-grade in-memory reservation engine with per-SKU locking, "
            "TTL-based expiry, per-user purchase limits, and idempotency-key safety."
        ),
        lifespan=lifespan,
    )

    # ── Exception handler: catch engine errors and map to 4xx ─────

    @app.exception_handler(Exception)
    async def catch_all(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={"error": "INTERNAL_ERROR", "message": str(exc)},
        )

    # ── M2: Reserve ───────────────────────────────────────────────

    @app.post("/reserve", response_model=ReservationResponse, status_code=201)
    async def reserve(body: ReserveRequest):
        """
        Reserve *quantity* of *sku* for *user_id*.

        The reservation is held for the configured TTL (default 120 s).
        During this window the stock is considered unavailable to others.

        **Idempotency**: pass `idempotency_key` to safely retry — the same
        key always returns the same result (the original reservation record
        or the original error).
        """
        eng = get_engine()
        success, result = eng.reserve(
            sku=body.sku,
            user_id=body.user_id,
            quantity=body.quantity,
            idempotency_key=body.idempotency_key,
        )
        if not success:
            status = 409 if result.get("error") in (
                ErrorCode.INSUFFICIENT_STOCK.value,
                ErrorCode.USER_LIMIT_EXCEEDED.value,
            ) else 404 if result["error"] == ErrorCode.SKU_NOT_FOUND.value else 400
            raise HTTPException(status_code=status, detail=result)

        return _to_reservation_response(result)

    # ── M3: Confirm ───────────────────────────────────────────────

    @app.post("/confirm", response_model=ReservationResponse)
    async def confirm(body: ConfirmCancelRequest):
        """Permanently deduct stock from a reservation.  Idempotent."""
        eng = get_engine()
        success, result = eng.confirm(
            reservation_id=body.reservation_id,
            idempotency_key=body.idempotency_key,
        )
        if not success:
            status = 409 if result["error"] == ErrorCode.RESERVATION_ALREADY_TERMINAL.value else 404
            raise HTTPException(status_code=status, detail=result)
        return _to_reservation_response(result)

    # ── M3: Cancel ────────────────────────────────────────────────

    @app.post("/cancel", response_model=ReservationResponse)
    async def cancel(body: CancelRequest):
        """Cancel a reservation — stock is released.  Idempotent."""
        eng = get_engine()
        success, result = eng.cancel(
            reservation_id=body.reservation_id,
            idempotency_key=body.idempotency_key,
        )
        if not success:
            status = 409 if result["error"] == ErrorCode.RESERVATION_ALREADY_TERMINAL.value else 404
            raise HTTPException(status_code=status, detail=result)
        return _to_reservation_response(result)

    # ── M5: Reports ───────────────────────────────────────────────

    @app.get("/report", response_model=InventoryReportResponse)
    async def report_all():
        """Real-time stock report for all SKUs."""
        eng = get_engine()
        reports = eng.report_all()
        return InventoryReportResponse(
            products=[
                SkuReportResponse(
                    sku=r.sku,
                    total_stock=r.total_stock,
                    sold=r.sold,
                    reserved=r.reserved,
                    available=r.available,
                    is_sold_out=r.is_sold_out,
                )
                for r in reports
            ]
        )

    @app.get("/report/{sku}", response_model=SkuReportResponse)
    async def report_sku(sku: str):
        """Real-time stock report for one SKU."""
        eng = get_engine()
        report = eng.report_sku(sku)
        if report is None:
            raise HTTPException(status_code=404, detail={"error": "SKU_NOT_FOUND", "message": f"SKU '{sku}' not found"})
        return SkuReportResponse(
            sku=report.sku,
            total_stock=report.total_stock,
            sold=report.sold,
            reserved=report.reserved,
            available=report.available,
            is_sold_out=report.is_sold_out,
        )

    # ── Lookup ───────────────────────────────────────────────────

    @app.get("/reservation/{reservation_id}", response_model=ReservationResponse)
    async def get_reservation(reservation_id: str):
        """Look up a reservation by ID."""
        eng = get_engine()
        record = eng.get_reservation(reservation_id)
        if record is None:
            raise HTTPException(
                status_code=404,
                detail={"error": "RESERVATION_NOT_FOUND", "message": f"Reservation '{reservation_id}' not found"},
            )
        return _to_reservation_response(record)

    # ── Health ───────────────────────────────────────────────────

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


# ── helpers ────────────────────────────────────────────────────────


def _to_reservation_response(record: Any) -> ReservationResponse:
    """Map an internal ReservationRecord to the API response model."""
    return ReservationResponse(
        reservation_id=record.reservation_id,
        sku=record.sku,
        user_id=record.user_id,
        quantity=record.quantity,
        state=record.state.value if hasattr(record.state, "value") else record.state,
        expires_at_iso=None,  # monotonic → wall-clock mapping is approximate
    )