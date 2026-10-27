// Process entry point: wires the DB, the HTTP interface, and (in production)
// the built frontend together on a single port so `npm start` is all you need.

import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import { fileURLToPath } from 'node:url';
import { createDb } from './db.js';
import { createApp } from './app.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.PORT) || 3000;

const dataDir = path.join(__dirname, '..', 'data');
fs.mkdirSync(dataDir, { recursive: true });
const db = createDb(path.join(dataDir, 'shortener.db'));

const apiHandler = createApp(db);
const dist = path.join(__dirname, '..', '..', 'frontend', 'dist');

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
};

function serveFile(res, filePath) {
  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
      return res.end('Not found');
    }
    res.writeHead(200, { 'Content-Type': MIME[path.extname(filePath)] || 'application/octet-stream' });
    res.end(data);
  });
}

const server = http.createServer((req, res) => {
  const { pathname } = new URL(req.url, 'http://localhost');

  // API endpoints and short-code redirects go straight to the interface.
  const isApi = pathname.startsWith('/api/');
  const isCode = pathname.length > 1 && !pathname.slice(1).includes('/');
  if (isApi || (isCode && pathname !== '/stats')) {
    return apiHandler(req, res);
  }

  // Serve the built single-page app when present (skipped in API-only mode).
  if (fs.existsSync(dist)) {
    if (pathname === '/' || pathname.startsWith('/stats')) {
      return serveFile(res, path.join(dist, 'index.html'));
    }
    return serveFile(res, path.join(dist, pathname));
  }

  apiHandler(req, res);
});

server.listen(PORT, () => {
  console.log(`URL shortener running at http://localhost:${PORT}`);
});
