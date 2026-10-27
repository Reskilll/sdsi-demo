"""
Thread-safe SQLite3 WAL Database Interface & Schema Management
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Generator

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "shortener.db"


def get_db_path() -> Path:
    """Resolves database path from environment variable or default location."""
    env_path = os.getenv("SQLITE_DB_PATH") or os.getenv("DATABASE_URL")
    if env_path:
        # If passed as sqlite:///path, strip sqlite prefix
        if env_path.startswith("sqlite:///"):
            env_path = env_path[10:]
        elif env_path.startswith("sqlite://"):
            env_path = env_path[9:]
        return Path(env_path).resolve()
    return DEFAULT_DB_PATH


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Returns a SQLite connection configured with WAL mode and high-concurrency pragmas."""
    target_path = db_path or get_db_path()
    conn = sqlite3.connect(target_path, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA busy_timeout=5000;")
    return conn


def init_db(db_path: Path | None = None) -> None:
    """Initializes tables, indexes, and constraints."""
    target_path = db_path or get_db_path()
    with get_connection(target_path) as conn:
        # URLs table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS urls (
                code TEXT PRIMARY KEY,
                original_url TEXT NOT NULL,
                canonical_hash TEXT NOT NULL,
                is_custom_alias INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                expires_at TEXT,
                total_clicks INTEGER NOT NULL DEFAULT 0,
                last_accessed_at TEXT,
                escalated INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_urls_canonical ON urls (canonical_hash, is_custom_alias);"
        )

        # Clicks Daily table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS clicks_daily (
                code TEXT NOT NULL REFERENCES urls(code) ON DELETE CASCADE,
                date_bucket TEXT NOT NULL,
                click_count INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (code, date_bucket)
            );
            """
        )

        # Security Audit Log table (tamper-evident SHA-256 chain)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS security_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                escalated INTEGER NOT NULL,
                prev_hash TEXT NOT NULL,
                curr_hash TEXT NOT NULL
            );
            """
        )

        # General Audit Logs table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                task_hash TEXT NOT NULL,
                prev_hash TEXT NOT NULL,
                record_hash TEXT NOT NULL,
                confidence_score REAL NOT NULL,
                risk_score REAL NOT NULL,
                escalated INTEGER NOT NULL,
                decision TEXT NOT NULL
            );
            """
        )
        conn.commit()
