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

  // PostgreSQL foreign key violation (insert with bad ref, or delete of referenced row)
  if (err.code === '23503') {
    const isDelete = err.message && err.message.includes('delete');
    return res.status(400).json({
      error: isDelete
        ? 'Cannot delete: this record is still referenced by existing expenses or shares. Remove those first.'
        : 'Referenced record does not exist',
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