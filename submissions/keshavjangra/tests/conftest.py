# Shared test fixtures and configuration
import sys
from pathlib import Path

# Make sure the scheduler package is importable from the tests directory
_src = Path(__file__).resolve().parent.parent
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))