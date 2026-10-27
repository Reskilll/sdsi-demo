"""Booking CRUD router."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from ..database import get_db, find_conflicting_booking
from ..engine import validate_booking_input, OVERLAP_ERROR
from ..models import (
    BookingCreate, BookingUpdate, BookingResponse, BookingList, ErrorResponse,
)

router = APIRouter(prefix="/bookings", tags=["bookings"])


async def _get_booking(db, booking_id: int) -> dict:
    async with db.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)) as cursor:
        row = await cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Booking {booking_id} not found")
    return dict(row)


def _row_to_response(row: dict) -> BookingResponse:
    return BookingResponse(
        id=row["id"],
        room=row["room"],
        organiser=row["organiser"],
        start_time=datetime.fromisoformat(row["start_time"]),
        end_time=datetime.fromisoformat(row["end_time"]),
        attendee_count=row["attendee_count"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


@router.post("", status_code=201, response_model=BookingResponse)
async def create_booking(body: BookingCreate):
    db = await get_db()
    try:
        validate_booking_input(body.room, body.attendee_count, body.start_time, body.end_time)

        # Lock the table to prevent race conditions
        await db.execute("BEGIN IMMEDIATE")

        conflict = await find_conflicting_booking(db, body.room, body.start_time, body.end_time)
        if conflict:
            await db.execute("ROLLBACK")
            raise HTTPException(status_code=409, detail=OVERLAP_ERROR)

        now = datetime.now(timezone.utc).isoformat()
        cursor = await db.execute(
            """INSERT INTO bookings (room, organiser, start_time, end_time, attendee_count, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (body.room, body.organiser, body.start_time.isoformat(),
             body.end_time.isoformat(), body.attendee_count, now, now),
        )
        booking_id = cursor.lastrowid
        await db.commit()

        row = await _get_booking(db, booking_id)
        return _row_to_response(row)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        await db.close()


@router.get("", response_model=BookingList)
async def list_bookings(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    room: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
):
    db = await get_db()
    try:
        conditions = []
        params: list = []

        if room:
            conditions.append("room = ?")
            params.append(room)
        if date_from:
            conditions.append("start_time >= ?")
            params.append(date_from)
        if date_to:
            conditions.append("end_time <= ?")
            params.append(date_to + "T23:59:59")

        where = ""
        if conditions:
            where = "WHERE " + " AND ".join(conditions)

        # Count total
        count_query = f"SELECT COUNT(*) FROM bookings {where}"
        async with db.execute(count_query, params) as cursor:
            total = (await cursor.fetchone())[0]

        # Paginate
        offset = (page - 1) * page_size
        data_query = f"SELECT * FROM bookings {where} ORDER BY start_time ASC LIMIT ? OFFSET ?"
        async with db.execute(data_query, params + [page_size, offset]) as cursor:
            rows = await cursor.fetchall()

        bookings = [_row_to_response(dict(r)) for r in rows]
        return BookingList(bookings=bookings, total=total, page=page, page_size=page_size)
    finally:
        await db.close()


@router.get("/{booking_id}", response_model=BookingResponse)
async def get_booking(booking_id: int):
    db = await get_db()
    try:
        row = await _get_booking(db, booking_id)
        return _row_to_response(row)
    finally:
        await db.close()


@router.put("/{booking_id}", response_model=BookingResponse)
async def update_booking(booking_id: int, body: BookingUpdate):
    db = await get_db()
    try:
        existing = await _get_booking(db, booking_id)
        existing_d = existing

        # Merge existing with provided fields
        room = body.room if body.room is not None else existing_d["room"]
        organiser = body.organiser if body.organiser is not None else existing_d["organiser"]
        start_time = body.start_time if body.start_time is not None else datetime.fromisoformat(existing_d["start_time"])
        end_time = body.end_time if body.end_time is not None else datetime.fromisoformat(existing_d["end_time"])
        attendee_count = body.attendee_count if body.attendee_count is not None else existing_d["attendee_count"]

        validate_booking_input(room, attendee_count, start_time, end_time)

        await db.execute("BEGIN IMMEDIATE")

        conflict = await find_conflicting_booking(db, room, start_time, end_time, exclude_id=booking_id)
        if conflict:
            await db.execute("ROLLBACK")
            raise HTTPException(status_code=409, detail=OVERLAP_ERROR)

        now = datetime.now(timezone.utc).isoformat()
        await db.execute(
            """UPDATE bookings SET room=?, organiser=?, start_time=?, end_time=?, attendee_count=?, updated_at=?
               WHERE id=?""",
            (room, organiser, start_time.isoformat(), end_time.isoformat(), attendee_count, now, booking_id),
        )
        await db.commit()

        row = await _get_booking(db, booking_id)
        return _row_to_response(row)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        await db.close()


@router.delete("/{booking_id}", status_code=204)
async def delete_booking(booking_id: int):
    db = await get_db()
    try:
        await _get_booking(db, booking_id)  # 404 if missing
        await db.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
        await db.commit()
    finally:
        await db.close()