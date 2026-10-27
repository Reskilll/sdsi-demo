"""Recurrence router (M5)."""
from datetime import datetime, date, timezone
from fastapi import APIRouter, HTTPException
from ..database import get_db, find_conflicting_booking
from ..engine import (
    validate_booking_input,
    generate_recurrence_dates,
    build_occurrence_datetimes,
    OVERLAP_ERROR,
    CAPACITY_EXCEEDED,
    ROOM_NOT_FOUND,
)
from ..models import (
    RecurrenceRequest, RecurrenceResponse, RecurrenceOccurrenceResult,
    ConflictInfo, BookingResponse,
)

router = APIRouter(prefix="/bookings/recurring", tags=["recurrence"])


@router.post("", status_code=201, response_model=RecurrenceResponse)
async def create_recurring(body: RecurrenceRequest):
    # First validate template input
    try:
        validate_booking_input(body.room, body.attendee_count, body.start_time, body.end_time)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    dates = generate_recurrence_dates(body.recurrence_start, body.recurrence_end)
    if not dates:
        raise HTTPException(status_code=400, detail="No recurrence dates generated")

    db = await get_db()
    try:
        created: list[RecurrenceOccurrenceResult] = []
        conflicts: list[RecurrenceOccurrenceResult] = []
        failures: list[RecurrenceOccurrenceResult] = []

        for target_date in dates:
            occ_start, occ_end = build_occurrence_datetimes(body.start_time, body.end_time, target_date)

            # Validate this occurrence
            try:
                validate_booking_input(body.room, body.attendee_count, occ_start, occ_end)
            except ValueError as e:
                failures.append(RecurrenceOccurrenceResult(
                    date=target_date, error=str(e),
                ))
                continue

            # Check for conflicts within a transaction
            await db.execute("BEGIN IMMEDIATE")
            conflict = await find_conflicting_booking(db, body.room, occ_start, occ_end)
            if conflict:
                await db.execute("ROLLBACK")
                conflicts.append(RecurrenceOccurrenceResult(
                    date=target_date,
                    conflict=ConflictInfo(
                        booking_id=conflict["id"],
                        room=conflict["room"],
                        start_time=datetime.fromisoformat(conflict["start_time"]),
                        end_time=datetime.fromisoformat(conflict["end_time"]),
                    ),
                ))
                continue

            # Insert this occurrence
            now = datetime.now(timezone.utc).isoformat()
            cursor = await db.execute(
                """INSERT INTO bookings (room, organiser, start_time, end_time, attendee_count, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (body.room, body.organiser, occ_start.isoformat(), occ_end.isoformat(),
                 body.attendee_count, now, now),
            )
            booking_id = cursor.lastrowid
            await db.commit()

            created.append(RecurrenceOccurrenceResult(
                date=target_date,
                booking=BookingResponse(
                    id=booking_id,
                    room=body.room,
                    organiser=body.organiser,
                    start_time=occ_start,
                    end_time=occ_end,
                    attendee_count=body.attendee_count,
                    created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
                ),
            ))

        return RecurrenceResponse(created=created, conflicts=conflicts, failures=failures)
    finally:
        await db.close()