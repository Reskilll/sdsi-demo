'use strict';

const config = require('../config');

// 404 for unmatched API routes.
function notFound(req, res) {
  res.status(404).json({ error: 'Resource not found.' });
}

// Central error handler. Never leaks stack traces to clients in production.
// eslint-disable-next-line no-unused-vars
function errorHandler(err, req, res, next) {
  const status = err.status || 500;
  if (status >= 500) {
    console.error('[error]', err);
  }
  res.status(status).json({
    error: status >= 500 ? 'Internal server error.' : err.message,
    ...(config.isProd ? {} : { stack: status >= 500 ? err.stack : undefined }),
  });
}

module.exports = { notFound, errorHandler };
