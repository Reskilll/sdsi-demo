'use strict';

const crypto = require('crypto');
const { ValidationError } = require('./errors');

const MAX_URL_LENGTH = 2048;
const ALLOWED_PROTOCOLS = new Set(['http:', 'https:']);

// eslint-disable-next-line no-control-regex
const CONTROL_CHARS = /[\u0000-\u001f\u007f]/;

/**
 * Validate + canonicalize a URL into a single stable string so that
 * "different-looking" URLs that point at the same resource hash identically.
 *
 * Canonical form:
 *   - scheme + hostname lowercased
 *   - default port (80/443) stripped
 *   - fragment and embedded credentials removed
 *   - a bare "/" path collapsed to ""
 *   - IDN hostnames punycoded (WHATWG URL does this for us)
 */
function canonicalize(raw) {
  if (typeof raw !== 'string') {
    throw new ValidationError('url must be a string');
  }

  const trimmed = raw.trim();
  if (trimmed.length === 0) {
    throw new ValidationError('url is required');
  }
  if (trimmed.length > MAX_URL_LENGTH) {
    throw new ValidationError(`url exceeds ${MAX_URL_LENGTH} characters`);
  }
  if (CONTROL_CHARS.test(trimmed)) {
    throw new ValidationError('url contains invalid control characters');
  }

  let url;
  try {
    url = new URL(trimmed);
  } catch {
    throw new ValidationError('url is malformed');
  }

  // Scheme allowlist — this alone rejects javascript:, data:, file:, ftp:, etc.
  if (!ALLOWED_PROTOCOLS.has(url.protocol)) {
    throw new ValidationError('only http and https URLs are allowed');
  }
  if (!url.hostname) {
    throw new ValidationError('url must include a hostname');
  }

  url.username = '';
  url.password = '';
  url.hash = '';

  const hostname = url.hostname.toLowerCase();
  const port = normalizedPort(url.port, url.protocol);
  const pathname = url.pathname === '/' ? '' : url.pathname;

  return {
    canonical: `${url.protocol}//${hostname}${port}${pathname}${url.search}`,
    hostname,
    protocol: url.protocol,
  };
}

function normalizedPort(explicitPort, protocol) {
  if (explicitPort === '') {
    return '';
  }
  const defaultPort = protocol === 'http:' ? '80' : '443';
  return explicitPort === defaultPort ? '' : `:${explicitPort}`;
}

function hashUrl(canonical) {
  return crypto.createHash('sha256').update(canonical).digest('hex');
}

module.exports = { canonicalize, hashUrl, MAX_URL_LENGTH, ALLOWED_PROTOCOLS };