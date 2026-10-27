"""FastAPI app: Meeting Room Booking Engine."""
from datetime import date, datetime, timedelta
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status

from .models import Booking, BookingCreate, BookingUpdate, Room
from .service import BookingService
from .store import Store

BASE = Path(__file__).parent


def default_store() -> Store:
    return Store(BASE / "rooms.json", BASE / "bookings.json")


def default_service() -> BookingService:
    return BookingService(default_store())


def get_store(request: Request) -> Store:
    store = getattr(request.app.state, "store", None)
    if store is None:
        store = default_store()
        request.app.state.store = store
    return store


def get_service(request: Request) -> BookingService:
    service = getattr(request.app.state, "service", None)
    if service is None:
        service = BookingService(get_store(request))
        request.app.state.service = service
    return service


app = FastAPI(title="Meeting Room Booking Engine")


def _require_room(store: Store, room_id: str) -> Room:
    room = store.get_room(room_id)
    if room is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"unknown room '{room_id}'")
    return room


def _require_booking(service: BookingService, booking_id: str) -> Booking:
    booking = service.existing(booking_id)
    if booking is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"unknown booking '{booking_id}'")
    return booking


def _conflict_exc(conflicts) -> HTTPException:
    return HTTPException(
        status.HTTP_409_CONFLICT,
        detail={
            "message": "booking conflicts with an existing booking",
            "conflicts": [c.model_dump(mode="json") for c in conflicts],
        },
    )


@app.get("/rooms", response_model=list[Room])
def list_rooms(store: Store = Depends(get_store)):
    return list(store.rooms.values())


@app.post("/bookings", response_model=Booking, status_code=status.HTTP_201_CREATED)
def create_booking(data: BookingCreate, store: Store = Depends(get_store),
                   service: BookingService = Depends(get_service)):
    _require_room(store, data.room_id)
    booking = service.create(data)
    result = service.validate(booking)
    if not result.ok:
        service.delete(booking.id)
        raise _conflict_exc(result.conflicts)
    return booking


@app.get("/bookings", response_model=list[Booking])
def list_bookings(
    room_id: str | None = None,
    start_from: datetime | None = Query(default=None, alias="from"),
    start_to: datetime | None = Query(default=None, alias="to"),
    store: Store = Depends(get_store),
):
    result = store.list_bookings()
    if room_id:
        result = [b for b in result if b.room_id == room_id]
    if start_from:
        result = [b for b in result if b.start >= start_from]
    if start_to:
        result = [b for b in result if b.start <= start_to]
    return result


@app.get("/bookings/{booking_id}", response_model=Booking)
def get_booking(booking_id: str, service: BookingService = Depends(get_service)):
    return _require_booking(service, booking_id)


@app.put("/bookings/{booking_id}", response_model=Booking)
def update_booking(booking_id: str, data: BookingUpdate,
                   store: Store = Depends(get_store),
                   service: BookingService = Depends(get_service)):
    _require_booking(service, booking_id)
    _require_room(store, data.room_id)
    updated = Booking(
        id=booking_id,
        room_id=data.room_id,
        organiser=data.organiser,
        start=data.start,
        end=data.end,
        attendees=data.attendees,
        recurrence=data.recurrence,
    )
    result = service.validate(updated, exclude_id=booking_id)
    if not result.ok:
        raise _conflict_exc(result.conflicts)
    store.save(updated)
    return updated


@app.delete("/bookings/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_booking(booking_id: str, service: BookingService = Depends(get_service)):
    if not service.delete(booking_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"unknown booking '{booking_id}'")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/slots/find")
def find_slot(
    duration_mins: int = Query(gt=0),
    attendees: int = Query(gt=0),
    day: date = Query(alias="date"),
    service: BookingService = Depends(get_service),
):
    found = service.find_slot(duration_mins, attendees, day)
    if found is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="no free slot found for the given duration and attendee count",
        )
    room, slot = found
    return {
        "room": room.model_dump(),
        "start": slot.isoformat(),
        "end": (slot + timedelta(minutes=duration_mins)).isoformat(),
    }