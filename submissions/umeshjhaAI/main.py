"""Command-line entry point for the mini job scheduler.

Usage:
    python main.py --input sample.json
    python main.py --input sample.json --workers 2
    python main.py --input sample.json --failed-job transform
    python main.py --input sample.json --format json
"""

import sys

from scheduler.cli import main

if __name__ == "__main__":
    sys.exit(main())
