import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import type { RunContext } from '../core/context.js';
import { defineTool } from '../core/tool.js';
import { llmText, TruncatedError } from '../core/llm.js';
import { sanitizeHtml, UNTRUSTED_RULE, untrusted } from '../core/guard.js';
import { inferBrandName } from '../core/brand.js';
import { gotoSafe, newContext } from '../tools/browser.js';
import { a11yInspect, mobileInspect, uxReview } from '../tools/inspectors.js';
import type { BrandKit, CrawlData, Finding, Prototype } from '../core/types.js';

const esc = (s: string) => s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!);

function lum(hex: string) {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255).map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
const onColor = (bg: string) => (lum(bg) > 0.4 ? '#111827' : '#ffffff');
function shade(hex: string, amt: number) {
  const c = [1, 3, 5].map((i) => Math.max(0, Math.min(255, Math.round(parseInt(hex.slice(i, i + 2), 16) * (1 + amt)))));
  return '#' + c.map((n) => n.toString(16).padStart(2, '0')).join('');
}

export const brandKitExtract = defineTool({
  name: 'skill.brand-kit',
  kind: 'skill',
  feed: {
    start: ['The Designer is stealing the brand\'s colours (politely)…', 'Studying the logo, fonts and tone so the new design still feels like them.'],
    end: (r: BrandKit) => `Brand kit ready: ${r.colors.primary} on ${r.colors.bg}, ${r.font} type, ${r.nav.length} nav items.`,
    error: 'The brand kit would not come together.',
    detail: (r) => `Name ${r.name}; primary ${r.colors.primary}; font ${r.font}; hero "${r.heroTitle}"; CTA "${r.cta.text}".`,
  },
  run: async ({ crawl }: { crawl: CrawlData }) => {
    const host = new URL(crawl.finalUrl).hostname.replace(/^www\./, '');
    const name = inferBrandName(crawl.title, host, crawl.siteName);
    const heroTitle = crawl.h1s[0] ?? crawl.title;
    return {
      name, title: crawl.title, description: crawl.description || crawl.heroText, logo: crawl.logo,
      colors: { ...crawl.colors, primary: crawl.colors.primary.toLowerCase() === crawl.colors.bg.toLowerCase() ? crawl.colors.text : crawl.colors.primary },
      font: crawl.fonts[1] || crawl.fonts[0] || 'system-ui', nav: crawl.nav.slice(0, 6), heroTitle,
      heroSub: crawl.heroText || crawl.description || crawl.sections[0]?.text || '',
      cta: crawl.ctas[0] ?? { text: crawl.nav[0]?.text ?? 'Learn more', href: crawl.finalUrl },
      sections: crawl.sections.filter((s) => s.heading).slice(0, 6), images: crawl.images, origin: crawl.origin,
    } satisfies BrandKit;
  },
});

function templateHtml(b: BrandKit, crawl: CrawlData): string {
  const p = /^#[0-9a-f]{6}$/i.test(b.colors.primary) ? b.colors.primary : '#2563eb';
  const dark = /^#[0-9a-f]{6}$/i.test(b.colors.bg) && lum(b.colors.bg) < 0.15;
  const bg = dark ? b.colors.bg : '#ffffff', fg = dark ? '#f3f4f6' : '#111827', soft = dark ? shade(bg, 0.35) : '#f3f4f6', muted = dark ? '#cbd5e1' : '#4b5563';
  // Primary used as button background must pass contrast with its label; use a darker shade if needed.
  const btn = lum(p) > 0.35 && !dark ? shade(p, -0.45) : p;
  const hero = b.images[0];
  const cards = b.sections.length ? b.sections : [{ heading: 'What we do', text: b.description }];
  const navItems = b.nav.map((n, i) => `<li><a href="${cards[i] ? `#sec${i}` : esc(n.href)}">${esc(n.text)}</a></li>`).join('');
  const font = esc(b.font).replace(/[^\w \-]/g, '');
  return `<!doctype html>
<html lang="${esc(crawl.lang || 'en')}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(b.title)}</title>
<meta name="description" content="${esc((b.description || b.heroSub).slice(0, 155))}">
<script type="application/ld+json">${JSON.stringify({ '@context': 'https://schema.org', '@type': 'Organization', name: b.name, url: b.origin, logo: b.logo ?? undefined, description: b.description })}</script>
<style>
:root{--p:${btn};--on:${onColor(btn)};--bg:${bg};--fg:${fg};--soft:${soft};--muted:${muted}}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;font-family:"${font}",system-ui,-apple-system,Segoe UI,Roboto,sans-serif;font-size:1rem;line-height:1.6;background:var(--bg);color:var(--fg)}
img{max-width:100%;height:auto}
a{color:inherit}.skip{position:absolute;left:-999px}.skip:focus{left:1rem;top:1rem;background:var(--p);color:var(--on);padding:.75rem 1rem;z-index:9;border-radius:8px}
header{position:sticky;top:0;z-index:5;background:color-mix(in srgb,var(--bg) 92%,transparent);backdrop-filter:blur(10px);border-bottom:1px solid color-mix(in srgb,var(--fg) 10%,transparent)}
.bar{max-width:1120px;margin:auto;padding:.75rem 1.25rem;display:flex;align-items:center;gap:1.5rem}
.brand{display:flex;align-items:center;gap:.6rem;font-weight:700;text-decoration:none;font-size:1.15rem}.brand img{height:34px;width:auto}
nav{margin-left:auto}nav ul{list-style:none;display:flex;gap:.25rem;margin:0;padding:0}
nav a{display:block;padding:.65rem .9rem;border-radius:999px;text-decoration:none;min-height:44px;line-height:1.7;transition:background .15s}nav a:hover,nav a:focus-visible{background:var(--soft)}
.btn{display:inline-block;background:var(--p);color:var(--on);padding:.85rem 1.5rem;min-height:44px;border-radius:999px;font-weight:600;text-decoration:none;transition:transform .15s,box-shadow .15s}
.btn:hover,.btn:focus-visible{transform:translateY(-2px);box-shadow:0 8px 24px color-mix(in srgb,var(--p) 40%,transparent)}
.btn.ghost{background:transparent;color:var(--fg);border:2px solid color-mix(in srgb,var(--fg) 25%,transparent)}
details.menu{display:none;margin-left:auto}details.menu summary{list-style:none;cursor:pointer;padding:.65rem 1rem;border:1px solid var(--soft);border-radius:999px;min-height:44px}
.hero{max-width:1120px;margin:auto;padding:4.5rem 1.25rem 3rem;display:grid;grid-template-columns:1.1fr .9fr;gap:3rem;align-items:center}
.eyebrow{color:var(--muted);font-weight:600;letter-spacing:.08em;text-transform:uppercase;font-size:.8rem}
h1{font-size:clamp(2.2rem,5vw,3.6rem);line-height:1.08;margin:.4rem 0 1rem;letter-spacing:-.02em}
.lead{font-size:1.2rem;color:var(--muted);max-width:34em}.cta-row{display:flex;gap:.75rem;flex-wrap:wrap;margin-top:1.75rem}
.hero-img{border-radius:24px;overflow:hidden;background:var(--soft);aspect-ratio:4/3;display:grid;place-items:center;box-shadow:0 24px 60px rgba(0,0,0,.18)}.hero-img img{width:100%;height:100%;object-fit:cover}
.hero-fallback{background:linear-gradient(135deg,var(--p),color-mix(in srgb,var(--p) 40%,var(--bg)));width:100%;height:100%}
section.block{max-width:1120px;margin:auto;padding:3rem 1.25rem}h2{font-size:clamp(1.6rem,3vw,2.2rem);margin:0 0 1.5rem;letter-spacing:-.01em}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:1.25rem}
.card{background:var(--soft);border-radius:20px;padding:1.5rem;transition:transform .2s,box-shadow .2s;scroll-margin-top:90px}.card:hover{transform:translateY(-4px);box-shadow:0 16px 36px rgba(0,0,0,.12)}
.card h3{margin:.25rem 0 .5rem;font-size:1.2rem}.card p{margin:0;color:var(--muted)}.num{display:inline-grid;place-items:center;width:36px;height:36px;border-radius:50%;background:var(--p);color:var(--on);font-weight:700}
.band{background:var(--p);color:var(--on);margin:3rem 0 0}.band .in{max-width:1120px;margin:auto;padding:3.5rem 1.25rem;display:flex;gap:2rem;align-items:center;justify-content:space-between;flex-wrap:wrap}.band h2{margin:0}.band .btn{background:var(--on);color:var(--p)}
footer{max-width:1120px;margin:auto;padding:2rem 1.25rem 5rem;color:var(--muted);font-size:.9rem}
.ribbon{position:fixed;bottom:12px;right:12px;background:#111827;color:#fff;font-size:.78rem;padding:.5rem .85rem;border-radius:999px;opacity:.9;z-index:9}
:focus-visible{outline:3px solid var(--p);outline-offset:2px}
@media(max-width:820px){nav{display:none}details.menu{display:block}.hero{grid-template-columns:1fr;padding-top:2.5rem}.menu ul{list-style:none;margin:.5rem 0 0;padding:.5rem;background:var(--bg);border:1px solid var(--soft);border-radius:16px;position:absolute;right:1.25rem}.menu a{display:block;padding:.75rem 1rem;min-height:44px}}
@media(prefers-reduced-motion:reduce){*{transition:none!important;scroll-behavior:auto!important}}
</style>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header><div class="bar">
<a class="brand" href="${esc(b.origin)}" target="_blank" rel="noopener">${b.logo ? `<img src="${esc(b.logo)}" alt="${esc(b.name)} logo" height="34">` : ''}<span>${esc(b.name)}</span></a>
<nav aria-label="Main"><ul>${navItems}</ul></nav>
<details class="menu"><summary aria-label="Open menu">Menu</summary><ul>${navItems}</ul></details>
<a class="btn" href="${esc(b.cta.href)}" target="_blank" rel="noopener">${esc(b.cta.text)}</a>
</div></header>
<main id="main">
<div class="hero">
<div><div class="eyebrow">${esc(b.name)}</div><h1>${esc(b.heroTitle)}</h1><p class="lead">${esc(b.heroSub)}</p>
<div class="cta-row"><a class="btn" href="${esc(b.cta.href)}" target="_blank" rel="noopener">${esc(b.cta.text)}</a>${cards[0] ? '<a class="btn ghost" href="#sec0">See more</a>' : ''}</div></div>
<div class="hero-img">${hero ? `<img src="${esc(hero.src)}" alt="${esc(hero.alt || b.heroTitle)}" width="800" height="600" fetchpriority="high">` : '<div class="hero-fallback" role="img" aria-label="Brand illustration"></div>'}</div>
</div>
<section class="block" aria-labelledby="whyh"><h2 id="whyh">Why ${esc(b.name)}</h2><div class="grid">
${cards.map((c, i) => `<article class="card" id="sec${i}"><span class="num" aria-hidden="true">${i + 1}</span><h3>${esc(c.heading)}</h3><p>${esc(c.text || b.description)}</p></article>`).join('\n')}
</div></section>
${b.images.length > 1 ? `<section class="block" aria-label="Gallery"><div class="grid">${b.images.slice(1, 4).map((im) => `<img src="${esc(im.src)}" alt="${esc(im.alt || b.name)}" loading="lazy" style="border-radius:20px;width:100%;aspect-ratio:4/3;object-fit:cover">`).join('')}</div></section>` : ''}
<div class="band"><div class="in"><h2>Ready when you are.</h2><a class="btn" href="${esc(b.cta.href)}" target="_blank" rel="noopener">${esc(b.cta.text)}</a></div></div>
</main>
<footer><p>&copy; ${esc(b.name)}</p></footer>
<div class="ribbon" role="note">Concept redesign prepared for ${esc(b.name)}</div>
</body></html>`;
}

const withRibbon = (html: string, name: string) =>
  html.replace('</body>', `<div style="position:fixed;bottom:12px;right:12px;background:#111827;color:#fff;font:12px system-ui;padding:8px 14px;border-radius:999px;z-index:9" role="note">Concept redesign prepared for ${esc(name)}</div></body>`);

/** A cut-off page is usable if its <style> block finished and a body with real content began: drop the broken last tag and close the rest. */
export function salvageHtml(partial: string): string | null {
  const text = partial.match(/<!doctype html[\s\S]*/i)?.[0];
  if (!text || !/<\/style>/i.test(text) || !/<body[\s>]/i.test(text) || text.length < 3000) return null;
  const cut = text.replace(/<[^>]*$/, '').replace(/[^<>]*$/, (tail) => (tail.length > 200 ? '' : tail));
  return cut + '\n</main></section></div></body></html>';
}

export const generatePrototype = defineTool({
  name: 'skill.prototype',
  kind: 'skill',
  feed: {
    start: ['The Designer is rebuilding the homepage from scratch. Hold tight.', 'Sketching, coding, polishing: the new homepage is taking shape.'],
    end: (r: { html: string; usedLLM: boolean }) => `New homepage built (${Math.round(r.html.length / 1024)} KB of HTML, ${r.usedLLM ? 'model-designed' : 'template-based offline mode'}).`,
    error: 'The first draft fell apart.',
    detail: (r) => (r.usedLLM ? 'Generated by the model from the brand kit and the top audit findings, single-file HTML/CSS.' : 'Offline template generator used (no model key). Semantic HTML, fluid layout, accessible nav, JSON-LD.'),
  },
  run: async ({ brand, crawl, fixes, feedback }: { brand: BrandKit; crawl: CrawlData; fixes: Finding[]; feedback?: string }, ctx) => {
    let html: string | null = null;
    let lastPost = 0;
    try {
      const out = await llmText(
        'You are a senior product designer and front-end engineer. Produce ONE self-contained HTML file (inline CSS, no external scripts or fonts) that redesigns a company homepage. Keep it compact: HARD LIMIT of 220 lines in total and about 70 lines of CSS (short selectors, no vendor prefixes, no comments), one hero, 3-5 content cards, one closing call to action, footer. It must be responsive, semantic, WCAG AA accessible, visually modern, on-brand, include a meta description and schema.org JSON-LD, hover states, a mobile menu without JavaScript, and use the provided image URLs. Reply with the HTML only, starting with <!doctype html>. Never add <script> elements other than JSON-LD. ' + UNTRUSTED_RULE,
        `Brand kit (colours, fonts and copy taken from their website):\n${untrusted('website', JSON.stringify(brand, null, 1), 6000)}\n\nProblems the redesign must fix:\n${fixes.map((f) => `- ${f.title}: ${f.fix}`).join('\n')}${feedback ? `\n\nA previous attempt was re-audited and got worse. Fix this: ${feedback}` : ''}`,
        { maxTokens: 14000, usage: ctx, onProgress: (chars) => {
          if (chars - lastPost < 2500) return;
          lastPost = chars;
          ctx.run.bus.emit({ from: ctx.agent, kind: 'status', friendly: `The Designer is still typing… about ${Math.round(chars / 45)} lines of code so far.` });
        } },
      );
      const m = out?.match(/<!doctype html[\s\S]*<\/html>/i);
      if (m) html = withRibbon(m[0], brand.name);
      else if (out) ctx.run.bus.emit({ from: ctx.agent, kind: 'warning', friendly: 'The model\'s page was not usable HTML. Using the template.', detail: { summary: out.slice(0, 300) } });
    } catch (e) {
      const salvaged = e instanceof TruncatedError ? salvageHtml(e.partial) : null;
      if (salvaged) {
        html = withRibbon(salvaged, brand.name);
        ctx.run.bus.emit({ from: ctx.agent, kind: 'warning', friendly: 'The model ran out of room near the end of the page. Closing it off and using what it wrote.', detail: { summary: `Output was cut at the token limit after ${(e as TruncatedError).partial.length} characters; the styles were complete, so the open tags were closed automatically.` } });
      } else {
        ctx.run.bus.emit({ from: ctx.agent, kind: 'warning', friendly: e instanceof TruncatedError ? 'The model ran out of room before finishing the styles. Using the template.' : 'The model could not design this one. Using the template.', detail: { summary: e instanceof Error ? e.message : String(e) } });
      }
    }
    const usedLLM = html !== null;
    // Guardrail: model-written HTML never runs code in a reviewer's browser.
    return { html: usedLLM ? sanitizeHtml(html!) : templateHtml(brand, crawl), usedLLM };
  },
});

export const screenshotUrl = defineTool({
  name: 'browser.screenshot',
  feed: {
    start: ['Taking the "after" photo…', 'Snapping the finished prototype.'],
    end: () => 'After-shot captured. Time for the before/after reveal.',
    error: 'The camera shy prototype refused to pose.',
  },
  run: async ({ url, file }: { url: string; file: string }, tctx) => {
    const ctx = await newContext({ viewport: { width: 1440, height: 900 } });
    try {
      const page = await ctx.newPage();
      await gotoSafe(page, url);
      writeFileSync(file, await page.screenshot({ type: 'png' }));
      tctx.run.bus.emit({ from: tctx.agent, kind: 'status', friendly: 'Snapshot of the finished prototype.', image: `/runs/${tctx.run.runId}/shot-after.png` });
      return true;
    } finally { await ctx.close(); }
  },
});

export async function runRedesign(run: RunContext, feedback?: string): Promise<Prototype> {
  const { crawl, audit } = run.data;
  if (!crawl || !audit) throw new Error('Redesign needs the audit first.');
  const say = (friendly: string, kind: 'status' | 'question' | 'answer' | 'handoff' = 'status', to?: 'audit' | 'lead') => run.bus.emit({ from: 'redesign', to, kind, friendly });
  say('Got the problem list. Time to make something beautiful.');
  const brand = await brandKitExtract({ crawl }, { run, agent: 'redesign' });
  run.data.brand = brand;
  const { html, usedLLM } = await generatePrototype({ brand, crawl, fixes: audit.topFixes, feedback }, { run, agent: 'redesign' });
  const file = join(run.dir, 'prototype.html');
  writeFileSync(file, html);
  const protoUrl = `${run.baseUrl}/runs/${run.runId}/prototype.html`;
  await screenshotUrl({ url: protoUrl, file: join(run.dir, 'shot-after.png') }, { run, agent: 'redesign' });

  run.bus.emit({ from: 'redesign', to: 'audit', kind: 'question', friendly: 'Rebuilt it. Can you check my homework?' });
  const input = { crawl, dir: run.dir, target: protoUrl };
  // AI-search is not re-run: robots.txt and llms.txt belong to the site, not the page, so before/after would not be comparable.
  const [a11y, mobile, ux] = await Promise.allSettled([
    a11yInspect(input, { run, agent: 'a11y' }), mobileInspect(input, { run, agent: 'mobile' }), uxReview(input, { run, agent: 'ux' }),
  ]);
  const before = (c: string) => audit.categories.find((x) => x.category === c)?.score;
  const reaudit = ([['a11y', a11y], ['mobile', mobile], ['ux', ux]] as const).flatMap(([c, r]) =>
    r.status === 'fulfilled' && before(c) !== undefined ? [{ category: r.value.category, before: before(c)!, after: r.value.score }] : []);
  const proto: Prototype = {
    file: 'prototype.html', shotFile: 'shot-after.png', usedLLM, reaudit,
    changes: audit.topFixes.map((f) => ({ change: f.fix, fixes: f.title })),
  };
  run.data.prototype = proto;
  const gain = reaudit.map((r) => `${r.category} ${r.before}→${r.after}`).join(', ');
  run.bus.emit({
    from: 'audit', to: 'redesign', kind: 'answer', friendly: `Homework checked. Scores moved: ${gain || 'n/a'}.`,
    detail: { summary: 'Same inspectors re-run against the prototype. Speed and AI-search are not re-measured: a local prototype would not be a fair comparison for speed, and robots.txt/llms.txt belong to the site rather than the page.' },
  });
  run.bus.emit({
    from: 'redesign', to: 'lead', kind: 'partial_result', friendly: 'The new homepage is live. Drag the slider to see the difference.',
    panel: { name: 'prototype', data: { ...proto, before: `/runs/${run.runId}/shot-desktop.png`, after: `/runs/${run.runId}/shot-after.png`, url: `/runs/${run.runId}/prototype.html`, brand: brand.name } },
  });
  return proto;
}
