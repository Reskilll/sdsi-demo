import { describe, it, before } from 'node:test';
import assert from 'node:assert/strict';
import * as srv from './services.js';
import * as db from './db.js';

async function reset() { await db.saveBookings([]); }

const sample = () => ({
  roomId: 'meeting-1',
  title: 'Sprint sync',
  organiser: 'alice@example.com',
  start: '2026-10-28T10:00:00.000Z',
  end: '2026-10-28T11:00:00.000Z',
  attendees: ['bob@example.com'],
});

// ────────────────────────────────────────────────────────────────────
describe('M1 — CRUD', async () => {
  before(async () => { await reset(); });

  it('creates a booking', async () => {
    const r = await srv.createBooking(sample());
    assert.ok(r.ok);
    assert.ok(r.booking.id);
    assert.equal(r.booking.roomId, 'meeting-1');
    assert.equal(r.booking.start, '2026-10-28T10:00:00.000Z');
  });
  it('lists bookings', async () => {
    const list = await srv.listBookings();
    assert.ok(list.length >= 1);
  });
  it('gets a booking by id', async () => {
    const all = await srv.listBookings();
    const b = await srv.getBooking(all[0].id);
    assert.equal(b.id, all[0].id);
  });
  it('returns null for unknown booking', async () => {
    assert.equal(await srv.getBooking('nonexistent'), null);
  });
  it('updates a booking', async () => {
    const all = await srv.listBookings();
    const r = await srv.updateBooking(all[0].id, { title: 'Updated' });
    assert.equal(r.booking.title, 'Updated');
  });
  it('deletes a booking', async () => {
    const all = await srv.listBookings();
    await srv.deleteBooking(all[0].id);
    assert.equal(await srv.getBooking(all[0].id), null);
  });
});

// ────────────────────────────────────────────────────────────────────
describe('M2 — Overlap rejection', async () => {
  before(async () => { await reset(); });

  it('rejects overlapping booking on same room', async () => {
    await srv.createBooking(sample());
    const r = await srv.createBooking({ ...sample(), start: '2026-10-28T10:30:00.000Z', end: '2026-10-28T11:30:00.000Z' });
    assert.ok(!r.ok);
    assert.equal(r.status, 409);
  });
  it('allows back-to-back bookings', async () => {
    await reset();
    await srv.createBooking(sample());
    const r = await srv.createBooking({ ...sample(), start: '2026-10-28T11:00:00.000Z', end: '2026-10-28T12:00:00.000Z' });
    assert.ok(r.ok);
  });
  it('allows non-overlapping on same room', async () => {
    await reset();
    await srv.createBooking(sample());
    const r = await srv.createBooking({ ...sample(), start: '2026-10-28T12:00:00.000Z', end: '2026-10-28T13:00:00.000Z' });
    assert.ok(r.ok);
  });
  it('allows simultaneous on different rooms', async () => {
    await reset();
    await srv.createBooking(sample());
    const r = await srv.createBooking({ ...sample(), roomId: 'meeting-2' });
    assert.ok(r.ok);
  });
});

// ────────────────────────────────────────────────────────────────────
describe('M3 — Capacity', async () => {
  before(async () => { await reset(); });

  it('rejects when attendees exceed capacity', async () => {
    const r = await srv.createBooking({ roomId: 'phone-booth', title: 'x', organiser: 'a', start: '2026-10-28T10:00:00.000Z', end: '2026-10-28T11:00:00.000Z', attendees: ['a','b','c'] });
    assert.ok(!r.ok);
    assert.equal(r.status, 400);
  });
  it('allows when attendees fit capacity', async () => {
    const r = await srv.createBooking({ roomId: 'phone-booth', title: 'x', organiser: 'a', start: '2026-10-28T11:00:00.000Z', end: '2026-10-28T12:00:00.000Z', attendees: ['a','b'] });
    assert.ok(r.ok);
  });
});

// ────────────────────────────────────────────────────────────────────
describe('M4 — Find slot', async () => {
  before(async () => { await reset(); });

  async function fillRoom(roomId, date) {
    for (let h = 9; h < 18; h++) {
      const hs = `${h.toString().padStart(2, '0')}:00:00.000Z`;
      const hs2 = `${(h + 1).toString().padStart(2, '0')}:00:00.000Z`;
      await srv.createBooking({ roomId, title: 'Block', organiser: 'sys', start: `${date}T${hs}`, end: `${date}T${hs2}`, attendees: ['x'] });
    }
  }

  it('finds earliest free room & slot (smallest capacity)', async () => {
    await fillRoom('meeting-1', '2026-10-28');
    await fillRoom('phone-booth', '2026-10-28');
    // phone-booth (cap 2) filled, meeting-1 (cap 4) filled → meeting-2 (cap 6) is next smallest
    const slot = await srv.findSlot(60, 2, '2026-10-28');
    assert.ok(slot);
    assert.equal(slot.room.id, 'meeting-2');
    assert.equal(slot.start, '2026-10-28T09:00:00.000Z');
  });

  it('returns null when no room fits attendee count', async () => {
    assert.equal(await srv.findSlot(60, 100, '2026-10-28'), null);
  });

  it('finds earliest slot after partial occupancy', async () => {
    await reset();
    await srv.createBooking({ ...sample(), roomId: 'meeting-1', start: '2026-10-28T09:00:00.000Z', end: '2026-10-28T10:00:00.000Z' });
    // For 4 attendees, phone-booth (cap2) too small; meeting-1 (cap4) and "Block" not there yet
    // But we booked 09-10, so earliest 60min slot is 10:00
    const slot = await srv.findSlot(60, 4, '2026-10-28');
    assert.ok(slot);
    assert.equal(slot.room.id, 'meeting-1');
    assert.equal(slot.start, '2026-10-28T10:00:00.000Z');
  });

  it('returns null when all suitable rooms booked', async () => {
    await fillRoom('meeting-1', '2026-10-28');
    await fillRoom('meeting-2', '2026-10-28');
    await fillRoom('conference-b', '2026-10-28');
    await fillRoom('conference-a', '2026-10-28');
    await fillRoom('boardroom', '2026-10-28');
    // Only phone-booth (cap2) & training (cap20) not filled; need cap>=3
    assert.equal(await srv.findSlot(30, 3, '2026-10-28'), null);
  });

  it('returns null for invalid params', async () => {
    assert.equal(await srv.findSlot(0, -1, '2026-10-28'), null);
  });
});

// ────────────────────────────────────────────────────────────────────
describe('M5 — Recurring bookings', async () => {
  before(async () => { await reset(); });

  it('creates weekly recurring booking', async () => {
    const r = await srv.createRecurring({
      roomId: 'meeting-1', title: 'Weekly standup', organiser: 'alice@example.com',
      start: '2026-10-28T10:00:00.000Z', end: '2026-10-28T11:00:00.000Z',
      attendees: ['bob@example.com'], recurrence: 'weekly', recurrenceEnd: '2026-11-11',
    });
    assert.ok(r.ok, r.error ?? 'ok');
    assert.equal(r.occurrences.length, 3);
    assert.ok(r.occurrences.every(o => o.created));
    assert.equal(r.conflicts.length, 0);
  });

  it('reports conflicts on occurrences', async () => {
    // Block the Nov 4 occurrence
    const block = await srv.createBooking({
      roomId: 'meeting-1', title: 'Blocking booking', organiser: 'bob@example.com',
      start: '2026-11-04T10:00:00.000Z', end: '2026-11-04T11:00:00.000Z',
      attendees: ['alice@example.com'],
    });
    assert.ok(block.ok);

    const r = await srv.createRecurring({
      roomId: 'meeting-1', title: 'Weekly sync', organiser: 'alice@example.com',
      start: '2026-11-04T10:00:00.000Z', end: '2026-11-04T11:00:00.000Z',
      attendees: ['bob@example.com'], recurrence: 'weekly', recurrenceEnd: '2026-11-18',
    });
    assert.ok(r.ok, r.error ?? 'ok');
    assert.ok(r.conflicts.length >= 1);
    assert.ok(r.conflicts[0].reason.includes('Blocking'));
  });
});

// ────────────────────────────────────────────────────────────────────
describe('Edge cases', async () => {
  before(async () => { await reset(); });

  it('rejects non-existent room', async () => {
    const r = await srv.createBooking({ ...sample(), roomId: 'nope' });
    assert.ok(!r.ok); assert.equal(r.status, 404);
  });
  it('accepts empty attendees', async () => {
    assert.ok((await srv.createBooking({ ...sample(), attendees: [] })).ok);
  });
  it('accepts full business day booking', async () => {
    assert.ok((await srv.createBooking({ roomId: 'meeting-1', title: 'x', organiser: 'a', start: '2026-11-01T09:00:00.000Z', end: '2026-11-01T18:00:00.000Z', attendees: ['b'] })).ok);
  });
  it('rejects findSlot > business day', async () => {
    assert.equal(await srv.findSlot(600, 1, '2026-10-28'), null);
  });
  it('rejects end before start', async () => {
    const r = await srv.createBooking({ ...sample(), start: '2026-10-28T11:00:00.000Z', end: '2026-10-28T10:00:00.000Z' });
    assert.ok(!r.ok); assert.equal(r.status, 400);
  });
  it('rejects update to overlapping time', async () => {
    const b1 = await srv.createBooking({ ...sample(), start: '2026-10-28T09:00:00.000Z', end: '2026-10-28T10:00:00.000Z' });
    const b2 = await srv.createBooking({ ...sample(), start: '2026-10-28T11:00:00.000Z', end: '2026-10-28T12:00:00.000Z' });
    const r = await srv.updateBooking(b2.booking.id, { start: '2026-10-28T09:30:00.000Z', end: '2026-10-28T10:30:00.000Z' });
    assert.ok(!r.ok); assert.equal(r.status, 409);
  });
});