"""
Reservation Engine — thin orchestration layer.

This is the public API consumed by the HTTP layer.  It owns:
- Store initialization (loading inventory.json)
- Reservation lifecycle (reserve → confirm/cancel/expire)
- Report queries
- Lifecycle management (start/stop sweeper)

All thread-safety lives in StateStore; this layer adds no locks of its own.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import Product, ReservationRecord, SkuReport, SystemConfig
from .store import StateStore
from .sweeper import Sweeper


class ReservationEngine:
    """Top-level entry-point for the reservation system."""

    def __init__(self, config: Optional[SystemConfig] = None) -> None:
        self.config = config or SystemConfig()
        self.store = StateStore(self.config)
        self.sweeper = Sweeper(
            store=self.store,
            interval_seconds=self.config.sweeper_interval_seconds,
        )

    # ── bootstrap ─────────────────────────────────────────────────

    def load_inventory(self, path: str | Path) -> None:
        """Parse inventory.json and populate the store.  Call once at startup."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Inventory file not found: {path}")

        data = json.loads(path.read_text(encoding="utf-8"))

        # Merge config overrides from the file
        file_config = data.get("config", {})
        ttl = file_config.get("reservation_ttl_seconds")
        if ttl is not None:
            self.config = SystemConfig(
                reservation_ttl_seconds=float(ttl),
                sweeper_interval_seconds=file_config.get(
                    "sweeper_interval_seconds",
                    self.config.sweeper_interval_seconds,
                ),
                idempotency_ttl_seconds=file_config.get(
                    "idempotency_ttl_seconds",
                    self.config.idempotency_ttl_seconds,
                ),
            )
            # Rebuild store and sweeper with new config
            self.store = StateStore(self.config)
            self.sweeper = Sweeper(
                store=self.store,
                interval_seconds=self.config.sweeper_interval_seconds,
            )

        products = [
            Product(
                sku=p["sku"],
                name=p["name"],
                total_stock=p["total_stock"],
                per_user_limit=p["per_user_limit"],
            )
            for p in data["products"]
        ]
        self.store.load_products(products)

    def start_sweeper(self) -> None:
        self.sweeper.start()

    def stop(self) -> None:
        self.sweeper.stop()

    # ── API ───────────────────────────────────────────────────────

    def reserve(
        self,
        sku: str,
        user_id: str,
        quantity: int,
        idempotency_key: Optional[str] = None,
    ) -> tuple[bool, Any]:
        return self.store.reserve(sku, user_id, quantity, idempotency_key)

    def confirm(
        self,
        reservation_id: str,
        idempotency_key: Optional[str] = None,
    ) -> tuple[bool, Any]:
        return self.store.confirm(reservation_id, idempotency_key)

    def cancel(
        self,
        reservation_id: str,
        idempotency_key: Optional[str] = None,
    ) -> tuple[bool, Any]:
        return self.store.cancel(reservation_id, idempotency_key)

    def report_sku(self, sku: str) -> Optional[SkuReport]:
        return self.store.report_sku(sku)

    def report_all(self) -> List[SkuReport]:
        return self.store.report_all()

    def get_reservation(self, reservation_id: str) -> Optional[ReservationRecord]:
        return self.store.get_reservation(reservation_id)