"""Main FastAPI application."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from .routers import bookings, room_list, find_slot, recurrence
from .database import init_db
from .rooms import load_rooms


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    load_rooms()
    yield
    # Shutdown


app = FastAPI(
    title="Meeting Room Booking Engine",
    description="PS2: Meeting Room Booking Engine — SDSI Hackathon",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(bookings.router)
app.include_router(room_list.router)
app.include_router(find_slot.router)
app.include_router(recurrence.router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "internal_server_error", "detail": str(exc)},
    )


@app.get("/health")
async def health():
    return {"status": "ok"}