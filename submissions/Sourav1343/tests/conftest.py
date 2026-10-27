"""Pytest configuration — makes the submission root importable.

All tests import ``engine`` and refer to ``rooms.json`` relative to the
submission root, so we add that directory to ``sys.path`` and switch the
working directory there before collecting tests.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# The submission root is one level above this file (tests/).
SUBMISSION_ROOT = Path(__file__).resolve().parent.parent

if str(SUBMISSION_ROOT) not in sys.path:
    sys.path.insert(0, str(SUBMISSION_ROOT))

# Ensure relative paths like "rooms.json" resolve to the submission root.
os.chdir(SUBMISSION_ROOT)