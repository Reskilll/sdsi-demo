'use strict';

const { shorten } = require('./services/shorten');
const { resolve, recordClick } = require('./services/resolve');
const { stats } = require('./services/stats');

/**
 * Register all routes. Each handler is thin: it validates/coerces input, calls
 * a service, and returns a response. Domain errors propagate to the central
 * error handler in server.js.
 */
module.exports = async function buildRoutes(fastify, { db }) {
  fastify.get('/healthz', async () => ({ ok: true }));

  fastify.post('/api/shorten', async (request) => {
    const body = request.body || {};
    const result = shorten(db, {
      url: body.url,
      ttl: body.ttl,
      alias: body.alias,
      selfHosts: selfHostsFor(request),
    });
    return { ...result, shortUrl: absoluteUrl(request, result.shortUrl) };
  });

  // Resolve: 302 redirect, 410 gone, or 404 unknown.
  fastify.get('/:code', async (request, reply) => {
    const outcome = resolve(db, request.params.code);
    if (outcome.status === 404) {
      return reply.code(404).send({ error: 'Not Found', message: 'No such short code' });
    }
    if (outcome.status === 410) {
      return reply.code(410).send({ error: 'Gone', message: 'This link has expired' });
    }
    recordClick(db, outcome.linkId);
    return reply.redirect(outcome.location, 302);
  });

  // Stats for a code.
  fastify.get('/api/stats/:code', async (request, reply) => {
    const result = stats(db, request.params.code);
    if (!result) {
      return reply.code(404).send({ error: 'Not Found', message: 'No such short code' });
    }
    return result;
  });
};

function absoluteUrl(request, path) {
  return `${request.protocol}://${request.host}${path}`;
}

// Hosts that should never be shortenable: the request's own host (prevents
// self-referential redirect loops) plus any configured allowed hosts.
function selfHostsFor(request) {
  const hosts = new Set();
  if (request.hostname) hosts.add(request.hostname);
  // Also cover the common localhost aliases during development.
  hosts.add('localhost');
  hosts.add('127.0.0.1');
  return hosts;
}