// URL validation for the shortener.
//
// Accepts only absolute http(s) URLs. Rejects anything else — including
// javascript:, data:, file: and other schemes — as well as malformed strings
// the WHATWG URL parser cannot make sense of.

const MAX_URL_LENGTH = 2048;

export class ValidationError extends Error {
  constructor(code, message) {
    super(message);
    this.name = 'ValidationError';
    this.code = code; // stable machine-readable code, surfaced by the API
  }
}

export function validateUrl(raw) {
  if (typeof raw !== 'string') {
    throw new ValidationError('INVALID_URL', 'URL must be a string.');
  }

  const value = raw.trim();
  if (value.length === 0) {
    throw new ValidationError('INVALID_URL', 'URL is empty.');
  }
  if (value.length > MAX_URL_LENGTH) {
    throw new ValidationError('INVALID_URL', `URL exceeds ${MAX_URL_LENGTH} characters.`);
  }
  if (/\s/.test(value)) {
    throw new ValidationError('INVALID_URL', 'URL must not contain whitespace.');
  }

  let parsed;
  try {
    parsed = new URL(value);
  } catch {
    throw new ValidationError('INVALID_URL', 'URL is malformed.');
  }

  // WHATWG lowercases the protocol, so this catches HTTPS://, JAVASCRIPT:, etc.
  const protocol = parsed.protocol;
  if (protocol !== 'http:' && protocol !== 'https:') {
    throw new ValidationError('INVALID_URL', 'Only http:// and https:// URLs are allowed.');
  }
  if (!parsed.hostname) {
    throw new ValidationError('INVALID_URL', 'URL must include a hostname.');
  }

  // Normalized form — makes shortening idempotent for equivalent spellings.
  return parsed.toString();
}
