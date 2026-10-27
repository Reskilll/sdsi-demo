"""Find-slot router (M4)."""
from datetime import datetime, date
from fastapi import APIRouter, HTTPException
from ..database import get_db
from ..engine import find_earliest_slot
from ..rooms import get_rooms
from ..models import FindSlotRequest, FindSlotResponse

router = APIRouter(prefix="/find-slot", tags=["find-slot"])


@router.post("", response_model=FindSlotResponse)
async def find_slot(body: FindSlotRequest):
    rooms = {r.name: r.capacity for r in get_rooms().values()}

    db = await get_db()
    try:
        # Load all bookings for the target date
        date_str = body.date.isoformat()
        async with db.execute(
            """SELECT * FROM bookings
               WHERE start_time >= ? AND start_time < ?
               ORDER BY start_time ASC""",
            (date_str, _next_day_str(body.date)),
        ) as cursor:
            rows = await cursor.fetchall()

        bookings = [dict(r) for r in rows]
        room_name, start, end = find_earliest_slot(
            body.date, body.duration_minutes, body.attendee_count, rooms, bookings
        )

        if room_name is None:
            return FindSlotResponse(available=False)

        return FindSlotResponse(available=True, room=room_name, start_time=start, end_time=end)
    finally:
        await db.close()


def _next_day_str(d: date) -> str:
    from datetime import timedelta
    return (d + timedelta(days=1)).isoformat()