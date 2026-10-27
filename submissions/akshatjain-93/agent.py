"""Flash sale agent runner for the SDSI Agentic AI platform."""

from pathlib import Path
from typing import Dict, Any

from flash_sale import FlashSaleEngine


def run(task: str) -> Dict[str, Any]:
    """Agent entry point matching agent-template schema."""
    inventory_path = Path(__file__).resolve().parent / "inventory.json"
    engine = FlashSaleEngine(inventory_source=str(inventory_path), default_ttl=120)
    summary = engine.get_system_summary()
    reports = {sku: rep.to_dict() for sku, rep in engine.get_all_reports().items()}
    engine.shutdown()

    return {
        "plan": [
            "Load inventory from sample input file (M1)",
            "Initialize thread-safe reservation engine with 120s TTL (M2)",
            "Configure confirmation, cancellation, and auto-expiry lifecycle (M3)",
            "Enforce per-user purchase limits per SKU (M4)",
            "Generate real-time stock reports maintaining invariant (M5)",
        ],
        "result": {
            "status": "READY",
            "task": task,
            "summary": summary,
            "products": reports,
        },
        "escalated": False,
    }
