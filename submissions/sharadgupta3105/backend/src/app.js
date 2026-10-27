// Express interface over the engine. Thin by design: routes map HTTP to
// engine calls and translate errors into JSON. No business logic lives here.

import express from 'express';
import { Shortener } from './engine.js';

export function createApp(db) {
  const app = express();
  const shortener = new Shortener(db);

  app.disable('x-powered-by');
  app.use(express.json({ limit: '10kb' }));

  app.get('/api/health', (req, res) => {
    res.json({ ok: true });
  });

  app.post('/api/shorten', (req, res) => {
    const { url, customAlias, expiresAt } = req.body ?? {};
    const result = shortener.shorten({ url, customAlias, expiresAt });
    const shortUrl = `${req.protocol}://${req.get('host')}/${result.code}`;
    res.status(result.created ? 201 : 200).json({ ...result, shortUrl });
  });

  app.get('/api/stats/:code', (req, res) => {
    const stats = shortener.stats(req.params.code);
    if (!stats) {
      return res.status(404).json({ error: { code: 'NOT_FOUND', message: 'No link with this code.' } });
    }
    res.json(stats);
  });

  // Redirect route (M2): 302 found, 410 gone, 404 unknown. Registered after
  // the /api/* routes so it never shadows them.
  app.get('/:code', (req, res) => {
    const result = shortener.resolve(req.params.code);
    if (result.status === 404) return res.status(404).send('Not found');
    if (result.status === 410) return res.status(410).send('Gone');
    res.redirect(302, result.url);
  });

  // Central error handler — never let a bad request crash the process.
  app.use((err, req, res, _next) => {
    if (err?.code) {
      const status = err.code === 'ALIAS_TAKEN' ? 409 : 400;
      return res.status(status).json({ error: { code: err.code, message: err.message } });
    }
    if (err?.type === 'entity.parse.failed') {
      return res.status(400).json({ error: { code: 'BAD_JSON', message: 'Request body must be valid JSON.' } });
    }
    if (err?.type === 'entity.too.large') {
      return res.status(413).json({ error: { code: 'PAYLOAD_TOO_LARGE', message: 'Request body is too large.' } });
    }
    console.error(err);
    res.status(500).json({ error: { code: 'INTERNAL', message: 'Internal server error.' } });
  });

  return app;
}
