import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "bookings.db"))
ROOMS_PATH = os.getenv("ROOMS_PATH", str(BASE_DIR / "rooms.json"))
MAX_RECURRENCE_OCCURRENCES = int(os.getenv("MAX_RECURRENCE_OCCURRENCES", "52"))
WORKING_HOURS_START = int(os.getenv("WORKING_HOURS_START", "9"))
WORKING_HOURS_END = int(os.getenv("WORKING_HOURS_END", "18"))