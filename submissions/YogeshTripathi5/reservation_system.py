"""Core inventory reservation engine — thread-safe, lock-based, in-memory."""

import json
import threading
import time
import uuid


class InventoryReservationSystem:
    """Manages PS4 product inventory: reserve → confirm/cancel/expire cycle.

    Thread-safe via reentrant lock. Expiry is lazy (checked on every mutating
    operation) — no background timer needed.
    """

    def __init__(self, inventory_path=None, default_ttl=120, data=None):
        self._lock = threading.RLock()
        self._default_ttl = default_ttl

        # Products keyed by SKU
        self._products = {}
        if data:
            self._products = data
        elif inventory_path:
            self._load_inventory(inventory_path)

        # reservation_id -> reservation record
        self._reservations = {}

        # (user_id, sku) -> total quantity across active reservations + confirmed purchases
        self._user_sku_counts = {}

    # ------------------------------------------------------------------ loading

    def _load_inventory(self, path):
        with open(path) as f:
            raw = json.load(f)
        if not isinstance(raw, list):
            raise ValueError("inventory JSON must be a list of items")
        for item in raw:
            sku = item.get("sku")
            if not sku:
                raise ValueError("each inventory item must have a 'sku' field")
            stock = item.get("stock", 0)
            if not isinstance(stock, int) or stock < 0:
                raise ValueError(f"invalid stock for SKU {sku!r}")
            self._products[sku] = {
                "name": item.get("name", ""),
                "total": stock,
                "reserved": 0,
                "sold": 0,
            }

    # ------------------------------------------------------------- expiry sweep

    def _clean_expired(self):
        now = time.monotonic()
        expired = [
            rid for rid, r in self._reservations.items()
            if r["status"] == "active" and r["expires_at"] <= now
        ]
        for rid in expired:
            r = self._reservations[rid]
            self._products[r["sku"]]["reserved"] -= r["qty"]
            r["status"] = "expired"
            self._decr_user_sku_count(r["user_id"], r["sku"], r["qty"])

    # ------------------------------------------------------ per-user SKU counts

    def _incr_user_sku_count(self, user_id, sku, qty):
        key = (user_id, sku)
        self._user_sku_counts[key] = self._user_sku_counts.get(key, 0) + qty

    def _decr_user_sku_count(self, user_id, sku, qty):
        key = (user_id, sku)
        self._user_sku_counts[key] = self._user_sku_counts.get(key, 0) - qty
        if self._user_sku_counts[key] <= 0:
            del self._user_sku_counts[key]

    # ------------------------------------------------------------------- public

    def products(self):
        """Return full product listing."""
        with self._lock:
            return {
                sku: {
                    "sku": sku,
                    "name": p["name"],
                    "total": p["total"],
                    "reserved": p["reserved"],
                    "sold": p["sold"],
                    "available": p["total"] - p["reserved"] - p["sold"],
                }
                for sku, p in self._products.items()
            }

    def product(self, sku):
        """Return a single product or None."""
        with self._lock:
            self._clean_expired()
            p = self._products.get(sku)
            if p is None:
                return None
            return {
                "sku": sku,
                "name": p["name"],
                "total": p["total"],
                "reserved": p["reserved"],
                "sold": p["sold"],
                "available": p["total"] - p["reserved"] - p["sold"],
            }

    def reserve(self, sku, user_id, quantity=1, ttl=None, purchase_limit=None):
        """Reserve *quantity* of *sku* for *user_id*.

        Returns dict with ``success`` bool, ``reservation_id`` on success,
        ``error`` message on failure.
        """
        if not sku or not user_id:
            return {"success": False, "error": "sku and user_id are required"}
        if not isinstance(quantity, int) or quantity <= 0:
            return {"success": False, "error": "quantity must be a positive integer"}

        with self._lock:
            self._clean_expired()

            p = self._products.get(sku)
            if p is None:
                return {"success": False, "error": f"unknown SKU: {sku}"}

            available = p["total"] - p["reserved"] - p["sold"]
            if available < quantity:
                return {
                    "success": False,
                    "error": f"insufficient stock: requested {quantity}, available {available}",
                }

            if purchase_limit is not None:
                key = (user_id, sku)
                held = self._user_sku_counts.get(key, 0)
                if held + quantity > purchase_limit:
                    return {
                        "success": False,
                        "error": (
                            f"purchase limit of {purchase_limit} exceeded: "
                            f"already have {held}, requesting {quantity}"
                        ),
                    }

            rid = str(uuid.uuid4())
            effective_ttl = ttl if ttl is not None else self._default_ttl
            self._reservations[rid] = {
                "id": rid,
                "sku": sku,
                "user_id": user_id,
                "qty": quantity,
                "expires_at": time.monotonic() + effective_ttl,
                "status": "active",
            }
            p["reserved"] += quantity
            self._incr_user_sku_count(user_id, sku, quantity)

            return {
                "success": True,
                "reservation_id": rid,
                "expires_in_seconds": effective_ttl,
            }

    def confirm(self, reservation_id):
        """Atomically convert a reservation to a confirmed purchase (deducts stock)."""
        with self._lock:
            self._clean_expired()

            r = self._reservations.get(reservation_id)
            if r is None:
                return {"success": False, "error": "reservation not found"}

            if r["status"] == "confirmed":
                return {"success": False, "error": "reservation already confirmed"}
            if r["status"] == "cancelled":
                return {"success": False, "error": "reservation already cancelled"}
            if r["status"] == "expired":
                return {"success": False, "error": "reservation has expired"}
            if r["status"] != "active":
                return {"success": False, "error": f"reservation in state '{r['status']}' cannot be confirmed"}

            sku = r["sku"]
            qty = r["qty"]
            p = self._products.get(sku)
            if p is None:
                return {"success": False, "error": "inconsistent state: product missing"}

            if p["reserved"] < qty:
                return {"success": False, "error": "inconsistent state: reserved count mismatch"}

            p["reserved"] -= qty
            p["sold"] += qty
            r["status"] = "confirmed"
            return {"success": True, "sku": sku, "quantity": qty}

    def cancel(self, reservation_id):
        """Cancel an active reservation and release its stock."""
        with self._lock:
            self._clean_expired()

            r = self._reservations.get(reservation_id)
            if r is None:
                return {"success": False, "error": "reservation not found"}

            if r["status"] == "cancelled":
                return {"success": False, "error": "reservation already cancelled"}
            if r["status"] == "confirmed":
                return {"success": False, "error": "cannot cancel a confirmed reservation"}
            if r["status"] == "expired":
                return {"success": False, "error": "reservation has expired"}
            if r["status"] != "active":
                return {"success": False, "error": f"reservation in state '{r['status']}' cannot be cancelled"}

            p = self._products[r["sku"]]
            p["reserved"] -= r["qty"]
            r["status"] = "cancelled"
            self._decr_user_sku_count(r["user_id"], r["sku"], r["qty"])
            return {"success": True, "sku": r["sku"], "quantity": r["qty"]}

    def reservation(self, reservation_id):
        """Look up a reservation by ID."""
        with self._lock:
            r = self._reservations.get(reservation_id)
            if r is None:
                return None
            return dict(r)