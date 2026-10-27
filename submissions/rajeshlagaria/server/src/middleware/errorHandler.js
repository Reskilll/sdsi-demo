/**
 * Global error handler middleware.
 */
function errorHandler(err, _req, res, _next) {
  console.error('[Error]', err.message);

  // PostgreSQL unique violation
  if (err.code === '23505') {
    return res.status(409).json({
      error: 'A record with that value already exists',
      detail: err.detail,
    });
  }

  // PostgreSQL foreign key violation
  if (err.code === '23503') {
    return res.status(400).json({
      error: 'Referenced record does not exist',
      detail: err.detail,
    });
  }

  // PostgreSQL check violation
  if (err.code === '23514') {
    return res.status(400).json({
      error: 'Value does not satisfy constraint',
      detail: err.detail,
    });
  }

  res.status(err.status || 500).json({
    error: err.message || 'Internal server error',
  });
}

module.exports = errorHandler;