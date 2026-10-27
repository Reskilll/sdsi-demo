import { createServer } from 'node:http';
import * as srv from './services.js';

const PORT = parseInt(process.env.PORT ?? '3000', 10);

/** Minimal JSON body parser */
function body(req) {
  return new Promise((resolve, reject) => {
    let chunks = '';
    req.on('data', c => chunks += c);
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

/** Match URL path */
function match(url) {
  const u = new URL(url, 'http://x');
  return { path: u.pathname.replace(/\/$/, '') || '/', query: Object.fromEntries(u.searchParams) };
}

export async function start() {
  const server = createServer(async (req, res) => {
    try {
      const { path, query } = match(req.url);
      const method = req.method;

      // ── CORS (for curl/testing) ──
      res.setHeader('Access-Control-Allow-Origin', '*');
      res.setHeader('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS');
      res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
      if (method === 'OPTIONS') return json(res, 204, null);

      // ── Routing ──
      const api = /^\/api\/bookings(?:\/(.+))?$/;

      const m = path.match(api);

      if (!m) {
        // Health check
        if (path === '/health') return json(res, 200, { status: 'ok' });
        return json(res, 404, { error: 'Not found' });
      }

      const id = m[1] ?? null;

      // Special sub-routes on /api/bookings
      if (method === 'GET' && id === 'find-slot') {
        const dur = parseInt(query.duration, 10);
        const att = parseInt(query.attendees, 10);
        if (isNaN(dur) || isNaN(att) || !query.date) {
          return json(res, 400, { error: 'Query params duration, attendees, date required' });
        }
        const slot = await srv.findSlot(dur, att, query.date);
        if (!slot) return json(res, 404, { error: 'No available slot found' });
        return json(res, 200, slot);
      }

      if (method === 'POST' && id === 'recurring') {
        const data = await body(req);
        const result = await srv.createRecurring(data);
        const status = result.ok ? 201 : result.status;
        return json(res, status, result.ok ? result : { error: result.error });
      }

      // CRUD
      if (method === 'GET' && !id) {
        const bookings = await srv.listBookings();
        return json(res, 200, bookings);
      }

      if (method === 'GET' && id) {
        const booking = await srv.getBooking(id);
        if (!booking) return json(res, 404, { error: 'Booking not found' });
        return json(res, 200, booking);
      }

      if (method === 'POST' && !id) {
        const data = await body(req);
        const result = await srv.createBooking(data);
        const status = result.ok ? 201 : result.status;
        return json(res, status, result.ok ? result.booking : { error: result.error });
      }

      if (method === 'PUT' && id) {
        const data = await body(req);
        const result = await srv.updateBooking(id, data);
        const status = result.ok ? 200 : result.status;
        return json(res, status, result.ok ? result.booking : { error: result.error });
      }

      if (method === 'DELETE' && id) {
        const result = await srv.deleteBooking(id);
        const status = result.ok ? 204 : result.status;
        if (result.ok) return json(res, status, null);
        return json(res, status, { error: result.error });
      }

      return json(res, 405, { error: 'Method not allowed' });
    } catch (err) {
      json(res, 400, { error: err.message || 'Bad request' });
    }
  });

  return new Promise((resolve) => {
    server.listen(PORT, () => {
      console.log(`Server listening on http://localhost:${PORT}`);
      resolve(server);
    });
  });
}