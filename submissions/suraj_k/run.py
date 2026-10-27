#!/usr/bin/env python3
"""
Convenience launcher for the Splitwise-Lite expense settler.

Usage:
    python run.py input.json
    python run.py batch/input_directory/
    python run.py --stdin
"""

from src.cli import main

if __name__ == "__main__":
    raise SystemExit(main())