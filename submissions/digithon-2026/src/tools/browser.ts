import { chromium, type Browser, type Page } from 'playwright';
import { existsSync, readdirSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { defineTool } from '../core/tool.js';
import { assertPublicUrl, isAllowedRequest } from '../core/ssrf.js';
import type { CrawlData, NetRequest } from '../core/types.js';
import { registrable } from '../core/domain.js';

/** Where Playwright keeps its browsers on each platform (PLAYWRIGHT_BROWSERS_PATH wins when set). */
export function playwrightCacheDirs(env: NodeJS.ProcessEnv = process.env, platform: NodeJS.Platform = process.platform, home = homedir()): string[] {
  if (env.PLAYWRIGHT_BROWSERS_PATH && env.PLAYWRIGHT_BROWSERS_PATH !== '0') return [env.PLAYWRIGHT_BROWSERS_PATH];
  if (platform === 'win32') return [join(env.LOCALAPPDATA ?? join(home, 'AppData', 'Local'), 'ms-playwright')];
  if (platform === 'darwin') return [join(home, 'Library', 'Caches', 'ms-playwright')];
  return [join(env.XDG_CACHE_HOME ?? join(home, '.cache'), 'ms-playwright')];
}

/** Falls back to the newest Playwright browser already cached on disk when the exact revision is missing (any OS). */
function cachedChromium(): string | undefined {
  const exeName = process.platform === 'win32' ? 'chrome-headless-shell.exe' : 'chrome-headless-shell';
  for (const root of playwrightCacheDirs()) {
    if (!existsSync(root)) continue;
    const dirs = readdirSync(root).filter((d) => d.startsWith('chromium_headless_shell-')).sort((a, b) => Number(b.split('-')[1]) - Number(a.split('-')[1]));
    for (const d of dirs) {
      const arch = readdirSync(join(root, d)).find((x) => x.startsWith('chrome-headless-shell'));
      const exe = arch && join(root, d, arch, exeName);
      if (exe && existsSync(exe)) return exe;
    }
  }
  return undefined;
}

/** Executable for tools that need their own Chrome (Lighthouse). */
export function chromiumExecutable(): string | undefined {
  if (process.env.CHROMIUM_PATH) return process.env.CHROMIUM_PATH;
  try { const p = chromium.executablePath(); if (existsSync(p)) return p; } catch { /* not installed */ }
  return cachedChromium();
}

let browserP: Promise<Browser> | null = null;
export function getBrowser(): Promise<Browser> {
  browserP ??= chromium.launch({ headless: true }).catch((err) => {
    const executablePath = process.env.CHROMIUM_PATH ?? cachedChromium();
    if (!executablePath) throw err;
    return chromium.launch({ headless: true, executablePath });
  });
  return browserP;
}
/** Requests the crawler refused because they pointed at a private or internal address (reported in the feed). */
export let blockedRequests = 0;
/**
 * Creates a context with the esbuild `__name` helper stubbed, so functions passed to page.evaluate run under tsx.
 * Guardrail: every request from every page is checked, so redirects and subrequests cannot reach private addresses.
 */
export async function newContext(opts: Parameters<Browser['newContext']>[0]) {
  const ctx = await (await getBrowser()).newContext({ ...opts, serviceWorkers: 'block' });
  await ctx.route('**/*', async (route) => {
    const req = route.request();
    if (await isAllowedRequest(req.url(), req.method())) return route.continue().catch(() => {});
    blockedRequests++;
    return route.abort('blockedbyclient').catch(() => {});
  });
  await ctx.addInitScript('window.__name = window.__name || ((f) => f);');
  return ctx;
}

export async function closeBrowser() {
  if (browserP) await (await browserP).close().catch(() => {});
  browserP = null;
}

/** Window globals that identify frameworks, analytics, commerce and marketing platforms. */
const GLOBAL_PROBES = ['React', '__REACT_DEVTOOLS_GLOBAL_HOOK__', '__NEXT_DATA__', '__NUXT__', 'Vue', '__VUE__', 'angular', 'ng', 'jQuery', 'Backbone', 'Ember', 'htmx', 'Alpine',
  'dataLayer', 'ga', 'gtag', 'google_tag_manager', 's_account', 's_gi', '_satellite', 'digitalData', 'adobe', 'Granite', 'CQ', 'Shopify', 'Magento', 'mage', 'requirejs', 'dw', 'dwAnalytics',
  'ACC', 'smartedit', 'SFDC', 'Munchkin', 'piAId', 'pi', 'optimizely', 'DY', 'DYO', 'analytics', 'mixpanel', 'amplitude', 'hj', 'clarity', 'fbq', 'ttq', 'criteo_q', 'utag', 'Optanon', 'OneTrust', 'Cookiebot',
  'Sentry', 'NREUM', 'newrelic', 'DD_RUM', 'FS', 'Stripe', 'paypal', 'Klarna', 'Intercom', 'drift', 'zE', 'algoliasearch', 'bluecore', 'klaviyo', '_learnq', 'braze', 'appboy', 'Bootstrap', 'WPML', 'wp', 'BV', '$BV', 'bvCallback', 'Insider', 'insider_object', 'lpTag', 'embedded_svc', 'fcWidget', 'QSI', 'truste', 'Didomi', 'Razorpay', 'uetq', 'alloy', 'heap', '_paq', 'grecaptcha'];

/** How long the crawler behaves like a visitor (scrolling, waiting) before it reads the network. Override with NITRO_DWELL_MS. */
export const DWELL_MS = Number(process.env.NITRO_DWELL_MS ?? 10_000);
/** The page HTML kept for signature matching. Big storefronts are 1 to 5 MB (the Samsung UK buy page is about 4 MB); markers can sit far down the page. */
export const HTML_CAP = 8_000_000;
/** Requests kept in the traffic log. */
export const NETWORK_CAP = 1500;

const UA_DESKTOP =
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36';

/** Scrolls and waits like a visitor so lazy content, chat and review widgets and ad pixels load before the network log is read. */
export async function dwellLikeVisitor(page: Page, ms = DWELL_MS) {
  const end = Date.now() + ms;
  const height = await page.evaluate(() => document.documentElement.scrollHeight).catch(() => 4000);
  const steps = Math.min(16, Math.max(6, Math.ceil(height / 900)));
  const pause = Math.max(350, Math.floor((ms * 0.65) / steps));
  await page.mouse.move(500, 350).catch(() => {});
  for (let i = 0; i < steps && Date.now() < end; i++) { await page.mouse.wheel(0, 900).catch(() => {}); await page.waitForTimeout(pause); }
  const rest = end - Date.now();
  if (rest > 0) await page.waitForTimeout(rest);
  await page.evaluate(() => window.scrollTo(0, 0)).catch(() => {});
}

export async function gotoSafe(page: Page, url: string) {
  try {
    await page.goto(url, { waitUntil: 'load', timeout: 30_000 });
  } catch (e) {
    if (!/Timeout/i.test(String(e))) throw e;
    // Slow site: carry on with whatever has rendered.
  }
  await page.waitForTimeout(1500);
}

async function fetchText(url: string): Promise<string | null> {
  try {
    const r = await fetch(url, { signal: AbortSignal.timeout(6000), headers: { 'user-agent': UA_DESKTOP } });
    return r.ok ? (await r.text()).slice(0, 20_000) : null;
  } catch {
    return null;
  }
}

/** Runs in the page: pulls the brand kit, structure and content the agents need. */
const extractInPage = () => {
  const abs = (u: string | null | undefined) => { try { return u ? new URL(u, location.href).href : ''; } catch { return ''; } };
  const txt = (el: Element | null | undefined) => (el?.textContent ?? '').replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
  const visible = (el: Element) => {
    const r = el.getBoundingClientRect(); const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none';
  };
  const rgb = (c: string) => (c.match(/[\d.]+/g) ?? []).map(Number);
  const hsl = (c: string) => {
    const [r, g, b, a = 1] = rgb(c); if (a < 0.5) return null;
    const mx = Math.max(r, g, b) / 255, mn = Math.min(r, g, b) / 255, l = (mx + mn) / 2;
    const d = mx - mn; const s = d === 0 ? 0 : d / (1 - Math.abs(2 * l - 1));
    return { s, l };
  };
  const hex = (c: string) => '#' + rgb(c).slice(0, 3).map((n) => Math.round(n).toString(16).padStart(2, '0')).join('');

  // Brand colour: most frequent saturated, mid-lightness colour on interactive/heading elements.
  const tally = new Map<string, number>();
  document.querySelectorAll('a, button, [class*="btn" i], [class*="button" i], h1, h2, svg').forEach((el) => {
    const s = getComputedStyle(el);
    for (const c of [s.backgroundColor, s.color, s.fill]) {
      const h = c && c.startsWith('rgb') ? hsl(c) : null;
      if (h && h.s > 0.35 && h.l > 0.2 && h.l < 0.7) tally.set(hex(c), (tally.get(hex(c)) ?? 0) + 1);
    }
  });
  const theme = document.querySelector('meta[name="theme-color"]')?.getAttribute('content') ?? '';
  const primary = [...tally.entries()].sort((a, b) => b[1] - a[1])[0]?.[0] ?? (/^#[0-9a-f]{6}$/i.test(theme) ? theme : '#2563eb');

  const bodyBg = getComputedStyle(document.body).backgroundColor;
  const htmlBg = getComputedStyle(document.documentElement).backgroundColor;
  const bgRaw = [bodyBg, htmlBg].find((c) => c && !/rgba\(.*, 0\)|transparent/.test(c)) ?? 'rgb(255,255,255)';

  const h1 = document.querySelector('h1');
  const h1s = [...document.querySelectorAll('h1')].map(txt).filter(Boolean);
  const sections = [...document.querySelectorAll('h2, h3')].filter(visible).slice(0, 8).map((h) => {
    const p = h.parentElement?.querySelector('p') ?? h.nextElementSibling;
    return { heading: txt(h).slice(0, 80), text: txt(p).slice(0, 180) };
  }).filter((s) => s.heading.length > 2);

  const navEls = [...document.querySelectorAll('nav a, header a')].filter(visible);
  const seen = new Set<string>();
  const nav = navEls.map((a) => ({ text: txt(a), href: abs(a.getAttribute('href')) }))
    .filter((n) => n.text.length > 1 && n.text.length < 28 && !/^skip/i.test(n.text) && n.href && !seen.has(n.text) && !!seen.add(n.text)).slice(0, 8);

  const ctaRe = /buy|shop|get |start|try|sign|contact|book|learn|demo|download|subscribe|order|join|explore|discover|apply|quote/i;
  const ctas = [...document.querySelectorAll('a, button')].filter((e) => visible(e) && e.getBoundingClientRect().top < innerHeight)
    .map((e) => ({ text: txt(e), href: abs(e.getAttribute('href')) }))
    .filter((c) => c.text.length > 2 && c.text.length < 30 && ctaRe.test(c.text)).slice(0, 8);

  const imgs = [...document.querySelectorAll('img')];
  const bigImgs = imgs.filter((i) => i.naturalWidth >= 200 && visible(i) && i.currentSrc && !i.currentSrc.startsWith('data:'))
    .slice(0, 6).map((i) => ({ src: i.currentSrc, alt: i.alt }));

  const logoEl = [...document.querySelectorAll('header img, nav img, [class*="logo" i] img, img[class*="logo" i], img[alt*="logo" i]')]
    .find((i) => (i as HTMLImageElement).currentSrc) as HTMLImageElement | undefined;
  const ld: unknown[] = [];
  document.querySelectorAll('script[type="application/ld+json"]').forEach((s) => { try { ld.push(JSON.parse(s.textContent ?? '')); } catch { /* ignore */ } });

  const heroP = [...document.querySelectorAll('p')].find((p) => visible(p) && txt(p).length > 30 && p.getBoundingClientRect().top < innerHeight * 1.2);
  const font = (el: Element | null) => getComputedStyle(el ?? document.body).fontFamily.split(',')[0].replace(/["']/g, '').trim();
  const m = (window as unknown as { __m?: { lcp: number; cls: number } }).__m ?? { lcp: 0, cls: 0 };
  const nt = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming | undefined;
  const fcp = performance.getEntriesByName('first-contentful-paint')[0]?.startTime ?? 0;

  return {
    title: document.title, description: document.querySelector('meta[name="description"]')?.getAttribute('content') ?? '',
    lang: document.documentElement.lang, viewportMeta: !!document.querySelector('meta[name="viewport"]'),
    h1s, heroTitle: txt(h1), sections, nav, ctas,
    images: bigImgs, imageCount: imgs.length, missingAlt: imgs.filter((i) => !i.hasAttribute('alt')).length,
    logo: logoEl ? logoEl.currentSrc : null,
    ogImage: abs(document.querySelector('meta[property="og:image"]')?.getAttribute('content')) || null,
    siteName: document.querySelector('meta[property="og:site_name"]')?.getAttribute('content') ?? undefined,
    colors: { bg: hex(bgRaw), text: hex(getComputedStyle(document.body).color), primary },
    fonts: [font(document.body), font(h1)],
    jsonLd: ld, heroText: txt(heroP).slice(0, 220), bodySample: txt(document.body).slice(0, 1500),
    scriptCount: document.scripts.length,
    perf: { lcp: Math.round(m.lcp), cls: +m.cls.toFixed(3), ttfb: Math.round(nt?.responseStart ?? 0), load: Math.round(nt?.loadEventEnd ?? 0), fcp: Math.round(fcp) },
  };
};

export const browserRender = defineTool({
  name: 'browser.render',
  feed: {
    start: ['Opening the front door and taking a good look around…', 'Firing up a real browser. No shortcuts.'],
    end: (r: CrawlData) => `Page loaded: "${r.title.slice(0, 50)}". ${r.requests} requests, ${(r.bytes / 1e6).toFixed(1)} MB.`,
    error: 'The page was shy and would not load.',
    detail: (r) => `Rendered ${r.finalUrl}. ${r.nav.length} nav links, ${r.ctas.length} above-the-fold CTAs, ${r.imageCount} images, brand colour ${r.colors.primary}, font ${r.fonts[0]}.`,
  },
  run: async (input: { url: string; dir: string }, ctx) => {
    const url = (await assertPublicUrl(input.url)).href;
    const context = await newContext({ viewport: { width: 1440, height: 900 }, userAgent: UA_DESKTOP });
    const page = await context.newPage();
    try {
      await page.addInitScript(() => {
        const w = window as unknown as { __m: { lcp: number; cls: number } };
        w.__m = { lcp: 0, cls: 0 };
        try {
          new PerformanceObserver((l) => { for (const e of l.getEntries()) w.__m.lcp = e.startTime; }).observe({ type: 'largest-contentful-paint', buffered: true });
          new PerformanceObserver((l) => { for (const e of l.getEntries() as unknown as { hadRecentInput: boolean; value: number }[]) if (!e.hadRecentInput) w.__m.cls += e.value; }).observe({ type: 'layout-shift', buffered: true });
        } catch { /* unsupported */ }
      });
      // A HAR-style record of every request: type, size, status and key headers.
      const meta = new Map<string, { url: string; type: string; mime: string; status: number; headers: Record<string, string> }>();
      const finished = new Map<string, number>();
      const cdp = await context.newCDPSession(page);
      await cdp.send('Network.enable');
      cdp.on('Network.responseReceived', (e: { requestId: string; type: string; response: { url: string; mimeType: string; status: number; headers: Record<string, string> } }) => {
        meta.set(e.requestId, { url: e.response.url, type: e.type, mime: e.response.mimeType, status: e.response.status, headers: Object.fromEntries(Object.entries(e.response.headers).map(([k, v]) => [k.toLowerCase(), String(v)])) });
      });
      cdp.on('Network.loadingFinished', (e: { requestId: string; encodedDataLength: number }) => { finished.set(e.requestId, e.encodedDataLength); });

      await gotoSafe(page, url);
      // Hide cookie/consent overlays so the hero is visible in the screenshot.
      await page.evaluate(() => {
        document.querySelectorAll('body *').forEach((el) => {
          const s = getComputedStyle(el);
          if ((s.position === 'fixed' || s.position === 'sticky') && /cookie|consent|privacy|onetrust/i.test((el.id + el.className + (el.textContent ?? '').slice(0, 200)))
              && el.getBoundingClientRect().height < innerHeight * 0.6 && !el.querySelector('h1, nav')) (el as HTMLElement).style.display = 'none';
        });
      }).catch(() => {});
      const data = await page.evaluate(extractInPage);
      const shot = join(input.dir, 'shot-desktop.png');
      writeFileSync(shot, await page.screenshot({ type: 'png' }));
      ctx.run.bus.emit({ from: ctx.agent, kind: 'status', friendly: 'Snapshot of the homepage, exactly as a visitor sees it.', image: `/runs/${ctx.run.runId}/shot-desktop.png` });
      const origin = new URL(page.url()).origin;
      const extras = Promise.all([fetchText(`${origin}/robots.txt`), fetchText(`${origin}/llms.txt`)]);
      ctx.run.bus.emit({ from: ctx.agent, kind: 'status', friendly: `Scrolling through the page like a visitor for ${Math.round(DWELL_MS / 1000)} seconds, so chat, reviews and late-loading scripts show up.` });
      await dwellLikeVisitor(page);
      const [robotsTxt, llms] = await extras;
      const { heroTitle, ...rest } = data;
      const siteHost = new URL(page.url()).hostname;
      const siteDomain = registrable(siteHost);
      const network: NetRequest[] = [...meta.entries()].filter(([, m]) => /^https?:/.test(m.url)).slice(0, NETWORK_CAP).map(([id, m]) => {
        const host = new URL(m.url).hostname;
        return { url: m.url.slice(0, 300), host, type: m.type, mime: m.mime, bytes: finished.get(id) ?? 0, status: m.status, thirdParty: registrable(host) !== siteDomain };
      });
      const bytes = [...finished.values()].reduce((a, b) => a + b, 0);
      const doc = [...meta.values()].find((m) => m.type === 'Document');
      const globals: string[] = await page.evaluate((names) => names.filter((n) => { try { return typeof (window as unknown as Record<string, unknown>)[n] !== 'undefined'; } catch { return false; } }), GLOBAL_PROBES).catch(() => []);
      // First-party cookies only: third-party cookies would wrongly suggest the site's own stack.
      const cookieNames = (await context.cookies()).filter((c) => registrable(c.domain.replace(/^\./, '')) === siteDomain).map((c) => c.name);
      const html = (await page.content().catch(() => '')).slice(0, HTML_CAP);
      return {
        ...rest, url, finalUrl: page.url(), origin, h1s: rest.h1s.length ? rest.h1s : heroTitle ? [heroTitle] : [],
        bytes, requests: finished.size, robotsTxt, llmsTxt: !!llms && !/<html/i.test(llms.slice(0, 200)), shotDesktop: 'shot-desktop.png',
        network, headers: doc?.headers ?? {}, cookieNames, html, globals,
      } satisfies CrawlData;
    } finally {
      await context.close();
    }
  },
});
