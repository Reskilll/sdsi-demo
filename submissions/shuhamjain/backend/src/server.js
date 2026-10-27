'use strict';

const Fastify = require('fastify');
const cors = require('@fastify/cors');
const { openDb } = require('./db');
const buildRoutes = require('./routes');
const { AppError } = require('./lib/errors');

const DEFAULT_PORT = 3000;

async function build(opts = {}) {
  const app = Fastify({ logger: opts.logger !== false });

  app.register(cors, { origin: true });

  const db = opts.db || openDb(opts.dbPath);

  // Rate limit on the write-heavy shorten endpoint (lightweight, in-memory).
  const rateLimit = makeRateLimit({ windowMs: 60_000, max: 100 });
  app.addHook('onRequest', (request, reply, done) => {
    if (request.raw.url.startsWith('/api/shorten') && request.method === 'POST') {
      const key = request.ip;
      const status = rateLimit.check(key);
      if (!status.ok) {
        reply.code(429).send({ error: 'Too Many Requests', message: 'Slow down' });
        return;
      }
    }
    done();
  });

  app.addHook('onClose', () => {
    if (db && !opts.db) {
      db.close();
    }
  });

  app.setErrorHandler((err, request, reply) => {
    if (err instanceof AppError) {
      return reply.code(err.statusCode).send({ error: err.message });
    }
    if (err && err.message === 'rate limited') {
      return; // already handled
    }
    app.log.error(err);
    return reply.code(500).send({ error: 'Internal Server Error' });
  });

  await buildRoutes(app, { db });

  return app;
}

function makeRateLimit({ windowMs, max }) {
  const hits = new Map();
  return {
    check(key) {
      const now = Date.now();
      const win = hits.get(key);
      if (!win || win.resetAt <= now) {
        hits.set(key, { count: 1, resetAt: now + windowMs });
        return { ok: true };
      }
      win.count += 1;
      if (win.count > max) {
        return { ok: false };
      }
      return { ok: true };
    },
  };
}

module.exports = { build, DEFAULT_PORT };