import { lookup } from 'node:dns/promises';
import { isIP } from 'node:net';

export function isPrivate(ip: string): boolean {
  if (ip.includes(':')) {
    const l = ip.toLowerCase();
    return l === '::1' || l.startsWith('fc') || l.startsWith('fd') || l.startsWith('fe80') || l.startsWith('::ffff:127.') || l === '::';
  }
  const [a, b] = ip.split('.').map(Number);
  return (
    a === 10 || a === 127 || a === 0 || (a === 169 && b === 254) ||
    (a === 172 && b >= 16 && b <= 31) || (a === 192 && b === 168) || (a === 100 && b >= 64 && b <= 127)
  );
}

/** Normalises user input to an http(s) URL and rejects anything resolving to a private address. */
export async function assertPublicUrl(input: string): Promise<URL> {
  const t = input.trim();
  if (/^[a-z][a-z0-9+.-]*:\/\//i.test(t) && !/^https?:\/\//i.test(t)) throw new Error('Only http(s) URLs are supported.');
  const raw = /^https?:\/\//i.test(t) ? t : `https://${t}`;
  let url: URL;
  try { url = new URL(raw); } catch { throw new Error('That does not look like a valid URL.'); }
  if (!/^https?:$/.test(url.protocol)) throw new Error('Only http(s) URLs are supported.');
  const host = url.hostname.replace(/^\[|\]$/g, '');
  if (!isIP(host) && !host.includes('.')) throw new Error(`"${host}" is not a full web address. Add the domain ending, for example ${host}.com.`);
  const addrs = isIP(host) ? [{ address: host }] : await lookup(host, { all: true }).catch(() => []);
  if (addrs.length === 0) throw new Error(`Could not resolve ${host}.`);
  if (addrs.some((a) => isPrivate(a.address))) throw new Error('Private and local addresses are not allowed.');
  return url;
}

/** This app's own address. The browser may load the redesign it serves from here (GET /runs/... only). */
export const APP_ORIGIN = `http://127.0.0.1:${process.env.PORT ?? 3000}`;
const LOCAL_NAMES = /^(localhost|.*\.localhost|.*\.local|.*\.internal|.*\.lan|metadata\.google\.internal)$/i;
const dnsCache = new Map<string, Promise<boolean>>();
const resolvesPrivate = (host: string, resolve: typeof lookup) => {
  if (!dnsCache.has(host)) dnsCache.set(host, resolve(host, { all: true }).then((a) => a.some((x) => isPrivate(x.address))).catch(() => false));
  return dnsCache.get(host)!;
};

/**
 * Guardrail for every request the browser makes while it audits a site (pages, redirects, scripts, images, XHR):
 * a public page cannot make our crawler reach private or internal addresses. Only the app's own /runs/ files are allowed.
 */
export async function isAllowedRequest(raw: string, method = 'GET', resolve: typeof lookup = lookup): Promise<boolean> {
  let url: URL;
  try { url = new URL(raw); } catch { return false; }
  if (!/^https?:$/.test(url.protocol)) return true; // data:, blob: and the like never leave the browser
  const app = new URL(APP_ORIGIN);
  const host = url.hostname.replace(/^\[|\]$/g, '');
  if ((host === app.hostname || host === 'localhost') && url.port === app.port) return method === 'GET' && url.pathname.startsWith('/runs/');
  if (isIP(host)) return !isPrivate(host);
  if (LOCAL_NAMES.test(host)) return false;
  return !(await resolvesPrivate(host, resolve));
}
