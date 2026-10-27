// Process entry point: wires the DB, the app, and (in production) the built
// frontend together on a single port so `npm start` is all you need.

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import express from 'express';
import { createDb } from './db.js';
import { createApp } from './app.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.PORT) || 3000;

const dataDir = path.join(__dirname, '..', 'data');
fs.mkdirSync(dataDir, { recursive: true });
const db = createDb(path.join(dataDir, 'shortener.db'));

const app = createApp(db);

// Serve the built single-page app when present (skipped in API-only mode).
const dist = path.join(__dirname, '..', '..', 'frontend', 'dist');
if (fs.existsSync(dist)) {
  app.use(express.static(dist));
  app.get('/stats/:code', (req, res) => res.sendFile(path.join(dist, 'index.html')));
}

app.listen(PORT, () => {
  console.log(`URL shortener running at http://localhost:${PORT}`);
});
