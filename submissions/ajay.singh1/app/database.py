import os
import sqlite3
import asyncio
import aiosqlite
from datetime import datetime, date
from pathlib import Path


def _db_path() -> str:
    import app.config
    return app.config.DATABASE_PATH


async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(_db_path())
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db():
    """Create tables if they do not exist."""
    db = await get_db()
    try:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room TEXT NOT NULL,
                organiser TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                attendee_count INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_bookings_room_start_end
            ON bookings(room, start_time, end_time)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_bookings_start_time
            ON bookings(start_time)
        """)
        await db.commit()
    finally:
        await db.close()


def _parse_row(row: aiosqlite.Row | tuple | None) -> dict | None:
    if row is None:
        return None
    return {
        "id": row[0],
        "room": row[1],
        "organiser": row[2],
        "start_time": row[3],
        "end_time": row[4],
        "attendee_count": row[5],
        "created_at": row[6],
        "updated_at": row[7],
    }


async def find_conflicting_booking(
    db: aiosqlite.Connection, room: str, start_time: datetime, end_time: datetime,
    exclude_id: int | None = None
) -> dict | None:
    """Find a booking that overlaps [start_time, end_time) for the same room."""
    # Half-open interval: a booking A conflicts with new booking B iff
    # A.start < B.end AND A.end > B.start
    query = """
        SELECT * FROM bookings
        WHERE room = ?
          AND start_time < ?
          AND end_time > ?
    """
    params = [room, end_time.isoformat(), start_time.isoformat()]
    if exclude_id is not None:
        query += " AND id != ?"
        params.append(exclude_id)
    query += " LIMIT 1"

    async with db.execute(query, params) as cursor:
        row = await cursor.fetchone()
    return _parse_row(row)