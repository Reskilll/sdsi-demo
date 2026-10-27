import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { playwrightCacheDirs } from '../tools/browser.js';

test('the browser cache is found on Windows, macOS and Linux, and PLAYWRIGHT_BROWSERS_PATH wins', () => {
  assert.equal(playwrightCacheDirs({ LOCALAPPDATA: 'C:\\Users\\a\\AppData\\Local' }, 'win32', 'C:\\Users\\a')[0], join('C:\\Users\\a\\AppData\\Local', 'ms-playwright'));
  assert.equal(playwrightCacheDirs({}, 'darwin', '/Users/a')[0], join('/Users/a', 'Library', 'Caches', 'ms-playwright'));
  assert.equal(playwrightCacheDirs({}, 'linux', '/home/a')[0], join('/home/a', '.cache', 'ms-playwright'));
  assert.equal(playwrightCacheDirs({ XDG_CACHE_HOME: '/data/cache' }, 'linux', '/home/a')[0], join('/data/cache', 'ms-playwright'));
  assert.deepEqual(playwrightCacheDirs({ PLAYWRIGHT_BROWSERS_PATH: '/opt/pw' }, 'win32', 'C:\\x'), ['/opt/pw']);
});

test('npm scripts run the same in PowerShell, Command Prompt and bash', () => {
  const scripts = (JSON.parse(readFileSync('package.json', 'utf8')) as { scripts: Record<string, string> }).scripts;
  for (const [name, cmd] of Object.entries(scripts)) {
    assert.ok(!/&&|\|\||;|'|\$\w|^\s*\w+=/.test(cmd), `${name} uses shell-specific syntax: ${cmd}`);
  }
});

test('no file path is built from a URL pathname (it breaks on Windows drive letters)', () => {
  const files = ['src', 'scripts'].flatMap((d) => readdirSync(d, { recursive: true }).map((f) => join(d, String(f)))).filter((f) => /\.(ts|mjs|js)$/.test(f) && !f.includes('test'));
  for (const f of files) assert.ok(!/import\.meta\.url\)\.pathname/.test(readFileSync(f, 'utf8')), f);
});
