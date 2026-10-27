// HTTP interface over the engine. Zero-dependency (Node's built-in `http`),
// thin by design: routes map HTTP to engine calls and translate errors into
// JSON. No business logic lives here.

import { Shortener } from './engine.js';

const BODY_LIMIT = 10 * 1024; // 10 KB

function readBody(req) {
  return new Promise((resolve, reject) => {
    let size = 0;
    const chunks = [];
    req.on('data', (chunk) => {
      size += chunk.length;
      if (size > BODY_LIMIT) {
        reject(Object.assign(new Error('Request body is too large.'), { code: 'PAYLOAD_TOO_LARGE', status: 413 }));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });
    req.on('end', () => resolve(Buffer.concat(chunks).toString('utf8')));
    req.on('error', reject);
  });
}

function sendJson(res, status, obj) {
  const body = JSON.stringify(obj);
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(body);
}

function sendText(res, status, text) {
  res.writeHead(status, { 'Content-Type': 'text/plain; charset=utf-8' });
  res.end(text);
}

function protocolOf(req) {
  return req.headers['x-forwarded-proto'] === 'https' || req.socket.encrypted ? 'https' : 'http';
}

export function createApp(db) {
  const shortener = new Shortener(db);

  return async function handler(req, res) {
    const { pathname } = new URL(req.url, 'http://localhost');

    try {
      if (req.method === 'GET' && pathname === '/api/health') {
        return sendJson(res, 200, { ok: true });
      }

      if (req.method === 'POST' && pathname === '/api/shorten') {
        const raw = await readBody(req);
        let body;
        try {
          body = raw ? JSON.parse(raw) : {};
        } catch {
          return sendJson(res, 400, { error: { code: 'BAD_JSON', message: 'Request body must be valid JSON.' } });
        }
        const { url, customAlias, expiresAt } = body ?? {};
        const result = shortener.shorten({ url, customAlias, expiresAt });
        const shortUrl = `${protocolOf(req)}://${req.headers.host || 'localhost'}/${result.code}`;
        return sendJson(res, result.created ? 201 : 200, { ...result, shortUrl });
      }

      if (req.method === 'GET' && pathname.startsWith('/api/stats/')) {
        const code = pathname.slice('/api/stats/'.length);
        const stats = shortener.stats(code);
        if (!stats) {
          return sendJson(res, 404, { error: { code: 'NOT_FOUND', message: 'No link with this code.' } });
        }
        return sendJson(res, 200, stats);
      }

      // Redirect route (M2): single-segment paths resolve a short code.
      // Registered conceptually after /api/* so it never shadows them.
      if (req.method === 'GET' && pathname.length > 1 && !pathname.slice(1).includes('/')) {
        const result = shortener.resolve(pathname.slice(1));
        if (result.status === 404) return sendText(res, 404, 'Not found');
        if (result.status === 410) return sendText(res, 410, 'Gone');
        res.writeHead(302, { Location: result.url });
        return res.end();
      }

      return sendJson(res, 404, { error: { code: 'NOT_FOUND', message: 'Not found.' } });
    } catch (err) {
      // Central error handling — never let a bad request crash the process.
      if (err?.code) {
        const status = err.code === 'ALIAS_TAKEN' ? 409 : 400;
        return sendJson(res, status, { error: { code: err.code, message: err.message } });
      }
      if (err?.status) {
        return sendJson(res, err.status, { error: { code: err.code, message: err.message } });
      }
      console.error(err);
      return sendJson(res, 500, { error: { code: 'INTERNAL', message: 'Internal server error.' } });
    }
  };
}
