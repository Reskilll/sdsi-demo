import PptxGenJSModule from 'pptxgenjs';
// pptxgenjs ships CJS typings; under NodeNext the default import is the module object.
const PptxGenJS = PptxGenJSModule as unknown as typeof PptxGenJSModule.default;
import { existsSync } from 'node:fs';
import { join } from 'node:path';
import type { AuditReport, MatchResult, Prototype, StackReport } from '../core/types.js';

/** Everything the client deck needs. Built from a run's data, or from a saved trace by scripts/rebuild-deck.ts. */
export interface DeckInput {
  brandName: string;
  url: string;
  audit: AuditReport;
  match: MatchResult;
  prototype?: Prototype;
  stack?: StackReport;
  /** Folder holding the run's screenshots. */
  dir: string;
  /** Written to the title slide, for example "2026-10-26". */
  date: string;
}

// Samsung palette: the blue is the Samsung web blue (2D69E2), deep navy, white and soft greys.
const BLUE = '2D69E2', NAVY = '0B1B5E', INK = '111827', MUTE = '5B6477', LINE = 'DDE2EE', BG = 'F4F6FB', PANEL = 'FFFFFF', SOFT = 'E8ECFF';
const GOOD = '0F9D6B', WARN = 'B7791F', BAD = 'D64545', OKBG = 'DFF5EA', WARNBG = 'FDF0D5', BADBG = 'FDE4E4';
const FONT = 'Calibri';
const W = 13.333, H = 7.5, M = 0.6;
export const LOGO_BLACK = join(process.cwd(), 'assets/brand/samsung-logo-black.png');
export const LOGO_WHITE = join(process.cwd(), 'assets/brand/samsung-logo-white.png');
export const AI_BACKGROUND = join(process.cwd(), 'assets/brand/ai-background.png');
const LOGO_RATIO = 106 / 334;

/** The logo PNG for a technology id, if we have one (scripts/build-tech-icons.ts). */
const techPng = (id: string) => { const f = join(process.cwd(), 'web/assets/tech/png', `${id}.png`); return existsSync(f) ? f : null; };
const inr = (n: number) => '₹' + new Intl.NumberFormat('en-IN').format(Math.round(n));
const lakh = (n: number) => '₹' + (n / 100000).toFixed(1) + ' lakh';
const clip = (s: string, n: number) => (s.length > n ? s.slice(0, n - 1).trimEnd() + '…' : s);
const grade = (v: number) => (v >= 90 ? 'A' : v >= 80 ? 'B' : v >= 65 ? 'C' : v >= 50 ? 'D' : 'F');
const tone = (v: number) => (v >= 80 ? GOOD : v >= 65 ? WARN : BAD);
const CAT: Record<string, string> = { speed: 'Speed', mobile: 'Mobile', a11y: 'Accessibility', ux: 'UX', geo: 'AI search' };
const status = (f: number) => (f >= 0.85 ? 'Strong' : f >= 0.5 ? 'Partial' : 'Gap');
const statusColor = (st: string) => (st === 'Strong' ? [OKBG, GOOD] : st === 'Partial' ? [WARNBG, WARN] : [BADBG, BAD]);

/** Same simple schedule the Estimate tab draws: the build starts first, fixes run alongside, QA closes, management spans all. */
export function schedule(ws: { name: string; days: number }[], weeks: number) {
  const total = ws.reduce((a, w) => a + w.days, 0) || 1, per = total / weeks;
  return ws.map((w, i) => {
    const isQA = /QA/i.test(w.name), isPM = /management/i.test(w.name);
    const dur = isPM ? weeks : Math.min(weeks, Math.max(0.6, (w.days / per) * 1.6));
    const start = isPM || i === 0 ? 0 : isQA ? Math.max(0, weeks - dur) : Math.min(weeks - dur, 0.35 * weeks * ((i - 1) / Math.max(1, ws.length - 3)));
    return { ...w, start: Math.max(0, start), dur };
  });
}

export async function buildClientDeck(d: DeckInput, outFile: string): Promise<number> {
  const pptx: any = new PptxGenJS();
  pptx.layout = 'LAYOUT_WIDE';
  pptx.title = `${d.brandName}: website improvement proposal`;
  pptx.author = 'Samsung SDS';
  pptx.company = 'Samsung SDS';
  const img = (f: string) => join(d.dir, f);
  const have = (f: string) => existsSync(img(f));
  const host = (() => { try { return new URL(d.url).hostname.replace(/^www\./, ''); } catch { return d.url; } })();
  let n = 0;

  // ── building blocks ──
  const T = (s: any, t: any, x: number, y: number, w: number, h: number, o: any = {}) => s.addText(t, { x, y, w, h, fontFace: FONT, color: INK, valign: 'top', margin: 0, fontSize: 14, ...o });
  const rect = (s: any, x: number, y: number, w: number, h: number, fill: string, o: any = {}) => s.addShape(o.round ? 'roundRect' : 'rect', { x, y, w, h, fill: { color: fill }, line: { color: o.line ?? fill, width: o.lineW ?? 0 }, rectRadius: o.round ? 0.1 : undefined });
  const card = (s: any, x: number, y: number, w: number, h: number, o: any = {}) => { rect(s, x, y, w, h, o.fill ?? PANEL, { round: true, line: o.line ?? LINE, lineW: 1 }); if (o.bar) rect(s, x, y, w, 0.07, o.bar); };
  const pill = (s: any, label: string, x: number, y: number, w: number, bg: string, fg: string, size = 10) => { rect(s, x, y, w, 0.27, bg, { round: true }); T(s, label, x, y, w, 0.27, { fontSize: size, bold: true, color: fg, align: 'center', valign: 'middle' }); };
  const stat = (s: any, x: number, y: number, w: number, h: number, value: string, label: string, color = INK, size = 28) => { card(s, x, y, w, h); T(s, value, x + 0.2, y + 0.12, w - 0.4, h * 0.55, { fontSize: size, bold: true, color, valign: 'middle' }); T(s, label, x + 0.2, y + h * 0.65, w - 0.4, h * 0.3, { fontSize: 11, color: MUTE }); };

  /** The Samsung wordmark: black on light slides, white on dark ones (assets/brand, made from the supplied logo by scripts/build-brand-assets.py). */
  const logo = (s: any, x: number, y: number, w: number, onDark = false) => {
    s.addImage({ path: onDark ? LOGO_WHITE : LOGO_BLACK, x, y, w, h: w * LOGO_RATIO, altText: 'Samsung logo' });
  };

  function base(title: string, kicker: string, notes: string) {
    const s = pptx.addSlide(); n++;
    s.background = { color: BG };
    rect(s, 0, 0, W, 0.12, BLUE);
    T(s, kicker.toUpperCase(), M, 0.38, 9, 0.3, { fontSize: 11, bold: true, color: BLUE, charSpacing: 3 });
    T(s, title, M, 0.68, 10.2, 0.8, { fontSize: 28, bold: true, color: NAVY, fit: 'shrink' });
    logo(s, W - M - 1.3, 0.38, 1.3);
    T(s, `${d.brandName}  ·  Prepared by Samsung SDS`, M, 7.05, 8, 0.28, { fontSize: 10, color: MUTE });
    T(s, String(n), W - M - 0.5, 7.05, 0.5, 0.28, { fontSize: 10, color: MUTE, align: 'right' });
    s.addNotes(notes);
    return s;
  }
  const cats = d.audit.categories, findings = cats.flatMap((c) => c.findings).sort((a, b) => b.severity - a.severity);

  // 1 · Cover
  {
    const s = pptx.addSlide(); n++;
    s.background = { color: NAVY };
    s.addImage({ path: AI_BACKGROUND, x: 0, y: 0, w: W, h: H, altText: 'Abstract network background' });
    rect(s, W * 0.60, 0, W * 0.40, H, BG);
    logo(s, M, 0.55, 2.6, true);
    T(s, 'WEBSITE IMPROVEMENT PROPOSAL', M, 2.0, 7, 0.35, { fontSize: 13, bold: true, color: 'B7C4FF', charSpacing: 4 });
    T(s, `A better ${d.brandName} homepage`, M, 2.45, 7.2, 2.0, { fontSize: 44, bold: true, color: 'FFFFFF', fit: 'shrink', valign: 'top' });
    T(s, `Audit, technology review, concept redesign and delivery plan for ${d.brandName}`, M, 4.55, 6.9, 0.9, { fontSize: 18, color: 'DCE3FF' });
    T(s, [{ text: host, options: { bold: true, breakLine: true } }, { text: `Prepared ${d.date} by Samsung SDS · Digital Engineering` }], M, 6.1, 7.2, 0.7, { fontSize: 13, color: 'B7C4FF' });
    if (have('shot-desktop.png')) {
      card(s, W * 0.60 + 0.35, 0.9, 4.6, 2.75, { line: LINE }); s.addImage({ path: img('shot-desktop.png'), x: W * 0.60 + 0.4, y: 0.95, w: 4.5, h: 2.65, sizing: { type: 'cover', w: 4.5, h: 2.65 } });
      T(s, `${d.brandName} today`, W * 0.60 + 0.35, 3.72, 4.6, 0.3, { fontSize: 11, bold: true, color: MUTE, align: 'center' });
    }
    if (have('shot-after.png')) {
      card(s, W * 0.60 + 0.55, 4.1, 4.6, 2.75, { line: BLUE }); s.addImage({ path: img('shot-after.png'), x: W * 0.60 + 0.6, y: 4.15, w: 4.5, h: 2.65, sizing: { type: 'cover', w: 4.5, h: 2.65 } });
      pill(s, 'CONCEPT', W * 0.60 + 4.0, 4.25, 1.0, BLUE, 'FFFFFF');
    }
    s.addNotes(`Cover. This proposal is for ${d.brandName} (${host}). The left side names the engagement; the right shows their homepage today and the concept redesign.`);
  }

  // 2 · Executive summary
  {
    const s = base('Where you stand, and what we recommend', 'Executive summary', `Overall score ${d.audit.overall} out of 100, grade ${d.audit.grade}. The three biggest opportunities are on the right.`);
    card(s, M, 1.65, 3.5, 3.3);
    s.addChart(pptx.charts.DOUGHNUT, [{ name: 'Score', labels: ['Score', 'Rest'], values: [d.audit.overall, 100 - d.audit.overall] }], { x: M + 0.35, y: 1.8, w: 2.8, h: 2.5, holeSize: 74, chartColors: [tone(d.audit.overall), 'E6E9F3'], showLegend: false, showValue: false, showPercent: false, showLabel: false, dataBorder: { pt: 0, color: 'FFFFFF' } });
    T(s, String(d.audit.overall), M, 2.55, 3.5, 0.9, { fontSize: 48, bold: true, align: 'center', color: tone(d.audit.overall), valign: 'middle' });
    T(s, `out of 100 · grade ${d.audit.grade}`, M, 4.35, 3.5, 0.3, { fontSize: 13, color: MUTE, align: 'center' });
    T(s, `${host} today`, M, 4.62, 3.5, 0.3, { fontSize: 11, color: MUTE, align: 'center' });
    const top = d.audit.topFixes.slice(0, 3);
    T(s, 'THE BIGGEST OPPORTUNITIES', M + 3.9, 1.65, 8, 0.3, { fontSize: 11, bold: true, color: MUTE, charSpacing: 2 });
    top.forEach((f, i) => { const y = 2.05 + i * 1.0; card(s, M + 3.9, y, 8.2, 0.88); T(s, String(i + 1), M + 4.05, y + 0.12, 0.5, 0.64, { fontSize: 26, bold: true, color: BLUE, valign: 'middle' }); T(s, clip(f.title, 70), M + 4.65, y + 0.1, 7.3, 0.35, { fontSize: 15, bold: true }); T(s, clip(f.impact, 120), M + 4.65, y + 0.47, 7.3, 0.36, { fontSize: 11, color: MUTE }); });
    const est = d.match.estimate, stk = d.stack;
    const items: [string, string, string?][] = [['Technologies found', stk ? String(stk.technologies.length) : 'n/a'], ['Organisation match', `${d.match.orgScore}/100`, tone(d.match.orgScore)], ['Team', `${d.match.team.length} people`], ['Timeline', `${est.weeks} weeks`], ['Investment', `₹${(est.priceLow / 100000).toFixed(1)}–${(est.priceHigh / 100000).toFixed(1)} lakh`]];
    const w = (W - 2 * M - 0.2 * 4) / 5;
    items.forEach(([l, v, c], i) => stat(s, M + i * (w + 0.2), 5.25, w, 1.5, v, l, c ?? INK, v.length > 9 ? 20 : 28));
  }

  // 3 · Scorecard
  {
    const s = base(`How ${d.brandName} scores today`, 'The audit', 'Each score is measured: Lighthouse for speed, axe-core for accessibility, a phone-sized browser for mobile, a vision model for UX and tool checks plus a model judgement for AI search. Findings and evidence follow.');
    const w = (W - 2 * M - 0.2 * 4) / 5;
    cats.forEach((c, i) => {
      const x = M + i * (w + 0.2); card(s, x, 1.65, w, 4.6, { bar: tone(c.score) });
      T(s, CAT[c.category] ?? c.category, x + 0.2, 1.85, w - 0.4, 0.35, { fontSize: 15, bold: true });
      T(s, String(c.score), x + 0.2, 2.25, w - 0.9, 0.85, { fontSize: 44, bold: true, color: tone(c.score), valign: 'middle' });
      pill(s, `Grade ${c.grade}`, x + w - 1.15, 2.5, 0.95, tone(c.score) === GOOD ? OKBG : tone(c.score) === WARN ? WARNBG : BADBG, tone(c.score));
      rect(s, x + 0.2, 3.2, w - 0.4, 0.12, 'E6E9F3', { round: true }); rect(s, x + 0.2, 3.2, Math.max(0.1, (w - 0.4) * c.score / 100), 0.12, tone(c.score), { round: true });
      T(s, clip(c.headline, 110), x + 0.2, 3.5, w - 0.4, 0.95, { fontSize: 11, color: INK });
      Object.entries(c.metrics).slice(0, 3).forEach(([k, v], j) => { T(s, k, x + 0.2, 4.55 + j * 0.55, w - 0.4, 0.22, { fontSize: 9, color: MUTE }); T(s, clip(String(v), 14), x + 0.2, 4.74 + j * 0.55, w - 0.4, 0.28, { fontSize: 12, bold: true }); });
    });
    T(s, `Overall ${d.audit.overall}/100, grade ${d.audit.grade}: speed 20%, mobile 20%, accessibility 20%, UX 25%, AI search 15%.`, M, 6.5, W - 2 * M, 0.3, { fontSize: 11, color: MUTE });
  }

  // 4–5 · Findings, six per slide, with evidence and the fix
  {
    const all = findings.slice(0, 12), pages = Math.max(1, Math.ceil(all.length / 6));
    for (let p = 0; p < pages; p++) {
      const rows = all.slice(p * 6, p * 6 + 6);
      const s = base(pages > 1 ? `What we found (${p + 1} of ${pages})` : 'What we found', 'The audit · findings and evidence', 'Every finding carries its evidence, the recommended fix and why it matters to the business.');
      const head = (t: string) => ({ text: t, options: { bold: true, color: MUTE, fontSize: 10, fill: { color: BG } } });
      const sev = (v: number) => (v >= 3 ? ['High', BAD, BADBG] : v === 2 ? ['Medium', WARN, WARNBG] : ['Low', MUTE, 'EEF0F5']);
      s.addTable([[head('AREA'), head('FINDING'), head('EVIDENCE'), head('RECOMMENDED FIX'), head('IMPACT')], ...rows.map((f) => {
        const [lbl, fg, bg] = sev(f.severity);
        return [{ text: CAT[f.category] ?? f.category, options: { bold: true, fontSize: 11, color: BLUE } }, { text: clip(f.title, 70), options: { bold: true, fontSize: 11 } }, { text: clip(f.evidence, 90), options: { fontSize: 10, color: MUTE } }, { text: clip(f.fix, 95), options: { fontSize: 10 } }, { text: lbl as string, options: { bold: true, fontSize: 10, color: fg as string, fill: { color: bg as string }, align: 'center' } }];
      })], { x: M, y: 1.65, w: W - 2 * M, colW: [1.35, 3.1, 3.4, 3.45, 0.83], rowH: 0.8, fontFace: FONT, color: INK, border: { type: 'solid', color: LINE, pt: 0.75 }, fill: { color: PANEL }, valign: 'middle' });
    }
  }

  // 6 · Technology stack
  if (d.stack) {
    const st = d.stack, tr = st.traffic;
    const s = base(`The technology behind ${host}`, 'Technology review', `Detected from ${tr.totalRequests} network requests, response headers, cookies, page markup and script globals. Each technology is coloured by how well our people cover it. Detection is a strong hint, not a certainty.`);
    const w = (W - 2 * M - 0.2 * 3) / 4;
    [[String(st.technologies.length), 'technologies detected', INK], [String(tr.totalRequests), 'network requests', INK], [`${tr.thirdParty.requestShare}%`, 'third-party requests', tr.thirdParty.requestShare > 60 ? WARN : INK], [String(tr.uniqueDomains), 'domains contacted', INK]].forEach(([v, l, c], i) => stat(s, M + i * (w + 0.2), 1.6, w, 1.2, v, l, c));
    const groups = new Map<string, typeof st.technologies>(); for (const t of st.technologies) groups.set(t.category, [...(groups.get(t.category) ?? []), t]);
    const cover = Object.fromEntries(st.coverage.skills.map((x) => [x.techId, x.status]));
    let y = 3.05; const colW = 7.6;
    for (const [cat, list] of [...groups].slice(0, 8)) {
      T(s, cat.toUpperCase(), M, y + 0.05, 2.3, 0.3, { fontSize: 9.5, bold: true, color: MUTE, charSpacing: 1 });
      let x = M + 2.4;
      for (const t of list.slice(0, 5)) {
        const ic = techPng(t.id), cw = Math.min(2.9, 0.4 + t.name.length * 0.085 + (ic ? 0.34 : 0)), col = cover[t.id] === 'strong' ? GOOD : cover[t.id] === 'partial' ? WARN : cover[t.id] === 'gap' ? BAD : LINE;
        if (x + cw > M + colW + 2.4) break;
        rect(s, x, y, cw, 0.36, PANEL, { round: true, line: col, lineW: t.confidence === 'likely' ? 1 : 2 });
        if (ic) s.addImage({ path: ic, x: x + 0.1, y: y + 0.07, w: 0.22, h: 0.22, altText: `${t.name} logo` });
        T(s, t.name, x + (ic ? 0.34 : 0), y, cw - (ic ? 0.34 : 0), 0.36, { fontSize: 10, bold: true, align: 'center', valign: 'middle' }); x += cw + 0.1;
      }
      y += 0.45;
    }
    T(s, 'Border colour: our coverage (green strong, amber partial, red gap). Thin border: a single signal, so likely rather than confirmed.', M, 6.55, 9.5, 0.3, { fontSize: 10, color: MUTE });
    card(s, 10.3, 3.05, 2.43, 3.35); T(s, 'BUSIEST DOMAINS', 10.45, 3.15, 2.2, 0.25, { fontSize: 9, bold: true, color: MUTE, charSpacing: 1 });
    const mx = Math.max(1, ...tr.topDomains.map((x) => x.bytes));
    tr.topDomains.slice(0, 6).forEach((x, i) => { const yy = 3.5 + i * 0.47; T(s, clip(x.domain, 24), 10.45, yy, 2.2, 0.2, { fontSize: 9, color: x.thirdParty ? WARN : INK }); rect(s, 10.45, yy + 0.22, 2.1, 0.1, 'E6E9F3', { round: true }); rect(s, 10.45, yy + 0.22, Math.max(0.08, 2.1 * x.bytes / mx), 0.1, x.thirdParty ? WARN : BLUE, { round: true }); });
  }

  // 7 · How we support the stack
  if (d.stack && d.stack.coverage.skills.length) {
    const cov = d.stack.coverage;
    const s = base('How Samsung SDS supports your stack', 'Technology review · our coverage', `We map each detected technology to our skills inventory. ${cov.score} percent of the platform stack has capacity today. Gaps are shown honestly with a plan to cover them. Skills data is sample data until connected to the real inventory.`);
    const rows = cov.skills.slice(0, 9), x = [M, M + 0.55, M + 3.4, M + 5.9, M + 9.2, M + 11.0], y0 = 1.65, rh = 0.46;
    [['TECHNOLOGY', 1, 2.8], ['CATEGORY', 2, 2.4], ['OUR SKILL', 3, 3.2], ['PEOPLE FREE', 4, 1.8], ['STATUS', 5, 1.0]].forEach(([h, i, w]) => T(s, h as string, x[i as number], y0, w as number, 0.25, { fontSize: 9.5, bold: true, color: MUTE, charSpacing: 1 }));
    rows.forEach((r, i) => {
      const y = y0 + 0.35 + i * rh, label = r.status === 'strong' ? 'Strong' : r.status === 'partial' ? 'Partial' : 'Gap', [bg, fg] = statusColor(label), ic = techPng(r.techId);
      rect(s, M, y + rh - 0.02, W - 2 * M, 0.01, LINE);
      if (ic) s.addImage({ path: ic, x: x[0] + 0.04, y: y + 0.08, w: 0.28, h: 0.28, altText: `${r.tech} logo` }); else { rect(s, x[0] + 0.04, y + 0.08, 0.28, 0.28, SOFT, { round: true }); T(s, r.tech.split(/\s+/).map((w) => w[0]).slice(0, 2).join('').toUpperCase(), x[0] + 0.04, y + 0.08, 0.28, 0.28, { fontSize: 8, bold: true, color: BLUE, align: 'center', valign: 'middle' }); }
      T(s, clip(r.tech, 26), x[1], y, 2.8, rh - 0.04, { fontSize: 13, bold: true, valign: 'middle' }); T(s, clip(r.category, 22), x[2], y, 2.4, rh - 0.04, { fontSize: 11, color: MUTE, valign: 'middle' });
      T(s, clip(r.skillLabel, 30), x[3], y, 3.2, rh - 0.04, { fontSize: 12, valign: 'middle' }); T(s, `${r.available} of ${r.headcount}${r.availableFrom && r.available ? ' · ' + r.availableFrom : ''}`, x[4], y, 1.8, rh - 0.04, { fontSize: 11, valign: 'middle' });
      pill(s, label, x[5], y + 0.09, 0.95, bg, fg, 10);
    });
    stat(s, M, 5.95, 3.9, 1.0, `${cov.score}%`, 'of your platform stack we can staff now', tone(cov.score));
    T(s, 'Strong: skilled and two or more people free. Partial: some capacity. Gap: nobody free, so we plan a partner or a hire.', M + 4.2, 6.1, 7.9, 0.7, { fontSize: 11, color: MUTE });
  }

  // 8 · Before / after
  {
    const s = base('Your own homepage, improved', 'Concept redesign', `The concept is built from ${d.brandName}'s own colours, fonts and content, then re-checked by the same inspectors. It is a concept for discussion, not a final design.`);
    const iw = 5.9, ih = 3.45;
    [['Today', 'shot-desktop.png', MUTE], ['Concept', 'shot-after.png', BLUE]].forEach(([lbl, f, col], i) => { const x = M + i * (iw + 0.33); card(s, x, 1.65, iw, ih + 0.1, { line: col as string }); if (have(f as string)) s.addImage({ path: img(f as string), x: x + 0.05, y: 1.7, w: iw - 0.1, h: ih, sizing: { type: 'cover', w: iw - 0.1, h: ih } }); pill(s, (lbl as string).toUpperCase(), x + 0.15, 1.82, 0.95, col as string, 'FFFFFF'); });
    const ra = d.prototype?.reaudit ?? []; const w = ra.length ? (W - 2 * M - 0.2 * (ra.length)) / (ra.length + 1) : 3;
    ra.forEach((r, i) => stat(s, M + i * (w + 0.2), 5.4, w, 1.3, `${r.before} → ${r.after}`, `${CAT[r.category] ?? r.category} score, re-checked on the concept`, r.after >= r.before ? GOOD : BAD));
    T(s, 'Same inspectors, run on the concept page. Speed and AI search are not re-measured on a local concept.', M + (ra.length) * (w + 0.2), 5.45, w, 1.2, { fontSize: 11, color: MUTE });
  }

  // 9 · Phone
  if (have('shot-mobile.png')) {
    const s = base('On a phone', 'Concept redesign · mobile', 'Most visitors arrive on a phone. These are phone-sized screenshots of the live site and of the concept.');
    const pw = 2.6, ph = 4.9;
    [['Today', 'shot-mobile.png', MUTE], ['Concept', 'shot-mobile-after.png', BLUE]].forEach(([lbl, f, col], i) => { const x = M + i * (pw + 0.5); if (have(f as string)) { card(s, x, 1.65, pw, ph, { line: col as string }); s.addImage({ path: img(f as string), x: x + 0.05, y: 1.7, w: pw - 0.1, h: ph - 0.1, sizing: { type: 'cover', w: pw - 0.1, h: ph - 0.1 } }); pill(s, (lbl as string).toUpperCase(), x + 0.15, 1.82, 0.95, col as string, 'FFFFFF'); } });
    const mob = cats.find((c) => c.category === 'mobile');
    if (mob) { card(s, M + 2 * (pw + 0.5) + 0.2, 1.65, 5.0, ph); T(s, 'Mobile today', M + 2 * (pw + 0.5) + 0.45, 1.85, 4.5, 0.35, { fontSize: 16, bold: true }); T(s, `${mob.score}/100 · grade ${mob.grade}`, M + 2 * (pw + 0.5) + 0.45, 2.25, 4.5, 0.5, { fontSize: 26, bold: true, color: tone(mob.score) }); T(s, clip(mob.headline, 140), M + 2 * (pw + 0.5) + 0.45, 2.9, 4.5, 0.9, { fontSize: 12, color: MUTE }); Object.entries(mob.metrics).slice(0, 4).forEach(([k, v], j) => { T(s, k, M + 2 * (pw + 0.5) + 0.45, 3.9 + j * 0.6, 2.3, 0.25, { fontSize: 10, color: MUTE }); T(s, String(v), M + 2 * (pw + 0.5) + 0.45, 4.15 + j * 0.6, 4.2, 0.3, { fontSize: 14, bold: true }); }); }
  }

  // 10 · What changed
  if (d.prototype?.changes.length) {
    const s = base('What changed, and why', 'Concept redesign · changes', 'Each change in the concept answers a specific audit finding.');
    const ch = d.prototype.changes.slice(0, 6);
    ch.forEach((c, i) => { const y = 1.65 + i * 0.88; card(s, M, y, W - 2 * M, 0.76); rect(s, M, y, 0.08, 0.76, BLUE); T(s, clip(c.fixes, 80), M + 0.3, y + 0.08, 4.9, 0.6, { fontSize: 13, bold: true, valign: 'middle' }); T(s, '→', M + 5.25, y + 0.08, 0.4, 0.6, { fontSize: 18, color: BLUE, valign: 'middle', align: 'center' }); T(s, clip(c.change, 150), M + 5.75, y + 0.08, W - 2 * M - 6.0, 0.6, { fontSize: 12, color: MUTE, valign: 'middle' }); });
  }

  // 11 · Organisation match
  {
    const m = d.match; const s = base('Why Samsung SDS fits this work', 'Organisation match', `The organisation match score is ${m.orgScore} out of 100: how well our skills cover what this work needs, weighted by importance and availability. It uses the detected technology stack and the audit findings. Skills are sample data until connected to the real inventory.`);
    card(s, M, 1.65, 3.2, 4.9);
    s.addChart(pptx.charts.DOUGHNUT, [{ name: 'Match', labels: ['Match', 'Rest'], values: [m.orgScore, 100 - m.orgScore] }], { x: M + 0.3, y: 1.85, w: 2.6, h: 2.6, holeSize: 74, chartColors: [tone(m.orgScore), 'E6E9F3'], showLegend: false, showValue: false, showPercent: false, showLabel: false, dataBorder: { pt: 0, color: 'FFFFFF' } });
    T(s, String(m.orgScore), M, 2.65, 3.2, 0.9, { fontSize: 44, bold: true, align: 'center', color: tone(m.orgScore), valign: 'middle' });
    T(s, 'organisation match', M, 4.5, 3.2, 0.3, { fontSize: 12, color: MUTE, align: 'center' });
    T(s, [{ text: 'Strengths', options: { bold: true, color: GOOD, breakLine: true } }, { text: clip(m.strengths.slice(0, 4).join(', ') || 'none', 90), options: { color: MUTE, breakLine: true } }, { text: ' ', options: { breakLine: true } }, { text: 'Gaps', options: { bold: true, color: m.gaps.length ? BAD : GOOD, breakLine: true } }, { text: m.gaps.length ? clip(m.gaps.join(', '), 90) : 'None', options: { color: MUTE } }], M + 0.25, 4.85, 2.8, 1.6, { fontSize: 11 });
    const rows = m.skills.slice(0, 9); const x0 = M + 3.5;
    T(s, 'SKILL', x0, 1.65, 3.0, 0.25, { fontSize: 9, bold: true, color: MUTE, charSpacing: 1 }); T(s, 'FIT', x0 + 3.2, 1.65, 2.2, 0.25, { fontSize: 9, bold: true, color: MUTE, charSpacing: 1 }); T(s, 'PEOPLE FREE', x0 + 5.6, 1.65, 1.5, 0.25, { fontSize: 9, bold: true, color: MUTE, charSpacing: 1 });
    rows.forEach((x, i) => { const y = 2.0 + i * 0.5, st = status(x.fit), [bg, fg] = statusColor(st); T(s, clip(x.label, 34), x0, y, 3.1, 0.4, { fontSize: 12, bold: true, valign: 'middle' }); rect(s, x0 + 3.2, y + 0.14, 2.2, 0.12, 'E6E9F3', { round: true }); rect(s, x0 + 3.2, y + 0.14, Math.max(0.08, 2.2 * x.fit), 0.12, fg, { round: true }); T(s, `${x.available} of ${x.headcount}`, x0 + 5.6, y, 1.1, 0.4, { fontSize: 11, valign: 'middle' }); pill(s, st, x0 + 6.75, y + 0.07, 0.85, bg, fg, 9.5); });
  }

  // 12 · Proposed team
  {
    const s = base('The team we would put on it', 'Proposed team', `Named people who are available. Fit blends their level and how much of the needed skill weight they cover. This is sample talent data until connected to the real roster.`);
    const w = (W - 2 * M - 0.25 * 2) / 3, h = 2.35;
    d.match.team.slice(0, 6).forEach((t, i) => {
      const x = M + (i % 3) * (w + 0.25), y = 1.65 + Math.floor(i / 3) * (h + 0.25); card(s, x, y, w, h);
      const hue = [...t.name].reduce((a, c) => a + c.charCodeAt(0), 0) % 4; const col = [BLUE, '2A6CF0', '0F8B8D', '5B3FD0'][hue];
      s.addShape('ellipse', { x: x + 0.25, y: y + 0.25, w: 0.7, h: 0.7, fill: { color: col }, line: { color: col, width: 0 } }); T(s, t.name.split(' ').map((p) => p[0]).slice(0, 2).join(''), x + 0.25, y + 0.25, 0.7, 0.7, { fontSize: 18, bold: true, color: 'FFFFFF', align: 'center', valign: 'middle' });
      T(s, t.name, x + 1.1, y + 0.25, w - 2.0, 0.35, { fontSize: 15, bold: true }); T(s, t.role, x + 1.1, y + 0.6, w - 2.0, 0.3, { fontSize: 11, color: MUTE });
      T(s, `${Math.round(t.fit * 100)}%`, x + w - 0.95, y + 0.25, 0.75, 0.4, { fontSize: 20, bold: true, color: BLUE, align: 'right' }); T(s, 'fit', x + w - 0.95, y + 0.65, 0.75, 0.25, { fontSize: 10, color: MUTE, align: 'right' });
      T(s, clip(t.skills.slice(0, 4).join(' · '), 60), x + 0.25, y + 1.2, w - 0.5, 0.35, { fontSize: 11, color: INK }); T(s, `Level ${t.level}/5 · available from ${t.availableFrom}`, x + 0.25, y + 1.6, w - 0.5, 0.3, { fontSize: 10.5, color: MUTE }); T(s, clip(t.rationale, 95), x + 0.25, y + 1.88, w - 0.5, 0.4, { fontSize: 9, color: MUTE });
    });
  }

  // 13 · Plan and estimate
  {
    const e = d.match.estimate; const s = base('The plan: effort and timeline', 'Estimate', `About ${e.totalDays} person-days over ${e.weeks} weeks. The timeline is an indicative picture of the effort, to be fixed in discovery.`);
    const total = e.workstreams.reduce((a, w) => a + w.days, 0) || 1, cols = [BLUE, '2A6CF0', '0F8B8D', '5B3FD0', 'D99A1B', 'E0457B', '8892B0'];
    T(s, 'EFFORT BY WORKSTREAM (PERSON-DAYS)', M, 1.6, 6, 0.3, { fontSize: 10, bold: true, color: MUTE, charSpacing: 2 });
    let x = M; e.workstreams.forEach((w, i) => { const ww = (W - 2 * M) * w.days / total; rect(s, x, 1.95, Math.max(0.05, ww - 0.03), 0.4, cols[i % cols.length]); x += ww; });
    e.workstreams.forEach((w, i) => { const col = i % 2, row = Math.floor(i / 2), xx = M + col * 6.1, yy = 2.5 + row * 0.3; rect(s, xx, yy + 0.07, 0.14, 0.14, cols[i % cols.length]); T(s, `${clip(w.name, 44)}  ·  ${w.days} d (${Math.round(100 * w.days / total)}%)`, xx + 0.25, yy, 5.7, 0.3, { fontSize: 10.5 }); });
    const wk = Math.max(2, e.weeks), cw = Math.ceil(wk), y0 = 4.1, lw = 3.4, tw = W - 2 * M - lw;
    T(s, 'INDICATIVE TIMELINE', M, y0 - 0.4, 5, 0.3, { fontSize: 10, bold: true, color: MUTE, charSpacing: 2 });
    for (let i = 0; i < cw; i++) T(s, `Week ${i + 1}`, M + lw + i * tw / cw, y0 - 0.05, tw / cw, 0.25, { fontSize: 9, color: MUTE, align: 'center' });
    schedule(e.workstreams, wk).slice(0, 7).forEach((w, i) => { const yy = y0 + 0.25 + i * 0.36; T(s, clip(w.name, 38), M, yy, lw - 0.1, 0.3, { fontSize: 10, valign: 'middle' }); rect(s, M + lw, yy + 0.04, tw, 0.22, 'EEF0F5', { round: true }); rect(s, M + lw + tw * w.start / cw, yy + 0.04, Math.max(0.2, tw * w.dur / cw), 0.22, cols[i % cols.length], { round: true }); });
  }

  // 14 · Investment
  {
    const e = d.match.estimate; const s = base('Investment', 'Estimate · commercials', 'A price range until discovery is complete, with every assumption stated.');
    card(s, M, 1.65, 6.4, 2.3, { bar: BLUE }); T(s, 'ESTIMATED INVESTMENT', M + 0.3, 1.9, 5.8, 0.3, { fontSize: 10, bold: true, color: MUTE, charSpacing: 2 });
    T(s, `${inr(e.priceLow)} – ${inr(e.priceHigh)}`, M + 0.3, 2.3, 5.8, 0.9, { fontSize: 34, bold: true, color: BLUE, fit: 'shrink' }); T(s, `${lakh(e.priceLow)} to ${lakh(e.priceHigh)} · a range until discovery is complete`, M + 0.3, 3.3, 5.8, 0.4, { fontSize: 12, color: MUTE });
    const w = (W - 2 * M - 6.4 - 0.3 - 0.2) / 2;
    stat(s, M + 6.7, 1.65, w, 1.05, String(e.totalDays), 'person-days'); stat(s, M + 6.7 + w + 0.2, 1.65, w, 1.05, `${e.weeks} weeks`, 'indicative duration'); stat(s, M + 6.7, 2.9, w, 1.05, String(d.match.team.length), 'people on the team'); stat(s, M + 6.7 + w + 0.2, 2.9, w, 1.05, 'In discovery', 'final scope and price', INK, 20);
    T(s, 'ASSUMPTIONS', M, 4.25, 6, 0.3, { fontSize: 10, bold: true, color: MUTE, charSpacing: 2 });
    T(s, e.assumptions.map((a) => ({ text: clip(a, 130), options: { bullet: true, breakLine: true } })), M, 4.6, W - 2 * M, 2.0, { fontSize: 13, paraSpaceAfter: 6 });
    T(s, 'Terms: to be added by the account owner before this proposal is sent.', M, 6.6, W - 2 * M, 0.3, { fontSize: 10.5, color: MUTE, italic: true });
  }

  // 15 · Next steps
  {
    const s = base('Next steps', 'Working together', 'Three simple steps. Nothing is sent or committed until a human approves.');
    const steps: [string, string][] = [['Walk through the concept', `A 30-minute session with your team on ${d.brandName}'s homepage concept, the audit and the technology review.`], ['Discovery week', 'We confirm scope, constraints and price, and fix the plan and the team.'], ['Start building', `The team starts ${d.match.team.map((t) => t.availableFrom).sort()[0] ?? 'soon'}, with weekly demos and a launch plan.`]];
    steps.forEach(([t, b], i) => { const y = 1.8 + i * 1.6; card(s, M, y, W - 2 * M, 1.35); s.addShape('ellipse', { x: M + 0.3, y: y + 0.3, w: 0.75, h: 0.75, fill: { color: BLUE }, line: { color: BLUE, width: 0 } }); T(s, String(i + 1), M + 0.3, y + 0.3, 0.75, 0.75, { fontSize: 24, bold: true, color: 'FFFFFF', align: 'center', valign: 'middle' }); T(s, t, M + 1.4, y + 0.22, W - 2 * M - 1.8, 0.4, { fontSize: 19, bold: true }); T(s, b, M + 1.4, y + 0.7, W - 2 * M - 1.8, 0.55, { fontSize: 13, color: MUTE }); });
  }

  // 16 · Closing
  {
    const s = pptx.addSlide(); n++; s.background = { color: NAVY };
    s.addImage({ path: AI_BACKGROUND, x: 0, y: 0, w: W, h: H, altText: 'Abstract network background' });
    logo(s, W / 2 - 1.6, 1.5, 3.2, true);
    T(s, `Let's make ${d.brandName}'s website your strongest sales channel.`, 1.2, 3.1, W - 2.4, 1.6, { fontSize: 34, bold: true, color: 'FFFFFF', align: 'center', fit: 'shrink' });
    T(s, 'Samsung SDS · Digital Engineering', 1.2, 5.0, W - 2.4, 0.5, { fontSize: 18, color: 'DCE3FF', align: 'center' });
    T(s, `${host}  ·  ${d.date}`, 1.2, 5.6, W - 2.4, 0.4, { fontSize: 13, color: 'B7C4FF', align: 'center' });
    s.addNotes('Close. Thank the audience and agree the first step.');
  }

  // 17 · Appendix
  {
    const s = base('How we measured', 'Appendix', 'Methods and limits, for anyone who wants to check our work.');
    const items: [string, string][] = [['Speed', 'Lighthouse 12, mobile profile with simulated throttling. Falls back to browser timings if Lighthouse cannot run.'], ['Mobile', 'The page reloaded at phone size with touch: viewport, overflow, tap targets, text size.'], ['Accessibility', 'axe-core run in a real browser; each rule weighted by impact.'], ['UX', 'A vision model scores a screenshot against a fixed rubric; findings must cite what is visible.'], ['AI search', 'Structured data, llms.txt, AI-crawler rules and a model judgement of how clearly the page says what you do.'], ['Technology', 'About 130 signatures over network requests, headers, cookies, markup and script globals. A hint, not a certainty.']];
    items.forEach(([t, b], i) => { const x = M + (i % 2) * 6.15, y = 1.65 + Math.floor(i / 2) * 1.5; card(s, x, y, 5.9, 1.3); T(s, t, x + 0.25, y + 0.15, 5.4, 0.3, { fontSize: 14, bold: true, color: BLUE }); T(s, b, x + 0.25, y + 0.5, 5.4, 0.75, { fontSize: 11.5, color: MUTE }); });
    T(s, 'Scores are for the homepage only, measured once. The bench roster, skills inventory and rates are sample data until connected to real systems.', M, 6.3, W - 2 * M, 0.5, { fontSize: 11, color: MUTE });
  }

  await pptx.writeFile({ fileName: outFile });
  return n;
}
