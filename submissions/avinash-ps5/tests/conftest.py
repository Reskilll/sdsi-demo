import sys
from pathlib import Path

# Add the submission root to PYTHONPATH so 'dag_scheduler' can be imported
_submission_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_submission_root))