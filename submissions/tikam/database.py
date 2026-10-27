"""SQLite database layer for the URL shortener.

Uses parameterized queries throughout to prevent SQL injection.
WAL mode for concurrent-read safety.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shortener.db")


def get_db() -> sqlite3.Connection:
    """Return a connection with row-factory and safety pragmas enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Create tables and indexes if they do not exist."""
    conn = get_db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS urls (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            short_code      TEXT    UNIQUE NOT NULL,
            original_url    TEXT    NOT NULL,
            normalized_url  TEXT    NOT NULL,
            is_custom       INTEGER DEFAULT 0,
            created_at      TEXT    DEFAULT (datetime('now')),
            expires_at      TEXT
        );

        CREATE TABLE IF NOT EXISTS clicks (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            short_code  TEXT NOT NULL,
            clicked_at  TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (short_code) REFERENCES urls(short_code)
        );

        CREATE INDEX IF NOT EXISTS idx_clicks_code
            ON clicks(short_code);

        CREATE INDEX IF NOT EXISTS idx_clicks_date
            ON clicks(short_code, clicked_at);

        CREATE INDEX IF NOT EXISTS idx_urls_normalized
            ON urls(normalized_url);
        """
    )
    conn.commit()
    conn.close()