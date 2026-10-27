"""
Entry-point: ``python -m src.main`` or ``python main.py``.

Starts the FastAPI server with uvicorn.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inventory Reservation System — Flash Sale Engine",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Bind address (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Bind port (default: 8000)",
    )
    parser.add_argument(
        "--inventory",
        default="inventory.json",
        help="Path to inventory JSON file (default: inventory.json)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable uvicorn auto-reload (dev only)",
    )
    args = parser.parse_args()

    import uvicorn

    # If a non-default inventory file is given, set an env var for the app to pick up
    if args.inventory != "inventory.json":
        import os

        os.environ["INVENTORY_PATH"] = str(Path(args.inventory).resolve())

    uvicorn.run(
        "src.app:create_app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        factory=True,
    )


if __name__ == "__main__":
    main()