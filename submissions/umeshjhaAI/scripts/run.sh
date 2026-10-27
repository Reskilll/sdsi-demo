#!/usr/bin/env bash
# Launch the Job Scheduler SPA: start the backend server and open the frontend.
#
# Usage:  ./scripts/run.sh [port]
#
# The single server (server.py) serves both the static frontend (GET /) and
# the scheduler API (POST /api/schedule), so this one command runs everything.
set -euo pipefail

# Resolve the project root (one level up from this script's directory).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

PORT="${1:-8380}"

# Pick a Python interpreter: respect PYTHON, then `python3`, then `python`.
PYTHON_BIN="${PYTHON:-}"
if [ -z "$PYTHON_BIN" ]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN=python3
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN=python
  else
    echo "error: no Python interpreter found (tried python3, python)" >&2
    exit 1
  fi
fi

URL="http://localhost:${PORT}"

# Open the browser (best-effort; the server keeps running either way).
open_browser() {
  case "$(uname -s 2>/dev/null || echo Windows)" in
    Darwin)  open "$URL" ;;
    Linux)   xdg-open "$URL" >/dev/null 2>&1 || true ;;
    *)       cmd.exe /c start "" "$URL" >/dev/null 2>&1 || true ;;
  esac
}

(
  # Give the server a moment to bind before opening the browser.
  sleep 1
  open_browser
) &

cd "$ROOT_DIR"
echo "Starting Job Scheduler SPA on ${URL} ..."
exec "$PYTHON_BIN" server.py "$PORT"
