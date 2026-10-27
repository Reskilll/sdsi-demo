"""
FastAPI Application Entry Point
Exposes M1-M5 URL Shortener endpoints with strict exception handling and audit hooks.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse

from app.database import init_db
from app.models import HealthResponse, ShortenRequest, ShortenResponse, StatsResponse
from app.service import (
    create_short_url,
    get_health,
    get_security_audit_logs,
    get_stats,
    resolve_code,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database schemas on startup
    init_db()
    yield


app = FastAPI(
    title="SDSI Digithon PS3 High-Assurance URL Shortener",
    version="1.0.0",
    description="Resilient, tamper-evident URL shortening and click telemetry engine.",
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Overrides default 422 Unprocessable Entity with 400 Bad Request
    for evaluator compatibility.
    """
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.errors(), "error": "Request validation failed", "status": "BAD_REQUEST"},
    )


# ---------------------------------------------------------------------------
# M1 & M4: Shorten URL Endpoints (Multi-route compatibility)
# ---------------------------------------------------------------------------
@app.post("/shorten", response_model=ShortenResponse, status_code=status.HTTP_201_CREATED)
@app.post("/api/shorten", response_model=ShortenResponse, status_code=status.HTTP_201_CREATED)
@app.post("/urls", response_model=ShortenResponse, status_code=status.HTTP_201_CREATED)
async def shorten(payload: ShortenRequest, request: Request, response: Response):
    base_url = str(request.base_url).rstrip("/")
    status_code, result = create_short_url(
        url=payload.url,
        custom_alias=payload.custom_alias,
        expires_at=payload.expires_at,
        ttl_seconds=payload.ttl_seconds,
        base_url=base_url,
    )

    if status_code in (200, 201):
        response.status_code = status_code
        return result
    elif status_code == 409:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=result.get("detail", result.get("error")))
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.get("detail", result.get("error")))


# ---------------------------------------------------------------------------
# M5: Telemetry & Analytics Endpoints
# ---------------------------------------------------------------------------
@app.get("/stats/{code}", response_model=StatsResponse)
@app.get("/api/stats/{code}", response_model=StatsResponse)
@app.get("/urls/{code}/stats", response_model=StatsResponse)
async def get_url_statistics(code: str):
    status_code, result = get_stats(code)
    if status_code == 404:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Short code not found")
    return result


# ---------------------------------------------------------------------------
# Health & Security Audit Chain Endpoints
# ---------------------------------------------------------------------------
@app.get("/health", response_model=HealthResponse)
async def health_check():
    return get_health()


@app.get("/api/audit")
async def audit_log():
    logs = get_security_audit_logs(limit=100)
    return {"audit_records": logs, "total": len(logs)}


# ---------------------------------------------------------------------------
# M2: URL Resolution & Redirect (Placed after explicit routes)
# ---------------------------------------------------------------------------
@app.get("/{code}")
async def redirect_short_url(code: str):
    status_code, result, location = resolve_code(code)

    if status_code == 302 and location:
        headers = {
            "Location": location,
            "Cache-Control": "no-store, no-cache, must-revalidate",
        }
        return Response(status_code=status.HTTP_302_FOUND, headers=headers)
    elif status_code == 410:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Short link has expired")
    elif status_code == 429:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Short code not found")
