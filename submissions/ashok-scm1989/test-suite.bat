@echo off
echo ======================================================================
echo  PS2: Meeting Room Booking Engine - Automated End-to-End Test Suite
echo ======================================================================

set BASE_URL=http://localhost:8080

echo.
echo [1/6] Testing M3: GET /api/rooms (Room Catalog from rooms.json)...
curl -s -X GET "%BASE_URL%/api/rooms"
echo.

echo.
echo [2/6] Testing M4: GET /api/rooms/find-slot (45m slot for 6 attendees on 2026-11-02)...
curl -s -X GET "%BASE_URL%/api/rooms/find-slot?date=2026-11-02&duration=45&attendees=6"
echo.

echo.
echo [3/6] Testing M1: POST /api/bookings (Create booking 09:00 - 10:00)...
curl -s -X POST "%BASE_URL%/api/bookings" ^
  -H "Content-Type: application/json" ^
  -d "{\"roomId\":\"ROOM-102\",\"title\":\"Sprint Sync\",\"organiser\":\"alice@example.com\",\"startTime\":\"2026-11-02T09:00:00\",\"endTime\":\"2026-11-02T10:00:00\",\"attendees\":[\"alice@example.com\",\"bob@example.com\"]}"
echo.

echo.
echo [4/6] Testing M2: POST /api/bookings (Reject Overlap 09:30 - 10:30 on same room)...
curl -s -X POST "%BASE_URL%/api/bookings" ^
  -H "Content-Type: application/json" ^
  -d "{\"roomId\":\"ROOM-102\",\"title\":\"Overlapping Sync\",\"organiser\":\"charlie@example.com\",\"startTime\":\"2026-11-02T09:30:00\",\"endTime\":\"2026-11-02T10:30:00\",\"attendees\":[\"charlie@example.com\"]}"
echo.

echo.
echo [5/6] Testing M2: POST /api/bookings (Allow Back-to-Back 10:00 - 11:00 on same room)...
curl -s -X POST "%BASE_URL%/api/bookings" ^
  -H "Content-Type: application/json" ^
  -d "{\"roomId\":\"ROOM-102\",\"title\":\"Back to Back Meeting\",\"organiser\":\"bob@example.com\",\"startTime\":\"2026-11-02T10:00:00\",\"endTime\":\"2026-11-02T11:00:00\",\"attendees\":[\"bob@example.com\"]}"
echo.

echo.
echo [6/6] Testing M3: POST /api/bookings (Reject Capacity Exceeded: Room cap 2, requested 5)...
curl -s -X POST "%BASE_URL%/api/bookings" ^
  -H "Content-Type: application/json" ^
  -d "{\"roomId\":\"ROOM-PHONE-1\",\"title\":\"Overcrowded\",\"organiser\":\"dave@example.com\",\"startTime\":\"2026-11-02T14:00:00\",\"endTime\":\"2026-11-02T15:00:00\",\"attendees\":[\"u1@ex.com\",\"u2@ex.com\",\"u3@ex.com\",\"u4@ex.com\",\"u5@ex.com\"]}"
echo.

echo.
echo [BONUS] Testing M5: POST /api/bookings/recurring (4 weekly occurrences with conflict report)...
curl -s -X POST "%BASE_URL%/api/bookings/recurring" ^
  -H "Content-Type: application/json" ^
  -d "{\"roomId\":\"ROOM-102\",\"title\":\"Weekly Arch Review\",\"organiser\":\"architect@example.com\",\"startTime\":\"2026-11-02T09:00:00\",\"endTime\":\"2026-11-02T10:00:00\",\"occurrences\":4,\"policy\":\"BOOK_AVAILABLE\",\"attendees\":[\"dev1@example.com\",\"dev2@example.com\"]}"
echo.

echo ======================================================================
echo  Test Suite Completed!
echo ======================================================================
