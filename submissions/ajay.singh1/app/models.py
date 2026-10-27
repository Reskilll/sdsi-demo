from datetime import date, datetime, time, timedelta
from typing import Optional
from pydantic import BaseModel, Field, model_validator, field_validator


class BookingBase(BaseModel):
    room: str = Field(..., min_length=1, max_length=100)
    organiser: str = Field(..., min_length=1, max_length=200)
    start_time: datetime
    end_time: datetime
    attendee_count: int = Field(..., gt=0, le=100_000)


class BookingCreate(BookingBase):
    @model_validator(mode="after")
    def check_times(self) -> "BookingCreate":
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be before end_time")
        if self.start_time.date() != self.end_time.date():
            raise ValueError("start_time and end_time must be on the same date")
        return self

    @field_validator("start_time", "end_time")
    @classmethod
    def strip_tz(cls, v: datetime) -> datetime:
        if v.tzinfo is not None:
            return v.replace(tzinfo=None)
        return v


class BookingUpdate(BaseModel):
    room: Optional[str] = Field(None, min_length=1, max_length=100)
    organiser: Optional[str] = Field(None, min_length=1, max_length=200)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    attendee_count: Optional[int] = Field(None, gt=0, le=100_000)

    @model_validator(mode="after")
    def check_times(self) -> "BookingUpdate":
        st = self.start_time
        et = self.end_time
        if st is not None and et is not None:
            if st >= et:
                raise ValueError("start_time must be before end_time")
            if st.date() != et.date():
                raise ValueError("start_time and end_time must be on the same date")
        return self


class BookingResponse(BookingBase):
    id: int
    created_at: datetime
    updated_at: datetime


class BookingList(BaseModel):
    bookings: list[BookingResponse]
    total: int
    page: int = 1
    page_size: int = 50


class ConflictInfo(BaseModel):
    booking_id: int
    room: str
    start_time: datetime
    end_time: datetime


class RecurrenceRequest(BaseModel):
    room: str = Field(..., min_length=1, max_length=100)
    organiser: str = Field(..., min_length=1, max_length=200)
    start_time: datetime
    end_time: datetime
    attendee_count: int = Field(..., gt=0, le=100_000)
    recurrence_start: date
    recurrence_end: date

    @model_validator(mode="after")
    def check_times(self) -> "RecurrenceRequest":
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be before end_time")
        if self.start_time.date() != self.end_time.date():
            raise ValueError("start_time and end_time must be on the same date")
        if self.recurrence_start > self.recurrence_end:
            raise ValueError("recurrence_start must be on or before recurrence_end")
        template_date = self.start_time.date()
        if self.recurrence_start < template_date:
            raise ValueError("recurrence_start must not be before the template booking date")
        return self

    @field_validator("start_time", "end_time")
    @classmethod
    def strip_tz(cls, v: datetime) -> datetime:
        if v.tzinfo is not None:
            return v.replace(tzinfo=None)
        return v


class RecurrenceOccurrenceResult(BaseModel):
    date: date
    booking: Optional[BookingResponse] = None
    conflict: Optional[ConflictInfo] = None
    error: Optional[str] = None


class RecurrenceResponse(BaseModel):
    created: list[RecurrenceOccurrenceResult]
    conflicts: list[RecurrenceOccurrenceResult]
    failures: list[RecurrenceOccurrenceResult]


class FindSlotRequest(BaseModel):
    date: date
    duration_minutes: int = Field(..., gt=0, le=1440)
    attendee_count: int = Field(..., gt=0, le=100_000)


class FindSlotResponse(BaseModel):
    available: bool
    room: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class RoomResponse(BaseModel):
    name: str
    capacity: int


class ErrorResponse(BaseModel):
    error: str
    detail: str | dict | None = None