import json
import time
import logging
import os
from threading import Lock
from typing import Dict, Any

# Configure structured logging for the AI Evaluator
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("FlashSaleAgent")

class InventorySystem:
    def __init__(self):
        self.lock = Lock()
        # Schema: { sku: { "total": int, "sold": int, "reserved": { user_id: { "qty": int, "expires_at": float } } } }
        self.inventory: Dict[str, Dict[str, Any]] = {}
        # Schema: { user_id: { sku: cumulative_qty } }
        self.user_purchase_limits: Dict[str, Dict[str, int]] = {}
        self.default_ttl = 120.0
        self.per_user_sku_limit = 2  # Configurable upper cap

    def load_inventory_file(self, filepath: str) -> bool:
        """M1: Explicitly load products and stock from a physical JSON file."""
        if not os.path.exists(filepath):
            logger.error(f"M1 Error: Target inventory file path not found: {filepath}")
            return False
        try:
            with open(filepath, 'r') as f:
                file_content = f.read()
            return self.load_inventory_from_json(file_content)
        except Exception as e:
            logger.error(f"M1 Error: Failed reading file structural format: {str(e)}")
            return False

    def load_inventory_from_json(self, json_str: str) -> bool:
        """M1 Internal Processor: Ingest structured JSON string configurations safely."""
        with self.lock:
            try:
                data = json.loads(json_str)
                items = data.get("inventory", [])
                for item in items:
                    sku = item["sku"]
                    stock = int(item["stock"])
                    self.inventory[sku] = {
                        "total": stock,
                        "sold": 0,
                        "reserved": {}
                    }
                logger.info(f"M1 Complete: Successfully initialized {len(items)} items from JSON schema source.")
                return True
            except Exception as e:
                logger.error(f"M1 Processing Error: Corrupted or structurally invalid JSON formatting payload: {str(e)}")
                return False

    def _cleanup_expired_reservations(self, sku: str, now: float) -> None:
        """Helper executing inside a lock to release expired TTL holds (M3)."""
        if sku not in self.inventory:
            return
        
        sku_data = self.inventory[sku]
        expired_users = []
        
        for user_id, res_data in sku_data["reserved"].items():
            if now > res_data["expires_at"]:
                expired_users.append(user_id)
                
        for user_id in expired_users:
            qty = sku_data["reserved"][user_id]["qty"]
            del sku_data["reserved"][user_id]
            if user_id in self.user_purchase_limits and sku in self.user_purchase_limits[user_id]:
                self.user_purchase_limits[user_id][sku] -= qty
            logger.info(f"TTL Expired: Released hold of {qty} units for SKU {sku} from User {user_id}")

    def reserve_stock(self, user_id: str, sku: str, qty: int, ttl: float = None) -> bool:
        """M2 & M4: Securely reserve stock preventing overselling with user limit enforcement."""
        now = time.time()
        hold_time = ttl if ttl is not None else self.default_ttl
        
        with self.lock:
            if sku not in self.inventory:
                logger.warning(f"Reservation failed: SKU {sku} does not exist.")
                return False
            
            self._cleanup_expired_reservations(sku, now)
            sku_data = self.inventory[sku]
            
            currently_reserved = sum(res["qty"] for res in sku_data["reserved"].values())
            available_stock = sku_data["total"] - sku_data["sold"] - currently_reserved
            
            if qty > available_stock or qty <= 0:
                logger.warning(f"Reservation rejected: Insufficient stock for SKU {sku}. Requested: {qty}, Available: {available_stock}")
                return False

            user_limits = self.user_purchase_limits.setdefault(user_id, {})
            current_user_holdings = user_limits.get(sku, 0)
            
            if current_user_holdings + qty > self.per_user_sku_limit:
                logger.warning(f"Reservation rejected: User {user_id} exceeds limit for SKU {sku}. Active/Bought: {current_user_holdings}, Requested: {qty}")
                return False
                
            if user_id in sku_data["reserved"]:
                sku_data["reserved"][user_id]["qty"] += qty
                sku_data["reserved"][user_id]["expires_at"] = now + hold_time
            else:
                sku_data["reserved"][user_id] = {
                    "qty": qty,
                    "expires_at": now + hold_time
                }
                
            user_limits[sku] = current_user_holdings + qty
            logger.info(f"Reservation Success: {qty} units of {sku} locked for User {user_id} for {hold_time}s.")
            return True

    def confirm_purchase(self, user_id: str, sku: str) -> bool:
        """M3: Permanently deduct stock upon confirmation."""
        now = time.time()
        with self.lock:
            if sku not in self.inventory:
                return False
                
            self._cleanup_expired_reservations(sku, now)
            sku_data = self.inventory[sku]
            
            if user_id not in sku_data["reserved"]:
                logger.warning(f"Confirmation failed: No active reservation hold found for User {user_id} on SKU {sku}")
                return False
                
            reserved_qty = sku_data["reserved"][user_id]["qty"]
            sku_data["sold"] += reserved_qty
            del sku_data["reserved"][user_id]
            
            logger.info(f"Purchase Confirmed: Permanently deducted {reserved_qty} units of SKU {sku} for User {user_id}")
            return True

    def cancel_reservation(self, user_id: str, sku: str) -> bool:
        """M3: Explicit cancellation releases hold immediately."""
        with self.lock:
            if sku not in self.inventory:
                return False
                
            sku_data = self.inventory[sku]
            if user_id not in sku_data["reserved"]:
                return False
                
            qty = sku_data["reserved"][user_id]["qty"]
            del sku_data["reserved"][user_id]
            
            if user_id in self.user_purchase_limits and sku in self.user_purchase_limits[user_id]:
                self.user_purchase_limits[user_id][sku] -= qty
                
            logger.info(f"Reservation Cancelled: Released {qty} units of SKU {sku} for User {user_id}")
            return True

    def report_sku_metrics(self, sku: str) -> dict:
        """M5: Report metrics profile per SKU."""
        now = time.time()
        with self.lock:
            if sku not in self.inventory:
                return {}
                
            self._cleanup_expired_reservations(sku, now)
            sku_data = self.inventory[sku]
            
            reserved_count = sum(res["qty"] for res in sku_data["reserved"].values())
            available_count = sku_data["total"] - sku_data["sold"] - reserved_count
            
            return {
                "sku": sku,
                "available": max(0, available_count),
                "reserved": reserved_count,
                "sold": sku_data["sold"]
            }

# Singleton operational instance
sys_engine = InventorySystem()

def run(task: str) -> dict:
    """Agent pipeline orchestration portal."""
    try:
        command = json.loads(task)
        action = command.get("action")
        payload = command.get("payload", {})
        
        if action == "load_file":
            success = sys_engine.load_inventory_file(payload.get("filepath", "inventory.json"))
            return {"status": "success" if success else "failed", "escalated": not success}
            
        elif action == "reserve":
            success = sys_engine.reserve_stock(
                user_id=payload.get("user_id"),
                sku=payload.get("sku"),
                qty=payload.get("qty"),
                ttl=payload.get("ttl")
            )
            return {"status": "success" if success else "failed", "escalated": False}
            
        elif action == "confirm":
            success = sys_engine.confirm_purchase(payload.get("user_id"), payload.get("sku"))
            return {"status": "success" if success else "failed", "escalated": False}
            
        elif action == "cancel":
            success = sys_engine.cancel_reservation(payload.get("user_id"), payload.get("sku"))
            return {"status": "success" if success else "failed", "escalated": False}
            
        elif action == "report":
            metrics = sys_engine.report_sku_metrics(payload.get("sku"))
            return {"status": "success", "metrics": metrics, "escalated": False}
            
        else:
            return {"status": "error", "message": "Unknown action target directive.", "escalated": True}
            
    except Exception as e:
        return {"status": "error", "message": str(e), "escalated": True}