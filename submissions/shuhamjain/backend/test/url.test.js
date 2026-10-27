'use strict';

const test = require('node:test');
const assert = require('node:assert');
const { canonicalize, hashUrl } = require('../src/lib/url');
const { ValidationError } = require('../src/lib/errors');

test('accepts http and https', () => {
  assert.strictEqual(canonicalize('http://example.com').canonical, 'http://example.com');
  assert.strictEqual(canonicalize('https://example.com').canonical, 'https://example.com');
});

test('rejects non-http(s) schemes', () => {
  for (const bad of [
    'javascript:alert(1)',
    'javascript://example.com/%0aalert(1)',
    'data:text/html,<script>alert(1)</script>',
    'vbscript:msgbox(1)',
    'file:///etc/passwd',
    'ftp://example.com/file',
    'mailto:user@example.com',
  ]) {
    assert.throws(() => canonicalize(bad), ValidationError, `should reject ${bad}`);
  }
});

test('rejects malformed / empty / oversized input', () => {
  assert.throws(() => canonicalize(''), ValidationError);
  assert.throws(() => canonicalize('   '), ValidationError);
  assert.throws(() => canonicalize('not a url'), ValidationError);
  assert.throws(() => canonicalize('http://'), ValidationError);
  assert.throws(() => canonicalize('http://exa mple.com'), ValidationError);
  assert.throws(() => canonicalize(123), ValidationError);
  assert.throws(() => canonicalize(null), ValidationError);
  assert.throws(() => canonicalize('https://example.com/' + 'a'.repeat(2100)), ValidationError);
  assert.throws(() => canonicalize('https://example.com/\u0000'), ValidationError);
});

test('canonicalizes equivalent URLs to the same key', () => {
  const pairs = [
    ['HTTP://EXAMPLE.COM:80#frag', 'http://example.com'],
    ['https://Example.com:443/', 'https://example.com'],
    ['https://example.com/', 'https://example.com'],
    ['https://example.com/#section', 'https://example.com'],
    ['https://user:pass@example.com/path', 'https://example.com/path'],
  ];
  for (const [a, b] of pairs) {
    assert.strictEqual(canonicalize(a).canonical, b, `${a} !== ${b}`);
  }
});

test('preserves path and query string', () => {
  assert.strictEqual(
    canonicalize('https://example.com/a/b?x=1&y=2').canonical,
    'https://example.com/a/b?x=1&y=2'
  );
});

test('hashUrl is deterministic and differs for different URLs', () => {
  assert.strictEqual(hashUrl('http://a.com'), hashUrl('http://a.com'));
  assert.notStrictEqual(hashUrl('http://a.com'), hashUrl('http://b.com'));
  assert.match(hashUrl('http://a.com'), /^[0-9a-f]{64}$/);
});