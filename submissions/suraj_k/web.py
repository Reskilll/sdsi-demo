#!/usr/bin/env python3
"""
Web launcher for the Splitwise-Lite expense settler.

Starts the FastAPI web server with uvicorn.

Usage:
    python web.py              # default: localhost:8000
    python web.py --port 3000  # custom port
    python web.py --reload     # auto-reload on code change (dev mode)
"""

from __future__ import annotations

import argparse
import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Splitwise-Lite web server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()

    uvicorn.run(
        "src.web.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()