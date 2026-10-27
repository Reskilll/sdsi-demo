import { randomUUID } from 'node:crypto';
import { loadRooms, loadBookings, saveBookings } from './db.js';

// ─── Limits ────────────────────────────────────────────────────────

const MAX_STRING_LEN = 200;
const MAX_ATTENDEES  = 500;
const MAX_OCCURRENCES = 52; // ~1 year of weekly bookings

// ─── Types ─────────────────────────────────────────────────────────

/**
 * @typedef {Object} Room
 * @property {string} id
 * @property {string} name
 * @property {number} capacity
 * @property {number} floor
 *
 * @typedef {Object} Booking
 * @property {string} id
 * @property {string} roomId
 * @property {string} title
 * @property {string} organiser
 * @property {string} start   ISO 8601
 * @property {string} end     ISO 8601
 * @property {string[]} attendees
 * @property {('once'|'weekly')} [recurrence]
 * @property {string} [recurrenceEnd] ISO 8601 date (YYYY-MM-DD)
 */

// ─── Helpers ───────────────────────────────────────────────────────

/** Parse ISO string to epoch ms */
function p(s) { return Date.parse(s); }

/**
 * Overlap check: back-to-back (end == other.start) is allowed.
 * Uses strict inequalities so that end === other.start does NOT overlap.
 */
function overlaps(aS, aE, bS, bE) {
  return p(aS) < p(bE) && p(aE) > p(bS);
}

/** Create a UTC Date for 09:00 on the given date string YYYY-MM-DD */
function businessStart(d) {
  const [y, m, day] = d.split('-').map(Number);
  return new Date(Date.UTC(y, m - 1, day, 9, 0, 0));
}

/** Create a UTC Date for 18:00 on the given date string YYYY-MM-DD */
function businessEnd(d) {
  const [y, m, day] = d.split('-').map(Number);
  return new Date(Date.UTC(y, m - 1, day, 18, 0, 0));
}

function toISO(d) { return d.toISOString(); }
function addMin(d, m) { return new Date(d.getTime() + m * 60_000); }

/**
 * Yield all dates from `startDate` to `endDate` (inclusive) spaced
 * `intervalDays` apart. Both params are ISO-8601 strings (date or datetime).
 * Dates are normalized to UTC midnight so the comparison is date-only.
 */
function* dateRange(startDate, endDate, intervalDays = 7) {
  const end = new Date(p(typeof endDate === 'string' && endDate.length === 10
    ? `${endDate}T23:59:59.999Z` : endDate));
  const s = new Date(p(startDate));
  let cur = new Date(Date.UTC(s.getUTCFullYear(), s.getUTCMonth(), s.getUTCDate()));
  while (cur <= end) {
    yield cur.toISOString().slice(0, 10);
    cur = new Date(cur.getTime() + intervalDays * 86_400_000);
  }
}

// ─── Room helpers ──────────────────────────────────────────────────

let _rooms = null;

export async function getRooms() {
  if (!_rooms) _rooms = await loadRooms();
  return _rooms;
}

/** @param {string} id */
export async function getRoom(id) {
  return (await getRooms()).find(r => r.id === id);
}

// ─── Booking CRUD ──────────────────────────────────────────────────

export async function listBookings() {
  return await loadBookings();
}

export async function getBooking(id) {
  const all = await loadBookings();
  return all.find(x => x.id === id) ?? null;
}

/** @returns {Promise<{ok:true, booking:Booking}|{ok:false, error:string, status:number}>} */
export async function createBooking(data) {
  data = normalizeBooking(data);

  const ve = validateFields(data);
  if (ve) return ve;

  if (p(data.start) >= p(data.end)) {
    return { ok: false, error: 'start must be before end', status: 400 };
  }

  const room = await getRoom(data.roomId);
  if (!room) return { ok: false, error: 'Room not found', status: 404 };

  if ((data.attendees?.length ?? 0) > room.capacity) {
    return { ok: false, error: `Attendee count (${data.attendees.length}) exceeds room capacity (${room.capacity})`, status: 400 };
  }

  const all = await loadBookings();
  const conflict = findConflict(all, data.roomId, data.start, data.end);
  if (conflict) {
    return { ok: false, error: `Overlaps with booking "${conflict.title || conflict.id}" (${conflict.start}–${conflict.end})`, status: 409 };
  }

  /** @type {Booking} */
  const booking = {
    id: randomUUID(),
    roomId: data.roomId,
    title: data.title ?? '',
    organiser: data.organiser,
    start: data.start,
    end: data.end,
    attendees: data.attendees ?? [],
    recurrence: data.recurrence ?? 'once',
    recurrenceEnd: data.recurrenceEnd,
  };

  all.push(booking);
  await saveBookings(all);
  return { ok: true, booking };
}

export async function updateBooking(id, updates) {
  const all = await loadBookings();
  const idx = all.findIndex(b => b.id === id);
  if (idx === -1) return { ok: false, error: 'Booking not found', status: 404 };

  const existing = all[idx];
  const patch = normalizeBooking(updates);
  const merged = { ...existing, ...patch, id: existing.id };

  // Validate dates if changed
  if (p(merged.start) >= p(merged.end)) {
    return { ok: false, error: 'start must be before end', status: 400 };
  }

  // Capacity check
  const room = await getRoom(merged.roomId);
  if (room && (merged.attendees?.length ?? 0) > room.capacity) {
    return { ok: false, error: `Attendee count exceeds room capacity (${room.capacity})`, status: 400 };
  }

  // Conflict check excluding self
  const conflict = all.find((b, i) =>
    i !== idx &&
    b.roomId === merged.roomId &&
    overlaps(merged.start, merged.end, b.start, b.end)
  );
  if (conflict) {
    return { ok: false, error: `Overlaps with booking "${conflict.title || conflict.id}"`, status: 409 };
  }

  Object.assign(all[idx], merged);
  await saveBookings(all);
  return { ok: true, booking: all[idx] };
}

export async function deleteBooking(id) {
  const all = await loadBookings();
  const idx = all.findIndex(b => b.id === id);
  if (idx === -1) return { ok: false, error: 'Booking not found', status: 404 };
  all.splice(idx, 1);
  await saveBookings(all);
  return { ok: true };
}

// ─── Validation helpers ────────────────────────────────────────────

/** Validate field lengths and attendee count. Returns error response or null. */
function validateFields(data) {
  if (!data.roomId || !data.organiser || !data.start || !data.end) {
    return { ok: false, error: 'Missing required fields: roomId, organiser, start, end', status: 400 };
  }
  for (const f of ['roomId', 'organiser', 'title']) {
    if (typeof data[f] === 'string' && data[f].length > MAX_STRING_LEN) {
      return { ok: false, error: `${f} exceeds max length of ${MAX_STRING_LEN}`, status: 400 };
    }
  }
  if (data.attendees && data.attendees.length > MAX_ATTENDEES) {
    return { ok: false, error: `Attendee count exceeds max of ${MAX_ATTENDEES}`, status: 400 };
  }
  return null;
}

function normalizeBooking(data) {
  /** @type {Record<string,*>} */
  const o = {};
  if (data.roomId !== undefined) o.roomId = data.roomId;
  if (data.title !== undefined) o.title = data.title;
  if (data.organiser !== undefined) o.organiser = data.organiser;
  if (data.start !== undefined) o.start = data.start;
  if (data.end !== undefined) o.end = data.end;
  if (data.attendees !== undefined) o.attendees = data.attendees;
  if (data.recurrence !== undefined) o.recurrence = data.recurrence;
  if (data.recurrenceEnd !== undefined) o.recurrenceEnd = data.recurrenceEnd;
  return o;
}

/**
 * Find a booking in `list` that overlaps the given slot on the same room.
 * @param {Booking[]} list
 * @param {string} roomId
 * @param {string} start
 * @param {string} end
 * @returns {Booking|null}
 */
function findConflict(list, roomId, start, end) {
  return list.find(b =>
    b.roomId === roomId && overlaps(start, end, b.start, b.end)
  ) ?? null;
}

// ─── Find slot ─────────────────────────────────────────────────────

/**
 * Given a duration, attendee count and date, return the earliest free
 * room and time slot between 09:00 and 18:00.
 *
 * Algorithm:
 *  1. Filter rooms that fit the attendee count.
 *  2. For each room, find the earliest available slot at 30-min
 *     granularity.
 *  3. Return the globally earliest slot across all rooms.
 *
 * @param {number} durationMinutes
 * @param {number} attendeeCount
 * @param {string} date  YYYY-MM-DD
 * @returns {Promise<{ room: Room, start: string, end: string }|null>}
 */
export async function findSlot(durationMinutes, attendeeCount, date) {
  if (durationMinutes <= 0 || attendeeCount <= 0) return null;
  if (durationMinutes > 9 * 60) return null; // 09:00–18:00

  const rooms = (await getRooms())
    .filter(r => r.capacity >= attendeeCount)
    .sort((a, b) => a.capacity - b.capacity);
  if (rooms.length === 0) return null;

  const all = await loadBookings();
  const dayStart = businessStart(date);
  const dayEnd = businessEnd(date);

  /** @type {{ room: Room, start: string, end: string }|null} */
  let best = null;

  for (const room of rooms) {
    // Get this room's bookings overlapping the business day
    const dayBookings = all
      .filter(b => b.roomId === room.id)
      .filter(b => overlaps(b.start, b.end, toISO(dayStart), toISO(dayEnd)))
      .sort((a, b) => p(a.start) - p(b.start));

    // Busy intervals in minutes from 09:00
    const busy = dayBookings.map(b => ({
      start: Math.max(0, diffMinutes(dayStart, new Date(p(b.start)))),
      end: Math.min(540, diffMinutes(dayStart, new Date(p(b.end)))),
    }));

    // Slide a 30-min window
    for (let off = 0; off + durationMinutes <= 540; off += 30) {
      const slotStart = off;
      const slotEnd = off + durationMinutes;
      const hasConflict = busy.some(b => slotStart < b.end && slotEnd > b.start);
      if (!hasConflict) {
        const startTime = addMin(dayStart, off);
        const endTime = addMin(startTime, durationMinutes);
        const candidate = {
          room,
          start: toISO(startTime),
          end: toISO(endTime),
        };
        if (!best || candidate.start < best.start) {
          best = candidate;
        }
        break; // Got this room's earliest slot, move to next room
      }
    }
  }

  return best;
}

function diffMinutes(a, b) {
  return (b.getTime() - a.getTime()) / 60_000;
}
function diffDays(a, b) {
  return (b - a) / 86_400_000;
}

// ─── Recurring bookings ───────────────────────────────────────────

/**
 * Create a weekly recurring booking series.
 * Creates the base occurrence first, then expands weekly occurrences
 * up to recurrenceEnd, reporting any conflicts.
 *
 * @param {Omit<Booking,'id'> & { recurrenceEnd: string }} data
 */
export async function createRecurring(data) {
  if (!data.recurrenceEnd) {
    return { ok: false, error: 'recurrenceEnd is required for recurring bookings', status: 400 };
  }

  // Create the base occurrence (this validates room, capacity & overlap)
  const base = await createBookingInner(data);
  if (!base.ok) return base;

  // Cap total occurrences to prevent abuse
  const estOccurrences = Math.ceil(diffDays(p(data.start), p(data.recurrenceEnd)) / 7) + 1;
  if (estOccurrences > MAX_OCCURRENCES) {
    return { ok: false, error: `Recurrence range exceeds max of ${MAX_OCCURRENCES} occurrences (${estOccurrences} estimated)`, status: 400 };
  }

  // Expand weekly occurrences
  const occurrences = [];
  const conflicts = [];

  for (const date of dateRange(data.start, data.recurrenceEnd)) {
    // Build this occurrence's start/end preserving the original time
    const origStart = new Date(p(data.start));
    const origEnd   = new Date(p(data.end));
    const [y, m, d] = date.split('-').map(Number);

    const occStart = new Date(Date.UTC(y, m - 1, d, origStart.getUTCHours(), origStart.getUTCMinutes(), origStart.getUTCSeconds()));
    const occEnd   = new Date(Date.UTC(y, m - 1, d, origEnd.getUTCHours(), origEnd.getUTCMinutes(), origEnd.getUTCSeconds()));

    // Skip the first occurrence (already created above)
    if (occStart.getTime() === p(base.booking.start) && occEnd.getTime() === p(base.booking.end)) {
      occurrences.push({ date, start: base.booking.start, end: base.booking.end, created: true });
      continue;
    }

    const occStartStr = toISO(occStart);
    const occEndStr   = toISO(occEnd);

    const all = await loadBookings();
    const conflict = findConflict(all, data.roomId, occStartStr, occEndStr);

    if (conflict) {
      conflicts.push({
        date,
        start: occStartStr,
        end: occEndStr,
        reason: `Overlaps with "${conflict.title || conflict.id}"`,
      });
      occurrences.push({ date, start: occStartStr, end: occEndStr, created: false, conflict: true });
    } else {
      const booking = {
        id: randomUUID(),
        roomId: data.roomId,
        title: data.title ?? '',
        organiser: data.organiser,
        start: occStartStr,
        end: occEndStr,
        attendees: data.attendees ?? [],
        recurrence: 'once',
      };
      all.push(booking);
      await saveBookings(all);
      occurrences.push({ date, start: occStartStr, end: occEndStr, created: true });
    }
  }

  return {
    ok: true,
    booking: base.booking,
    occurrences,
    conflicts,
  };
}

/**
 * Create a booking without the public-facing validation wrappers.
 * Used both by the public createBooking and internally by createRecurring.
 */
async function createBookingInner(data) {
  data = normalizeBooking(data);

  const ve = validateFields(data);
  if (ve) return ve;
  if (p(data.start) >= p(data.end)) {
    return { ok: false, error: 'start must be before end', status: 400 };
  }

  const room = await getRoom(data.roomId);
  if (!room) return { ok: false, error: 'Room not found', status: 404 };

  if ((data.attendees?.length ?? 0) > room.capacity) {
    return { ok: false, error: `Attendee count exceeds room capacity`, status: 400 };
  }

  const all = await loadBookings();
  const conflict = findConflict(all, data.roomId, data.start, data.end);
  if (conflict) {
    return { ok: false, error: `Overlaps with booking "${conflict.title || conflict.id}"`, status: 409 };
  }

  const booking = {
    id: randomUUID(),
    roomId: data.roomId,
    title: data.title ?? '',
    organiser: data.organiser,
    start: data.start,
    end: data.end,
    attendees: data.attendees ?? [],
    recurrence: data.recurrence ?? 'once',
    recurrenceEnd: data.recurrenceEnd,
  };

  all.push(booking);
  await saveBookings(all);
  return { ok: true, booking };
}