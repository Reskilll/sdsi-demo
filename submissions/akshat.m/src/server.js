import { createServer } from 'node:http';
import * as srv from './services.js';

const PORT = parseInt(process.env.PORT ?? '3000', 10);
const MAX_BODY = 1_048_576; // 1 MB

/** JSON body parser with size limit */
function body(req) {
  return new Promise((resolve, reject) => {
    let size = 0;
    let chunks = '';
    req.on('data', c => {
      size += c.length;
      if (size > MAX_BODY) { req.destroy?.(); reject(new Error('Request body too large')); }
      else chunks += c;
    });
    req.on('end', () => {
      if (!chunks) return resolve({});
      try { resolve(JSON.parse(chunks)); } catch { reject(new Error('Invalid JSON')); }
    });
    req.on('error', reject);
  });
}

/** Send JSON response (body omitted for 204) */
function json(res, status, data) {
  if (status === 204) { res.writeHead(204); return res.end(); }
  res.writeHead(status, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(data));
}

/** Match URL path & query */
function match(url) {
  const u = new URL(url, 'http://x');
  return { path: u.pathname.replace(/\/$/, '') || '/', query: Object.fromEntries(u.searchParams) };
}

export async function start() {
  const server = createServer(async (req, res) => {
    try {
      const { path, query } = match(req.url);
      const method = req.method;

      // ── CORS ──
      res.setHeader('Access-Control-Allow-Origin', '*');
      res.setHeader('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS');
      res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
      if (method === 'OPTIONS') return json(res, 204, null);

      // ── Health ──
      if (path === '/health') return json(res, 200, { status: 'ok' });

      // ── Rooms endpoint ──
      if (path === '/api/rooms' && method === 'GET') {
        return json(res, 200, await srv.getRooms());
      }

      // ── Booking routes ──
      const api = /^\/api\/bookings(?:\/(.+))?$/;
      const m = path.match(api);
      if (!m) return json(res, 404, { error: 'Not found' });

      const id = m[1] ?? null;

      if (method === 'GET' && id === 'find-slot') {
        const dur = parseInt(query.duration, 10);
        const att = parseInt(query.attendees, 10);
        if (isNaN(dur) || dur <= 0 || isNaN(att) || att < 0 || !query.date) {
          return json(res, 400, { error: 'Valid query params duration (>0), attendees (>=0), date required' });
        }
        const slot = await srv.findSlot(dur, att, query.date);
        if (!slot) return json(res, 404, { error: 'No available slot found' });
        return json(res, 200, slot);
      }

      if (method === 'POST' && id === 'recurring') {
        const data = await body(req);
        const result = await srv.createRecurring(data);
        const status = result.ok ? 201 : result.status;
        return json(res, status, result.ok
          ? { booking: result.booking, occurrences: result.occurrences, conflicts: result.conflicts }
          : { error: result.error });
      }

      if (method === 'GET' && !id) {
        return json(res, 200, await srv.listBookings());
      }

      if (method === 'GET' && id) {
        const booking = await srv.getBooking(id);
        if (!booking) return json(res, 404, { error: 'Booking not found' });
        return json(res, 200, booking);
      }

      if (method === 'POST' && !id) {
        const data = await body(req);
        const result = await srv.createBooking(data);
        return json(res, result.ok ? 201 : result.status, result.ok ? result.booking : { error: result.error });
      }

      if (method === 'PUT' && id) {
        const data = await body(req);
        const result = await srv.updateBooking(id, data);
        return json(res, result.ok ? 200 : result.status, result.ok ? result.booking : { error: result.error });
      }

      if (method === 'DELETE' && id) {
        const result = await srv.deleteBooking(id);
        return json(res, result.ok ? 204 : result.status, result.ok ? null : { error: result.error });
      }

      return json(res, 405, { error: 'Method not allowed' });
    } catch (err) {
      json(res, 400, { error: err.message || 'Bad request' });
    }
  });

  // ── Graceful shutdown ──
  const shutdown = () => { server.close(); console.log('Server shut down'); process.exit(0); };
  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);

  return new Promise((resolve) => {
    server.listen(PORT, () => {
      console.log(`Server listening on http://localhost:${PORT}\n` +
        `Endpoints: GET /health, GET /api/rooms, GET/POST/PUT/DELETE /api/bookings[/:id], ` +
        `GET /api/bookings/find-slot, POST /api/bookings/recurring`);
      resolve(server);
    });
  });
}