'use strict';

const ALPHABET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz';
const BASE = ALPHABET.length; // 62

// Start the counter here (62^5) so every generated code is 6+ characters.
// Codes stay within the required 6-8 chars for the next ~218 trillion links
// (8-char codes begin at 62^8 - 1).
const MIN_VALUE = Math.pow(BASE, 5);

function encode(value) {
  if (!Number.isSafeInteger(value) || value < 0) {
    throw new TypeError(`encode expects a non-negative safe integer, got ${value}`);
  }
  let n = value;
  let out = '';
  do {
    out = ALPHABET[n % BASE] + out;
    n = Math.floor(n / BASE);
  } while (n > 0);
  return out;
}

module.exports = { ALPHABET, BASE, MIN_VALUE, encode };