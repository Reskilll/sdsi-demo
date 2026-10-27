"""SLA Breach Agent – entry point.

Usage:
    python main.py                    # use tickets/sla/holidays from this dir
    python main.py /path/to/data      # load JSON files from another directory
"""

import json
import sys
from pathlib import Path

from sla_engine import run

if __name__ == "__main__":
    data_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    output = run(data_dir)

    print(json.dumps(output["result"], indent=2, default=str))

    if output["escalated"]:
        print("\n⚠️  ESCALATION: One or more tickets breached SLA.")
    else:
        print("\n✓ All tickets within SLA targets.")