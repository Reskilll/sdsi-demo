"""
FastAPI integration tests for the Inventory Reservation System.

Run:
    python -m pytest tests/test_api.py -v
"""

from __future__ import annotations

import threading
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def client():
    """Create a FastAPI app with a test store, return an async client."""
    from src.engine import ReservationEngine
    from src import app as app_module
    from src.models import Product
    from src.store import _MutableSku

    eng = ReservationEngine()
    p = Product(sku="SKU-A", name="Test Product", total_stock=50, per_user_limit=200)
    eng.store._skus["SKU-A"] = _MutableSku(product=p)
    eng.store._locks["SKU-A"] = threading.RLock()
    eng.start_sweeper()
    app_module._engine = eng

    from src.app import create_app

    app = create_app()
    app.router.lifespan = None  # disable default lifespan

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    eng.stop()


# ── Health ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ── Reserve ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reserve_success(client: AsyncClient):
    resp = await client.post(
        "/reserve",
        json={"sku": "SKU-A", "user_id": "alice", "quantity": 2},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["reservation_id"]
    assert data["sku"] == "SKU-A"
    assert data["state"] == "reserved"


@pytest.mark.asyncio
async def test_reserve_insufficient_stock(client: AsyncClient):
    """Request more than available stock — limit must be high enough to not block first."""
    resp = await client.post(
        "/reserve",
        json={"sku": "SKU-A", "user_id": "bob", "quantity": 51},
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["error"] == "INSUFFICIENT_STOCK"


@pytest.mark.asyncio
async def test_reserve_unknown_sku(client: AsyncClient):
    resp = await client.post(
        "/reserve", json={"sku": "NOPE", "user_id": "bob", "quantity": 1}
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_reserve_zero_quantity(client: AsyncClient):
    resp = await client.post(
        "/reserve", json={"sku": "SKU-A", "user_id": "bob", "quantity": 0}
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_reserve_missing_field(client: AsyncClient):
    resp = await client.post("/reserve", json={"user_id": "bob"})
    assert resp.status_code == 422


# ── Confirm ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_confirm_success(client: AsyncClient):
    r = await client.post(
        "/reserve",
        json={"sku": "SKU-A", "user_id": "charlie", "quantity": 3},
    )
    rid = r.json()["reservation_id"]
    resp = await client.post("/confirm", json={"reservation_id": rid})
    assert resp.status_code == 200
    assert resp.json()["state"] == "sold"


@pytest.mark.asyncio
async def test_confirm_nonexistent(client: AsyncClient):
    resp = await client.post("/confirm", json={"reservation_id": "nonexistent-id"})
    assert resp.status_code == 404


# ── Cancel ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cancel_success(client: AsyncClient):
    r = await client.post(
        "/reserve", json={"sku": "SKU-A", "user_id": "dave", "quantity": 1}
    )
    rid = r.json()["reservation_id"]
    resp = await client.post("/cancel", json={"reservation_id": rid})
    assert resp.status_code == 200
    assert resp.json()["state"] == "released"


# ── Reports ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_report_all(client: AsyncClient):
    resp = await client.get("/report")
    assert resp.status_code == 200
    data = resp.json()
    assert "products" in data


@pytest.mark.asyncio
async def test_report_single_sku(client: AsyncClient):
    resp = await client.get("/report/SKU-A")
    assert resp.status_code == 200
    data = resp.json()
    assert data["sku"] == "SKU-A"
    assert data["total_stock"] == 50


@pytest.mark.asyncio
async def test_report_unknown_sku(client: AsyncClient):
    resp = await client.get("/report/NOPE")
    assert resp.status_code == 404


# ── Idempotency ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_api_idempotent_reserve(client: AsyncClient):
    body = {
        "sku": "SKU-A",
        "user_id": "eve",
        "quantity": 1,
        "idempotency_key": "ikey-api-1",
    }
    r1 = await client.post("/reserve", json=body)
    r2 = await client.post("/reserve", json=body)
    assert r1.status_code == r2.status_code == 201
    assert r1.json()["reservation_id"] == r2.json()["reservation_id"]


# ── Reservation lookup ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_reservation(client: AsyncClient):
    r = await client.post(
        "/reserve", json={"sku": "SKU-A", "user_id": "frank", "quantity": 1}
    )
    rid = r.json()["reservation_id"]
    resp = await client.get(f"/reservation/{rid}")
    assert resp.status_code == 200
    assert resp.json()["reservation_id"] == rid


@pytest.mark.asyncio
async def test_get_nonexistent_reservation(client: AsyncClient):
    resp = await client.get("/reservation/nope")
    assert resp.status_code == 404