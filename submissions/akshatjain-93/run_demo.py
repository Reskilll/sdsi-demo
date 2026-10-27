#!/usr/bin/env python3
"""Entry point script to run the flash sale demo and verify all requirements."""

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from flash_sale.cli import run_flash_sale_simulation

if __name__ == "__main__":
    inventory_path = Path(__file__).resolve().parent / "inventory.json"
    run_flash_sale_simulation(str(inventory_path), concurrent_users=40)

