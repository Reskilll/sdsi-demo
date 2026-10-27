import test from 'node:test';
import assert from 'node:assert/strict';
import { detectTech, type Signals } from '../core/techSignatures.js';
import { stackCoverage, trafficStats } from '../core/stack.js';
import { neededSkills, type OrgSkill } from '../core/orgMatch.js';
import type { NetRequest } from '../core/types.js';

const req = (url: string, over: Partial<NetRequest> = {}): NetRequest => ({ url, host: new URL(url).hostname, type: 'Script', mime: 'text/javascript', bytes: 1000, status: 200, thirdParty: false, ...over });
const base: Signals = { headers: {}, cookieNames: [], html: '', globals: [], network: [] };
const names = (s: Partial<Signals>) => detectTech({ ...base, ...s }).map((t) => t.id);

test('detects Adobe stack from markup, requests and cookies', () => {
  const ids = names({ html: '<link href="/etc.clientlibs/site/main.css">', network: [req('https://assets.adobedtm.com/x/launch.js', { thirdParty: true })], cookieNames: ['AMCV_ABC%40AdobeOrg', 'mbox'] });
  for (const id of ['aem', 'adobe-launch', 'adobe-analytics', 'adobe-target']) assert.ok(ids.includes(id), id);
});

test('detects server stacks from headers and cookies', () => {
  assert.ok(names({ headers: { server: 'Werkzeug/3.0 Python/3.11' } }).includes('flask'));
  assert.ok(names({ headers: { 'x-powered-by': 'ASP.NET', 'x-aspnet-version': '4.0.30319' } }).includes('aspnet'));
  assert.ok(names({ cookieNames: ['JSESSIONID'] }).includes('java'));
  assert.ok(names({ cookieNames: ['csrftoken'] }).includes('django'));
});

test('detects commerce and framework signals', () => {
  assert.ok(names({ html: '<script src="/_ui/responsive/common/js/acc.js">' }).includes('hybris'));
  assert.ok(names({ network: [req('https://store.example.com/on/demandware.static/Sites/lib.js')] }).includes('sfcc'));
  assert.ok(names({ globals: ['__NEXT_DATA__'] }).includes('nextjs'));
});

test('confidence is confirmed only with two independent signals', () => {
  const [one] = detectTech({ ...base, globals: ['Stripe'] });
  assert.equal(one.confidence, 'likely');
  const [two] = detectTech({ ...base, globals: ['Stripe'], network: [req('https://js.stripe.com/v3/', { thirdParty: true })] });
  assert.equal(two.confidence, 'confirmed');
});

test('a third-party .php request does not imply the site runs PHP', () => {
  assert.ok(!names({ network: [req('https://www.facebook.com/fr/b.php?x=1', { thirdParty: true })] }).includes('php'));
  assert.ok(names({ network: [req('https://www.example.com/index.php?x=1')] }).includes('php'));
});

test('traffic stats: shares, types and domains', () => {
  const t = trafficStats([
    req('https://www.example.com/a.js', { bytes: 3000 }),
    req('https://cdn.vendor.com/b.js', { bytes: 1000, thirdParty: true }),
    req('https://www.example.com/i.png', { type: 'Image', bytes: 6000, status: 404 }),
  ]);
  assert.equal(t.totalRequests, 3);
  assert.equal(t.thirdParty.requestShare, 33);
  assert.equal(t.thirdParty.byteShare, 10);
  assert.equal(t.failedRequests, 1);
  assert.equal(t.byType[0].type, 'Images');
  assert.equal(t.uniqueDomains, 2);
});

test('stack coverage marks gaps, partials and strengths from the org inventory', () => {
  const inv: OrgSkill[] = [
    { id: 'adobe-aem', label: 'AEM', level: 4, headcount: 8, available: 3, availableFrom: '2026-11-02' },
    { id: 'adobe-analytics', label: 'AA', level: 3, headcount: 4, available: 1, availableFrom: '2026-11-16' },
    { id: 'adobe-campaign', label: 'AC', level: 2, headcount: 2, available: 0, availableFrom: null },
  ];
  const techs = detectTech({ ...base, html: '/etc.clientlibs/ neolane', cookieNames: ['AMCV_x'] });
  const { skills, score } = stackCoverage(techs, inv);
  const status = Object.fromEntries(skills.map((s) => [s.techId, s.status]));
  assert.equal(status['aem'], 'strong');
  assert.equal(status['adobe-analytics'], 'partial');
  assert.equal(status['adobe-campaign'], 'gap');
  assert.equal(score, Math.round((100 * (1 + 0.6 + 0)) / 3));
});

test('prospect stack raises the weight of platform skills in the org match', () => {
  const w = neededSkills([], [{ skill: 'sap-hybris', category: 'Commerce platform' }, { skill: 'web-analytics', category: 'Analytics' }]);
  assert.equal(w['sap-hybris'], 0.7);
  assert.equal(w['web-analytics'], 0.4);
});

// ── v0.4.2: gaps found by probing samsung.com ──
import { HTML_CAP, dwellLikeVisitor } from '../tools/browser.js';

test('detects chat, reviews and personalisation vendors seen on samsung.com', () => {
  const ids = names({
    network: [req('https://live-chat-static.sprinklr.com/widget.js', { thirdParty: true }), req('https://samsungsiel.api.useinsider.com/ins.js', { thirdParty: true }), req('https://resources.digital-cloud-west.medallia.com/x.js', { thirdParty: true }), req('https://dpm.demdex.net/id', { thirdParty: true })],
    globals: ['BV', 'bvCallback'],
  });
  for (const id of ['sprinklr', 'insider', 'medallia', 'aam', 'bazaarvoice']) assert.ok(ids.includes(id), id);
  assert.equal(detectTech({ ...base, globals: ['BV'] })[0].category, 'Reviews & feedback');
});

test('detects SAP Commerce (Hybris) from API paths and from markers deep in a very large page', () => {
  assert.ok(names({ network: [req('https://searchapi.example.com/v6/front/b2c/product/family/list/newhybris?siteCode=uk')] }).includes('hybris'));
  assert.ok(names({ network: [req('https://api.example.com/occ/v2/electronics/products/search')] }).includes('hybris'));
  const huge = '<div>x</div>'.repeat(70_000) + '<input id="shopIntegrationFlag" value="Hybris-new">';
  assert.ok(huge.length > 800_000);
  assert.ok(names({ html: huge }).includes('hybris'));
  assert.ok(HTML_CAP >= 3_000_000, 'the crawler must keep enough HTML to reach markers far down the page');
});

test('ad-tech traffic is one grouped entry, not dozens of cards', () => {
  const found = detectTech({ ...base, network: ['https://insight.adsrvr.org/t', 'https://ib.adnxs.com/x', 'https://c1.adform.net/y', 'https://image2.pubmatic.com/z'].map((u) => req(u, { thirdParty: true })) });
  assert.equal(found.filter((t) => t.id === 'adexchanges').length, 1);
  assert.equal(found.length, 1);
});

test('the crawler scrolls repeatedly and keeps looking for the full dwell time', async () => {
  let wheels = 0;
  const page = { evaluate: async () => 2700, mouse: { move: async () => {}, wheel: async () => { wheels++; } }, waitForTimeout: (ms: number) => new Promise((r) => setTimeout(r, ms)) };
  const t0 = Date.now();
  await dwellLikeVisitor(page as never, 1500);
  assert.ok(wheels >= 3, `scrolled ${wheels} times`);
  assert.ok(Date.now() - t0 >= 1450, 'waited the whole dwell time');
});

import { inferBrandName } from '../core/brand.js';
test('the company name on the cover comes from the domain, not from a tagline', () => {
  assert.equal(inferBrandName('Personal Banking & Netbanking Services | HDFC Bank', 'www.hdfc.bank.in'), 'HDFC Bank');
  assert.equal(inferBrandName('Galaxy S26 Ultra | Price | Samsung UK', 'www.samsung.com'), 'Samsung UK');
  assert.equal(inferBrandName('Samsung India | Mobile | Tablets | TV', 'www.samsung.com'), 'Samsung India');
  assert.equal(inferBrandName('Allbirds: Comfortable, Sustainable Shoes & Apparel', 'www.allbirds.com'), 'Allbirds: Comfortable, Sustainable Shoes & Apparel'.split(/[:]/)[0].trim());
  assert.equal(inferBrandName('Welcome', 'www.acme.io', 'Acme Inc'), 'Acme Inc');
});

import { existsSync as fileExists, readFileSync as readText } from 'node:fs';
import { SIGNATURES } from '../core/techSignatures.js';
test('every mapped technology logo exists, is listed for the UI, and has a PNG for PowerPoint', () => {
  const map = JSON.parse(readText('config/tech-icons.json', 'utf8')) as Record<string, string>;
  const list = readText('web/assets/tech/icons.js', 'utf8');
  const ids = new Set(SIGNATURES.map((s) => s.id));
  const mapped = Object.keys(map).filter((k) => !k.startsWith('_'));
  assert.ok(mapped.length >= 50, `only ${mapped.length} logos mapped`);
  for (const id of mapped) {
    assert.ok(ids.has(id), `${id} is not a known technology`);
    assert.ok(fileExists(`web/assets/tech/${id}.svg`), `${id}.svg missing: run npm run icons`);
    assert.ok(fileExists(`web/assets/tech/png/${id}.png`), `${id}.png missing: run npm run icons`);
    assert.ok(list.includes(`"${id}"`), `${id} missing from icons.js`);
  }
});
