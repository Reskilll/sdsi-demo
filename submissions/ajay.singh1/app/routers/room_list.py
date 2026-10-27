"""Rooms router."""
from fastapi import APIRouter
from ..rooms import get_rooms
from ..models import RoomResponse

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.get("", response_model=list[RoomResponse])
async def list_rooms():
    rooms = get_rooms()
    return sorted([r for r in rooms.values()], key=lambda r: r.name)