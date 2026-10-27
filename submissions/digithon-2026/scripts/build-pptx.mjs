// Builds the Digithon presentation as a PowerPoint file: docs/Nitro-Digithon-2026.pptx.
// Same story, numbers and colours as web/presentation.html (the animated version). Run: npm run pptx
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import pptxgen from 'pptxgenjs';

const ROOT = fileURLToPath(new URL('..', import.meta.url)); // a real path on Windows too (URL.pathname gives /C:/...)
const OUT = `${ROOT}docs/Nitro-Digithon-2026.pptx`;
const A = (f) => `${ROOT}web/assets/${f}`;
const ICON = (k) => A(`pptx/ic-${k}.png`);
const BOT = (id) => A(`pptx/bot-${id}.png`);
const MARKET = JSON.parse(readFileSync(`${ROOT}config/marketplace.json`, 'utf8')).agents;

// Palette from the app (light theme) and the dark slides.
const K = { bg: 'F4F6FB', panel: 'FFFFFF', panel2: 'F1F3F9', line: 'DFE3EE', fg: '1A2033', muted: '667089', acc: '4F6BFF', acc2: '7C4DFF', good: '0F9D6B', warn: 'B7791F', bad: 'D64545', okbg: 'DFF5EA', warnbg: 'FDF0D5', badbg: 'FDE4E4', hl: 'EEF2FF', dark: '0B1020', darkPanel: '17214A', darkFg: 'F1F4FF', darkMuted: 'A9B4D6' };
const FONT = 'Calibri';
const W = 13.333, X0 = 0.6, CW = W - 2 * X0;

const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE';
pres.title = 'Nitro: Digithon 2026';
pres.subject = 'AI pre-sales agents that turn available talent into new clients';
pres.author = 'Nitro team';
pres.theme = { headFontFace: FONT, bodyFontFace: FONT };

pres.defineSlideMaster({
  title: 'DARK', background: { color: K.dark },
  objects: [
    { placeholder: { options: { name: 'kicker', type: 'body', x: 0.8, y: 1.7, w: 11.7, h: 0.45, fontSize: 14, bold: true, color: '8FA5FF', charSpacing: 4, fontFace: FONT, margin: 0 }, text: '' } },
    { placeholder: { options: { name: 'title', type: 'title', x: 0.8, y: 2.05, w: 11.7, h: 1.75, fontSize: 48, bold: true, color: K.darkFg, fontFace: FONT, valign: 'top', align: 'left', margin: 0 }, text: '' } },
    { placeholder: { options: { name: 'body', type: 'body', x: 0.8, y: 3.75, w: 11.7, h: 1.8, fontSize: 20, color: K.darkMuted, fontFace: FONT, valign: 'top', margin: 0 }, text: '' } },
  ],
  slideNumber: { x: 12.3, y: 7.0, w: 0.6, h: 0.3, fontSize: 10, color: K.darkMuted, fontFace: FONT, align: 'right' },
});
pres.defineSlideMaster({
  title: 'CONTENT', background: { color: K.bg },
  objects: [
    { placeholder: { options: { name: 'kicker', type: 'body', x: X0, y: 0.38, w: CW, h: 0.36, fontSize: 12, bold: true, color: K.acc, charSpacing: 3, fontFace: FONT, margin: 0 }, text: '' } },
    { placeholder: { options: { name: 'title', type: 'title', x: X0, y: 0.72, w: CW, h: 0.9, fontSize: 34, bold: true, color: K.fg, fontFace: FONT, margin: 0, valign: 'middle', align: 'left' }, text: '' } },
    { text: { text: 'Nitro · Digithon 2026', options: { x: X0, y: 7.02, w: 4, h: 0.3, fontSize: 10, color: K.muted, fontFace: FONT, margin: 0 } } },
  ],
  slideNumber: { x: 12.3, y: 7.02, w: 0.45, h: 0.3, fontSize: 10, color: K.muted, fontFace: FONT, align: 'right' },
});

// ── helpers ──
const shadow = () => ({ type: 'outer', color: '1E2850', opacity: 0.08, blur: 8, offset: 2, angle: 90 });
/** "plain **bold** plain" → text runs. */
const md = (s, o = {}) => s.split(/(\*\*[^*]+\*\*)/).filter(Boolean).map((t) => (t.startsWith('**') ? { text: t.slice(2, -2), options: { ...o, bold: true } } : { text: t, options: { ...o } }));
let section = '';
const AGENT_NAMES = { lead: 'Coordinator', audit: 'Site Auditor', tech: 'Tech Detector', speed: 'Speed Tester', mobile: 'Mobile Tester', a11y: 'Accessibility Checker', ux: 'UX Reviewer', geo: 'AI-Search Checker', redesign: 'Designer', bench: 'Team Matcher', deck: 'Deck Writer' };
/** Readable alt text for every picture (pptxgenjs would otherwise use the file path). */
function altFor(path) {
  const bot = path.match(/bot-(\w+)\.png$/); if (bot) return `${AGENT_NAMES[bot[1]]} agent, pixel robot`;
  const ic = path.match(/ic-(\w+)\.png$/); if (ic) return `${ic[1]} icon`;
  return 'Illustration';
}
function slide(layout, kicker, title, notes) {
  const s = pres.addSlide({ masterName: layout, sectionTitle: section });
  const addImage = s.addImage.bind(s);
  s.addImage = (o) => addImage({ altText: altFor(o.path), ...o });
  if (kicker) s.addText(kicker.toUpperCase(), { placeholder: 'kicker' });
  if (title) s.addText(title, { placeholder: 'title' });
  if (notes) s.addNotes(notes);
  return s;
}
function box(s, x, y, w, h, o = {}) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: o.fill ?? K.panel }, line: { color: o.line ?? K.line, width: o.lineW ?? 1, dashType: o.dash }, shadow: o.flat ? undefined : shadow(), objectName: o.name });
}
function text(s, t, x, y, w, h, o = {}) {
  s.addText(typeof t === 'string' ? md(t) : t, { x, y, w, h, fontSize: 14, color: K.fg, fontFace: FONT, margin: 0, valign: 'top', isTextBox: true, ...o });
}
const TAGS = { today: [K.okbg, K.good], beta: [K.warnbg, K.warn], next: [K.panel2, K.muted], live: [K.okbg, K.good], planned: [K.panel2, K.muted] };
function tag(s, label, x, y, kind = 'today') {
  const [bg, fg] = TAGS[kind] ?? TAGS.next; const w = 0.2 + label.length * 0.085;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x - w, y, w, h: 0.28, rectRadius: 0.14, fill: { color: bg }, line: { color: bg } });
  text(s, label.toUpperCase(), x - w, y, w, 0.28, { fontSize: 9, bold: true, color: fg, align: 'center', valign: 'middle', charSpacing: 1 });
}
/** Card: icon (or robot) + bold title on one row, body text below, optional tag top-right. */
function card(s, x, y, w, h, { icon, bot, title, body, tags = [], border, size = 14 }) {
  box(s, x, y, w, h, { line: border });
  let tx = x + 0.25;
  if (icon) { s.addImage({ path: ICON(icon), x: x + 0.25, y: y + 0.22, w: 0.42, h: 0.42 }); tx = x + 0.8; }
  if (bot) { s.addImage({ path: BOT(bot), x: x + 0.25, y: y + 0.16, w: 0.4, h: 0.55 }); tx = x + 0.8; }
  let right = x + w - 0.2;
  for (const [label, kind] of tags) { tag(s, label, right, y + h - 0.42, kind); right -= 0.25 + label.length * 0.085; }
  text(s, title, tx, y + 0.2, x + w - 0.2 - tx, 0.48, { fontSize: 17, bold: true, valign: 'middle' });
  if (body) text(s, body, x + 0.25, y + 0.78, w - 0.5, h - 0.9, { fontSize: size, color: '44506B' });
}
function grid(s, items, cols, y, h, gap = 0.25) {
  const w = (CW - gap * (cols - 1)) / cols;
  items.forEach((it, i) => card(s, X0 + (i % cols) * (w + gap), y + Math.floor(i / cols) * (h + gap), w, h, it));
}
function stat(s, x, y, w, h, value, label, color = K.fg) {
  box(s, x, y, w, h);
  text(s, value, x + 0.25, y + 0.15, w - 0.5, h * 0.55, { fontSize: 36, bold: true, color, valign: 'middle' });
  text(s, label, x + 0.25, y + h * 0.62, w - 0.5, h * 0.33, { fontSize: 13, color: K.muted });
}
function stats(s, list, y, h = 1.3) {
  const gap = 0.25, w = (CW - gap * (list.length - 1)) / list.length;
  list.forEach(([v, l, c], i) => stat(s, X0 + i * (w + gap), y, w, h, v, l, c));
}
/** Checklist: a green tick (or red cross) and a line of text per item. Rows grow with the estimated line count. */
function checks(s, items, x, y, w, h, size = 16, mark = 'check') {
  const lineH = (size * 1.3) / 72, gap = size * 0.55 / 72, tw = w - 0.42;
  let cy = y;
  for (const it of items) {
    const lines = Math.max(1, Math.ceil((it.replace(/\*\*/g, '').length * size * 0.0072) / tw));
    text(s, mark === 'cross' ? '✕' : '✓', x, cy, 0.35, lineH, { fontSize: size, bold: true, color: mark === 'cross' ? K.bad : K.good });
    text(s, it, x + 0.42, cy, tw, lineH * lines, { fontSize: size });
    cy += lineH * lines + gap;
  }
}
function chips(s, list, x, y, w, size = 13) {
  let cx = x, cy = y; const h = 0.4;
  for (const c of list) {
    const [label, kind] = Array.isArray(c) ? c : [c, ''];
    const cw = 0.35 + label.length * size * 0.0072;
    if (cx + cw > x + w) { cx = x; cy += h + 0.12; }
    const line = { strong: K.good, partial: K.warn, gap: K.bad }[kind] ?? K.line;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: cx, y: cy, w: cw, h, rectRadius: 0.2, fill: { color: K.panel }, line: { color: line, width: kind ? 1.75 : 1 } });
    text(s, label, cx, cy, cw, h, { fontSize: size, bold: true, align: 'center', valign: 'middle' });
    cx += cw + 0.12;
  }
  return cy + h;
}
function arrow(s, x, y, w) { s.addShape(pres.shapes.LINE, { x, y, w, h: 0, line: { color: K.acc, width: 2, dashType: 'dash', endArrowType: 'triangle' } }); }
/** Process flow: boxes joined by arrows. Each step: { icon | bot | bots, title, sub, tone }. */
function flow(s, steps, y, h = 1.75) {
  const aw = 0.35, w = (CW - aw * (steps.length - 1)) / steps.length;
  steps.forEach((st, i) => {
    const x = X0 + i * (w + aw);
    box(s, x, y, w, h, { line: st.tone === 'bad' ? K.bad : st.tone === 'good' ? K.good : undefined, lineW: st.tone ? 1.75 : 1 });
    const bots = st.bots ?? (st.bot ? [st.bot] : []);
    if (bots.length) { const bw = Math.min(0.42, (w - 0.3) / bots.length); bots.forEach((b, j) => s.addImage({ path: BOT(b), x: x + w / 2 - (bots.length * bw) / 2 + j * bw, y: y + 0.18, w: bw * 0.9, h: bw * 0.9 * 1.375 })); }
    else if (st.icon) s.addImage({ path: ICON(st.icon), x: x + w / 2 - 0.25, y: y + 0.2, w: 0.5, h: 0.5 });
    text(s, st.title, x + 0.1, y + 0.82, w - 0.2, 0.36, { fontSize: 15, bold: true, align: 'center', color: st.tone === 'bad' ? K.bad : K.fg });
    text(s, st.sub, x + 0.12, y + 1.18, w - 0.24, h - 1.25, { fontSize: 12, color: K.muted, align: 'center' });
    if (i < steps.length - 1) arrow(s, x + w + 0.03, y + h / 2, aw - 0.06);
  });
}
function banner(s, t, y, tone = 'bad') {
  const [bg, fg] = tone === 'bad' ? [K.badbg, K.fg] : [K.hl, K.fg];
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: X0, y, w: CW, h: 0.55, rectRadius: 0.1, fill: { color: bg }, line: { color: bg } });
  text(s, t, X0 + 0.3, y, CW - 0.6, 0.55, { fontSize: 17, bold: true, color: fg, valign: 'middle' });
}
const note = (s, t, y, h = 0.5) => text(s, t, X0, y, CW, h, { fontSize: 11, color: K.muted, italic: true });
function botRow(s, y, size = 0.6) {
  const ids = ['lead', 'audit', 'tech', 'speed', 'mobile', 'a11y', 'ux', 'geo', 'redesign', 'bench', 'deck'];
  const step = size * 1.35; const x0 = (W - ids.length * step) / 2;
  ids.forEach((id, i) => s.addImage({ path: BOT(id), x: x0 + i * step, y, w: size, h: size * 1.375 }));
}
function ring(s, x, y, d, value, color, label) {
  s.addChart(pres.charts.DOUGHNUT, [{ name: label, labels: ['Score', 'Rest'], values: [value, 100 - value] }], { x, y, w: d, h: d, holeSize: 72, chartColors: [color, 'E6E9F3'], showLegend: false, showValue: false, showPercent: false, showLabel: false, dataBorder: { pt: 0, color: 'FFFFFF' } });
  text(s, String(value), x, y + d * 0.3, d, d * 0.28, { fontSize: 44, bold: true, align: 'center', valign: 'middle' });
  text(s, label, x + d * 0.3, y + d * 0.57, d * 0.4, d * 0.12, { fontSize: 12, color: K.muted, align: 'center', valign: 'middle' });
}

// ════════════════ 1 · The problem ════════════════
// Every slide is a named function, so the main track and the appendix can be ordered freely.
const S = {};
S.title = () => {
  const s = slide('DARK', 'Digithon 2026', null, 'Nitro, presented by Manish Paul (Digital CRM) with Abhishek Kaushik, Rohan Kalra, Saurav Singh and Amrendra Kumar; mentor Mukul Jain. Digithon 2026. Nitro is an AI pre-sales platform. Paste a prospect\'s website and a team of AI agents audits it, redesigns it, matches our available experts and writes a personalised pitch in minutes. A human approves everything before it is sent.');
  text(s, 'Nitro', 0.75, 1.95, 11.7, 1.85, { fontSize: 120, bold: true, color: '8FA5FF', valign: 'middle' });
  s.addText([{ text: 'Great developers, in front of every client.', options: { bold: true, color: K.darkFg, fontSize: 24, breakLine: true } }, { text: 'Powering external business in a supercharged environment.', options: { breakLine: true } }, { text: ' ', options: { fontSize: 10, breakLine: true } }, { text: 'Manish Paul', options: { bold: true, color: K.darkFg, fontSize: 22 } }, { text: '   Digital CRM', options: { fontSize: 16, breakLine: true } }, { text: 'Abhishek Kaushik  ·  Rohan Kalra  ·  Saurav Singh  ·  Amrendra Kumar', options: { fontSize: 16, color: K.darkFg, breakLine: true } }, { text: 'Mentor: ', options: { fontSize: 15 } }, { text: 'Mukul Jain', options: { fontSize: 15, bold: true, color: K.darkFg } }], { placeholder: 'body' });
  botRow(s, 6.05, 0.55);

};
S.p1 = () => {
  const s = slide('CONTENT', 'The problem · 1 of 6', 'Our best people are waiting for their next project', 'Skilled developers between projects are a cost to the organisation, and their time is not visible to clients.');
  text(s, 'Skilled developers between projects wait for work. That time is a **real cost**, and clients never see what these people can do.', X0, 2.0, 5.8, 1.6, { fontSize: 20, color: K.muted });
  checks(s, ['Skilled people wait instead of building', 'Nothing they do is visible to clients', 'Every week of waiting is cost we never recover'], X0, 3.9, 5.8, 2.0, 18, 'cross');
  const ids = ['lead', 'audit', 'tech', 'speed', 'mobile', 'a11y', 'ux', 'geo', 'redesign', 'bench', 'deck', 'lead'];
  ids.forEach((id, i) => { const x = 6.9 + (i % 6) * 0.95, y = 2.1 + Math.floor(i / 6) * 1.75; s.addImage({ path: BOT(id), x, y, w: 0.7, h: 0.96, transparency: 25 }); text(s, 'z', x + 0.66, y - 0.25, 0.3, 0.35, { fontSize: 18, bold: true, color: K.acc }); });
  text(s, 'Developers waiting for their next project', 6.9, 5.7, 5.7, 0.4, { fontSize: 14, color: K.muted, align: 'center' });

};
S.p2 = () => {
  const s = slide('CONTENT', 'The problem · 2 of 6', 'Proposals are slow, generic and rarely convert', 'A proposal needs a lead, research on the prospect\'s site and stack, a draft and a review. That takes days of senior time, so very few go out, and the ones that do are generic and seldom convert.');
  ['Find a lead', 'Research', 'Draft', 'Review', 'Send'].forEach((d, i) => { const x = X0 + i * 1.55; box(s, x, 2.0, 1.35, 1.3); text(s, String(i + 1), x, 2.12, 1.35, 0.55, { fontSize: 22, bold: true, align: 'center', color: K.acc }); text(s, d, x, 2.7, 1.35, 0.45, { fontSize: 14, bold: true, align: 'center' }); });
  text(s, 'Days of senior time for **one** pitch.', 8.5, 2.2, 4.2, 1, { fontSize: 20, color: K.muted });
  stats(s, [['Days', 'of senior time per proposal'], ['Few', 'proposals actually sent'], ['Rare', 'conversions', K.bad]], 3.75, 1.5);

};
S.p3 = () => {
  const s = slide('CONTENT', 'The problem · 3 of 6', 'Reaching out is slow, and nobody knows where to aim', 'No contact list, no shared playbook, and so much preparation that the moment passes. These are qualitative pain points; real numbers will come from our own pipeline data.');
  grid(s, [
    { icon: 'mail', title: 'No contacts', body: 'Who is the CTO? Who owns the website budget? Finding the right person takes days of digging, and the list is never ready.', border: K.bad },
    { icon: 'compass', title: 'No direction', body: 'Which companies? Which angle? Every seller invents their own approach, with no shared playbook for what to say.', border: K.bad },
    { icon: 'turtle', title: 'Slow reach-out', body: 'By the time the research, the deck and the first email are done, the moment has passed and the prospect has moved on.', border: K.bad },
  ], 3, 2.0, 2.8);
  banner(s, 'Result: the right person is rarely reached at the right moment.', 5.4);

};
S.p4 = () => {
  const s = slide('CONTENT', 'The problem', 'Demos take days to build. Nitro builds one in minutes.', 'Building one personalised demo for a prospect takes days of developer time, so we build one only when a deal is almost won. Nitro builds one in about 1.5 to 3 minutes per run, so every prospect can get one, and the agents are always available, working 24x7 in the background.');
  text(s, 'TIME TO BUILD ONE PERSONALISED DEMO FOR A PROSPECT', X0, 1.95, CW, 0.35, { fontSize: 12, bold: true, color: K.muted, charSpacing: 3 });
  [['By hand', 1, K.bad, 'Days', 'Days of developer time'], ['With Nitro', 0.03, K.good, '1.5–3 min', '']].forEach(([l, f, c, v, inner], i) => {
    const y = 2.45 + i * 0.8;
    text(s, l, X0, y, 2.4, 0.6, { fontSize: 17, bold: true, valign: 'middle' });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 3.1, y: y + 0.08, w: 7.6, h: 0.44, rectRadius: 0.1, fill: { color: 'E6E9F3' }, line: { color: 'E6E9F3' } });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 3.1, y: y + 0.08, w: Math.max(7.6 * f, 0.25), h: 0.44, rectRadius: 0.1, fill: { color: c }, line: { color: c } });
    if (inner) text(s, inner, 3.3, y + 0.08, 7.2, 0.44, { fontSize: 14, bold: true, italic: true, color: 'FFFFFF', valign: 'middle' });
    text(s, v, 10.9, y, 1.8, 0.6, { fontSize: 17, bold: true, color: c, valign: 'middle' });
  });
  grid(s, [
    { title: 'Every prospect gets one', body: 'Not only the deals that are almost won: a demo built on their own site, before the first meeting.' },
    { title: 'Always available · 24x7', body: 'Agents keep working in the background, so a demo is ready whenever sales needs one.', border: K.good },
  ], 2, 4.3, 1.6);
};
S.p5 = () => {
  const s = slide('CONTENT', 'The problem · 5 of 6', 'We rarely match the skills we have to the work we chase', 'There is no live view of who is available with which skills. Deals are chased without knowing whether we can staff them, and the right people wait while the right deals go elsewhere.');
  text(s, 'WHAT THE CLIENT NEEDS', X0, 1.95, 4.5, 0.3, { fontSize: 12, bold: true, color: K.muted, charSpacing: 2 });
  text(s, 'WHO IS AVAILABLE WITH THOSE SKILLS', 8.3, 1.95, 4.5, 0.3, { fontSize: 12, bold: true, color: K.muted, charSpacing: 2 });
  chips(s, [['Shopify', 'gap'], ['Accessibility', 'gap'], ['Web performance', 'gap'], ['Adobe Analytics', 'gap']], X0, 2.4, 4.6);
  chips(s, ['Java', 'Python', 'Next.js', 'Manual QA'], 8.3, 2.4, 4.5);
  text(s, '?', 5.4, 2.0, 2.5, 1.8, { fontSize: 90, bold: true, color: K.bad, align: 'center' });
  grid(s, [
    { title: 'No live view', body: 'Of who is available, with which skills.', border: K.bad },
    { title: 'Deals chased blind', body: 'Without knowing whether we can staff them.', border: K.bad },
    { title: 'The right people wait', body: 'While the right deals go elsewhere.', border: K.bad },
  ], 3, 4.3, 1.6);

};
S.p6 = () => {
  const s = slide('CONTENT', 'The problem', 'The client never sees what we would do for them', 'Generic proposals look like every other vendor. Nothing in them shows we looked at the client\'s own site, so ours lands in the client\'s inbox as one more unread proposal that looks like all the others.');
  box(s, X0, 1.95, 6.6, 4.3);
  s.addShape(pres.shapes.RECTANGLE, { x: X0 + 0.02, y: 1.97, w: 6.56, h: 0.5, fill: { color: K.panel2 }, line: { color: K.panel2 } });
  text(s, 'To: cmo@prospect.com · Subject: Proposal for your esteemed consideration', X0 + 0.25, 1.97, 6.2, 0.5, { fontSize: 11, color: K.muted, valign: 'middle' });
  text(s, [{ text: 'Dear Sir/Madam,', options: { breakLine: true } }, { text: 'We are pleased to submit our proposal for your consideration.', options: { breakLine: true } }, { text: 'We have 15+ years of experience and skilled professionals.', options: { breakLine: true } }, { text: 'We look forward to a fruitful association. Regards.' }], X0 + 0.35, 2.7, 5.9, 2.6, { fontSize: 16, fontFace: 'Cambria', paraSpaceAfter: 10 });
  s.addText('SENT', { x: X0 + 4.4, y: 5.1, w: 1.8, h: 0.75, fontSize: 30, bold: true, color: K.bad, align: 'center', valign: 'middle', rotate: -12, line: { color: K.bad, width: 3 }, fontFace: FONT, isTextBox: true });
  // the client's inbox: our email lands on top of other unread vendor proposals
  const ix = 7.5, iw = W - X0 - ix, rh = 0.46;
  box(s, ix, 1.95, iw, 0.55 + rh * 6);
  s.addShape(pres.shapes.RECTANGLE, { x: ix + 0.02, y: 1.97, w: iw - 0.04, h: 0.5, fill: { color: K.panel2 }, line: { color: K.panel2 } });
  text(s, 'Inbox · cmo@prospect.com', ix + 0.2, 1.97, iw - 1.6, 0.5, { fontSize: 12, bold: true, valign: 'middle' });
  text(s, [{ text: 'Unread ', options: { color: K.muted } }, { text: ' 6 ', options: { color: 'FFFFFF', highlight: K.acc } }], ix + iw - 1.5, 1.97, 1.3, 0.5, { fontSize: 11, bold: true, align: 'right', valign: 'middle' });
  [['Proposal for your esteemed consideration', 'Us'], ['Proposal for your consideration', 'Vendor A'], ['Introducing our capabilities', 'Vendor B'], ['Partnership opportunity', 'Vendor C'], ['Following up on our proposal', 'Vendor D'], ['Our services overview', 'Vendor E']].forEach(([t, f], r) => {
    const y = 2.5 + r * rh;
    if (r === 0) s.addShape(pres.shapes.RECTANGLE, { x: ix + 0.02, y, w: iw - 0.04, h: rh, fill: { color: K.hl }, line: { color: K.hl } });
    s.addShape(pres.shapes.OVAL, { x: ix + 0.2, y: y + rh / 2 - 0.05, w: 0.1, h: 0.1, fill: { color: K.acc }, line: { color: K.acc } });
    text(s, t, ix + 0.42, y, iw - 1.6, rh, { fontSize: 11, bold: true, valign: 'middle' });
    text(s, f, ix + iw - 1.15, y, 0.95, rh, { fontSize: 10, color: K.muted, align: 'right', valign: 'middle' });
  });
  text(s, 'One more proposal that looks like all the others.', ix, 5.45, iw, 0.7, { fontSize: 17, bold: true, color: K.muted });

};
S.pshort = () => {
  const s = slide('CONTENT', 'The problem · in short', 'Pre-sales today is slow, costly and not personal', 'Summary of the pre-sales pain points: slow reach, expensive pitches, talent between projects used badly, no personalisation, no scale, and no proof in the room during CTO meetings.');
  grid(s, [
    { icon: 'turtle', title: 'Slow reach', body: 'Finding a lead, researching and writing takes days. We reach only a few CTOs a month.' },
    { icon: 'money', title: 'Expensive', body: 'Senior architects spend days on each pitch. Most pitches lose, and that time is never recovered.' },
    { icon: 'chair', title: 'Talent not used well', body: 'Developers between projects wait instead of building proof for the next client.' },
    { icon: 'doc', title: 'Not personalised', body: 'The same slides go to every client. Nothing about their site, their stack or their customers.' },
    { icon: 'repeat', title: 'Does not scale', body: 'Manual research means very few proposals go out, however many leads we have.' },
    { icon: 'handshake', title: 'No proof in the room', body: 'In a CTO meeting we talk about skills. We cannot show what we would fix on their site.' },
  ], 3, 1.9, 1.85);
  banner(s, 'Result: fewer meetings, lower win rates, and unallocated capacity that keeps costing money.', 6.15);

};
S.whatif = () => {
  const s = slide('DARK', 'What if…', null, 'The turning point of the story: show, do not tell. The client sees their own site improved before any contract.');
  text(s, 'What if the prospect could see their own website, improved, before they signed anything?', 0.8, 2.2, 11.7, 2.5, { fontSize: 48, bold: true, color: K.darkFg });
  text(s, 'That is Nitro.', 0.8, 4.9, 11.7, 0.6, { fontSize: 24, bold: true, color: 'A9B8FF' });

};
S.paste = () => {
  const s = slide('CONTENT', 'The solution', 'Paste a URL. That\'s it.', 'One input: the prospect\'s website. The server checks it is a public address, then a whole office of AI agents goes to work.');
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 2.9, y: 2.1, w: 7.5, h: 0.95, rectRadius: 0.47, fill: { color: K.panel }, line: { color: K.acc, width: 2.5 }, shadow: shadow() });
  s.addImage({ path: ICON('globe'), x: 3.2, y: 2.3, w: 0.55, h: 0.55 });
  text(s, 'www.allbirds.com', 3.95, 2.1, 4.5, 0.95, { fontSize: 26, bold: true, valign: 'middle' });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 8.6, y: 2.27, w: 1.6, h: 0.6, rectRadius: 0.3, fill: { color: K.acc }, line: { color: K.acc } });
  text(s, 'Launch', 8.6, 2.27, 1.6, 0.6, { fontSize: 17, bold: true, color: 'FFFFFF', align: 'center', valign: 'middle' });
  text(s, '…and a whole office of AI agents goes to work.', X0, 3.45, CW, 0.6, { fontSize: 22, color: K.muted, align: 'center' });
  botRow(s, 4.4, 0.8);

};
S.team = () => {
  const s = slide('CONTENT', 'The team', 'Meet the 13 agents', 'Thirteen agents, each with one job. The Coordinator plans the run; the Market Researcher reads the latest news on the company first; the others audit, test, design, match people and write the pitch. The Tender Scout finds work in government tenders. Every tool call posts to a live feed.');
  const P = [['lead', 'Coordinator', 'Plans and runs the job'], ['research', 'Market Researcher', 'Latest news on the company'], ['tenders', 'Tender Scout', 'Triages government tenders'], ['audit', 'Site Auditor', 'Checks the website'], ['tech', 'Tech Detector', 'Finds the technologies'], ['speed', 'Speed Tester', 'Measures page speed'], ['mobile', 'Mobile Tester', 'Checks it on a phone'],
    ['a11y', 'Accessibility Checker', 'Works for everyone?'], ['ux', 'UX Reviewer', 'Usability and design'], ['geo', 'AI-Search Checker', 'Visible in AI search?'], ['redesign', 'Designer', 'Builds the new homepage'], ['bench', 'Team Matcher', 'Finds available experts'], ['deck', 'Deck Writer', 'Writes deck and proposal']];
  const cols = 7, gap = 0.16, w = (CW - gap * (cols - 1)) / cols, h = 2.05;
  P.forEach(([id, n, r], i) => {
    const x = X0 + (i % cols) * (w + gap), y = 1.95 + Math.floor(i / cols) * (h + gap);
    box(s, x, y, w, h);
    s.addImage({ path: BOT(id), x: x + w / 2 - 0.3, y: y + 0.18, w: 0.6, h: 0.825 });
    text(s, n, x + 0.08, y + 1.08, w - 0.16, 0.5, { fontSize: 13, bold: true, align: 'center', valign: 'middle' });
    text(s, r, x + 0.08, y + 1.55, w - 0.16, 0.42, { fontSize: 10.5, color: K.muted, align: 'center' });
  });
  const x = X0 + 6 * (w + gap), y = 1.95 + h + gap;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: K.acc }, line: { color: K.acc } });
  text(s, '13 agents\n\n12 in every run\n1 finds tenders', x + 0.05, y, w - 0.1, h, { fontSize: 14, bold: true, color: 'FFFFFF', align: 'center', valign: 'middle' });
  note(s, 'The Market Researcher runs first in every analysis; the Tender Scout triages government tenders. All are listed in the agent marketplace.', 6.35);
};
S.tenders = () => {
  const s = slide('CONTENT', 'Government tenders', 'The Tender Scout finds the work. And decides if it fits.', 'The Tender Scout watches the GeM portal, CPPP RSS feeds and state tender feeds. For each tender it reads the scope, asks whether it is digital work, matches it to our skills, and decides with a reason. A relevant tender goes to the agents like a website; one that does not fit is dropped and the reason is logged. Example: a MeitY website revamp and GIGW accessibility audit is relevant (web, accessibility); Delhi Metro civil works for a depot is not (civil works, not digital). Simulated on the home dashboard today, and callable as the tenders_triage tool over MCP.');
  // sources
  text(s, 'WATCHING', X0, 1.95, 2.2, 0.3, { fontSize: 11, bold: true, color: K.muted, charSpacing: 2 });
  [['gov', 'GeM portal'], ['news', 'CPPP RSS feed'], ['globe2', 'State tender feeds']].forEach(([ic, t], k) => {
    const y = 2.35 + k * 0.62; box(s, X0, y, 2.2, 0.5, { flat: true });
    s.addImage({ path: ICON(ic), x: X0 + 0.1, y: y + 0.09, w: 0.32, h: 0.32 });
    text(s, t, X0 + 0.5, y, 1.65, 0.5, { fontSize: 12, bold: true, valign: 'middle' });
  });
  arrow(s, X0 + 2.3, 3.0, 0.45);
  // the agent's checks
  const bx = 3.45, bw = 4.9;
  box(s, bx, 1.9, bw, 4.3);
  s.addImage({ path: BOT('tenders'), x: bx + 0.25, y: 2.05, w: 0.5, h: 0.69 });
  text(s, 'Tender Scout', bx + 0.9, 2.08, bw - 1.1, 0.4, { fontSize: 17, bold: true });
  text(s, 'Checks every tender, step by step', bx + 0.9, 2.45, bw - 1.1, 0.3, { fontSize: 11, italic: true, color: K.muted });
  ['Read the scope', 'Digital work?', 'Match our skills', 'Decide, with a reason'].forEach((t, k) => {
    const y = 2.95 + k * 0.78;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: bx + 0.25, y, w: bw - 0.5, h: 0.62, rectRadius: 0.08, fill: { color: K.panel2 }, line: { color: K.panel2 } });
    s.addShape(pres.shapes.OVAL, { x: bx + 0.4, y: y + 0.14, w: 0.34, h: 0.34, fill: { color: K.acc }, line: { color: K.acc } });
    text(s, String(k + 1), bx + 0.4, y + 0.14, 0.34, 0.34, { fontSize: 11, bold: true, color: 'FFFFFF', align: 'center', valign: 'middle' });
    text(s, t, bx + 0.9, y, bw - 1.2, 0.62, { fontSize: 14, bold: true, valign: 'middle' });
  });
  arrow(s, bx + bw + 0.1, 3.0, 0.45);
  // two verdicts
  const vx = 9.0, vw = W - X0 - vx;
  [[true, 'Website revamp and GIGW accessibility audit', 'Ministry of Electronics and IT', 'Relevant: web, accessibility', 'Sent to the agents'], [false, 'Civil works for depot expansion', 'Delhi Metro Rail Corporation', 'Not relevant: civil works', 'Dropped, reason logged']].forEach(([ok, t, b, v, n], k) => {
    const y = 1.9 + k * 2.2, c = ok ? K.good : K.muted;
    box(s, vx, y, vw, 2.0, { line: ok ? K.good : K.line, lineW: ok ? 2 : 1 });
    text(s, t, vx + 0.2, y + 0.15, vw - 0.4, 0.55, { fontSize: 13, bold: true });
    text(s, b, vx + 0.2, y + 0.72, vw - 0.4, 0.3, { fontSize: 10.5, color: K.muted });
    text(s, (ok ? '✓ ' : '✕ ') + v, vx + 0.2, y + 1.08, vw - 0.4, 0.38, { fontSize: 13, bold: true, color: ok ? K.good : K.bad });
    text(s, n, vx + 0.2, y + 1.48, vw - 0.4, 0.3, { fontSize: 11, color: c });
  });
  note(s, 'Simulated on the home dashboard today · also callable as the tenders_triage tool over MCP.', 6.4, 0.35);
};
S.howold = () => {
  const s = slide('CONTENT', 'How it works', 'One URL in. A send-ready pitch out.', 'A run goes: paste a URL, the Coordinator plans, seven checks run in parallel, the Designer and Team Matcher build in parallel, the Deck Writer writes, and a human reviews. About 1.5 to 3 minutes.');
  flow(s, [
    { icon: 'globe', title: '1 · Paste URL', sub: 'Checked to be a public site' },
    { bot: 'lead', title: '2 · Plan', sub: 'Coordinator picks the next step' },
    { bots: ['audit', 'tech', 'speed', 'mobile', 'a11y', 'ux', 'geo'], title: '3 · Audit', sub: 'Seven checks in parallel' },
    { bots: ['redesign', 'bench'], title: '4 · Build', sub: 'Redesign + team match' },
    { bot: 'deck', title: '5 · Write', sub: 'Deck and proposal' },
    { icon: 'person', title: '6 · You review', sub: 'Nothing is sent without a human', tone: 'good' },
  ], 2.1, 2.0);
  text(s, 'A full run takes about **1.5 to 3 minutes**. Every step streams live to the screen.', X0, 4.6, CW, 0.6, { fontSize: 20, color: K.muted });
  checks(s, ['Tools measure: Lighthouse, axe-core, Playwright, Chrome DevTools Protocol', 'The model (Claude) plans, judges design and clarity, and designs', 'Code guardrails keep the order, retries and step budget safe'], X0, 5.25, CW, 1.6, 15);

};
S.audit = () => {
  const s = slide('CONTENT', '1 · The audit · real run on allbirds.com', 'A report card, with evidence', 'Real result from allbirds.com: 64 out of 100, grade D. Speed 40 (F), mobile 87 (B), accessibility 70 (C), UX 60 (D), AI search 62 (D). Every finding carries its evidence.');
  ring(s, X0, 1.95, 3.6, 64, K.bad, 'grade D');
  s.addChart(pres.charts.BAR, [{ name: 'Score', labels: ['Speed (F)', 'Mobile (B)', 'Accessibility (C)', 'UX (D)', 'AI search (D)'], values: [40, 87, 70, 60, 62] }], {
    x: 4.6, y: 1.9, w: 8.1, h: 3.7, barDir: 'bar', chartColors: [K.bad, K.good, K.warn, K.bad, K.bad], valAxisMaxVal: 100, valAxisMinVal: 0, showValue: true, dataLabelPosition: 'outEnd', dataLabelFontSize: 13, dataLabelFontFace: '+mn-lt', dataLabelColor: K.fg,
    catAxisLabelFontSize: 14, catAxisLabelFontFace: '+mn-lt', catAxisLabelColor: K.fg, valAxisHidden: true, valGridLine: { style: 'none' }, catGridLine: { style: 'none' }, showLegend: false, catAxisOrientation: 'maxMin', barGapWidthPct: 60,
  });
  chips(s, ['Lighthouse (speed)', 'axe-core (accessibility)', 'Playwright (mobile)', 'Vision model (UX)', 'Every finding carries its evidence'], X0, 5.95, CW);

};
S.tech = () => {
  const s = slide('CONTENT', 'Their technology · real Allbirds run', 'We read their network traffic like a flight recorder', 'From 389 network requests Nitro detected 9 technologies across 25 domains; customer data goes to 5 analytics, tag and ad tools. Each technology is a way into a conversation about logistics, data, finance and cloud, mapped to our people and our in-house innovations.');
  stats(s, [['389', 'requests'], ['9', 'technologies'], ['5', 'tools get customer data'], ['25', 'domains']], 1.95, 1.3);
  const end = chips(s, [['Vue.js', 'partial'], ['Shopify', ''], ['Google Analytics 4', 'strong'], ['Microsoft Clarity', ''], ['Google Tag Manager', 'strong'], ['Meta Pixel', ''], ['Google Ads', ''], ['Cloudflare', 'strong'], ['Microsoft Azure', 'strong']], X0, 3.6, CW, 15);
  box(s, X0, end + 0.35, CW, 1.05, { fill: K.hl, line: K.hl, flat: true });
  text(s, '**Every technology is a way into a conversation:** logistics, data, finance and cloud, mapped to our people and our in-house innovations.', X0 + 0.3, end + 0.35, CW - 0.6, 1.05, { fontSize: 15, valign: 'middle' });

};
S.redesign = () => {
  const s = slide('CONTENT', 'The redesign · real Allbirds run', 'Their own site, improved, before they sign', 'The Designer extracts their colours, fonts and content and builds a new homepage in HTML in about 40 seconds. The same inspectors re-check it: accessibility 70 to 98, mobile 87 to 100.');
  const iw = 4.25, ih = iw * 9.3 / 16;
  [['allbirds-before.jpg', 'BEFORE', X0], ['allbirds-after.jpg', 'AFTER', X0 + iw + 0.25]].forEach(([f, l, x]) => {
    s.addImage({ path: A(f), x, y: 2.0, w: iw, h: ih, altText: `${l === 'BEFORE' ? 'Current' : 'Redesigned'} allbirds.com homepage` });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x + 0.12, y: 2.12, w: 1.05, h: 0.34, rectRadius: 0.17, fill: { color: '000000', transparency: 35 }, line: { color: '000000', transparency: 35 } });
    text(s, l, x + 0.12, 2.12, 1.05, 0.34, { fontSize: 11, bold: true, color: 'FFFFFF', align: 'center', valign: 'middle' });
  });
  stat(s, 9.55, 2.0, 3.18, 1.35, '70 → 98', 'accessibility score', K.good);
  stat(s, 9.55, 3.55, 3.18, 1.35, '87 → 100', 'mobile score', K.good);
  checks(s, ['Built from their real colours, fonts and content', 'Re-checked by the same inspectors', 'Real HTML, designed in about 40 seconds'], X0, 4.75, 8.8, 1.6, 15);

};
S.people = () => {
  const s = slide('CONTENT', 'The people · sample roster', 'Real developers who are free now', 'The Team Matcher scores how well our organisation fits the work, names available experts and estimates effort and price. The roster, skills and rates shown here are sample data behind an adapter, ready for real HR data.');
  ring(s, X0, 1.95, 3.2, 88, K.good, 'org match');
  const end = chips(s, [['Next.js / React', 'strong'], ['UX / UI design', 'strong'], ['QA automation', 'strong'], ['Web performance', 'strong'], ['Gap: Shopify / commerce', 'gap']], 4.2, 1.95, 8.5);
  const D = [['Aarav Mehta', 'Senior Frontend Engineer', 93, 'speed'], ['Dev Malhotra', 'Senior Frontend Engineer', 93, 'mobile'], ['Vikram Das', 'Design Systems Engineer', 82, 'ux'], ['Ananya Rao', 'UX Designer', 72, 'redesign'], ['Isha Patel', 'QA Automation Engineer', 72, 'a11y'], ['Zoya Ali', 'Accessibility Specialist', 71, 'geo']];
  const w = (8.5 - 0.2) / 2;
  D.forEach(([n, r, f, id], i) => { const x = 4.2 + (i % 2) * (w + 0.2), y = end + 0.3 + Math.floor(i / 2) * 0.95; box(s, x, y, w, 0.8); s.addImage({ path: BOT(id), x: x + 0.15, y: y + 0.12, w: 0.41, h: 0.56 }); text(s, n, x + 0.7, y + 0.08, w - 1.6, 0.35, { fontSize: 14, bold: true }); text(s, r, x + 0.7, y + 0.42, w - 1.6, 0.3, { fontSize: 11, color: K.muted }); text(s, `${f}%`, x + w - 0.95, y, 0.8, 0.8, { fontSize: 18, bold: true, color: K.acc, align: 'right', valign: 'middle' }); });
  note(s, 'Names, skills and match scores come from a sample roster. With real HR data the match also gives effort and price.', 6.4);

};
S.pitch = () => {
  const s = slide('CONTENT', 'The pitch', 'A deck ready for their CMO', 'The Deck Writer produces a 9-slide PowerPoint deck and a written proposal: their site today (64/100, grade D), what is costing them customers, before and after, why us (88/100 organisation match), and the plan with team, effort, timeline and price. Every number comes from the audit, the redesign and the match. Nothing is sent until a human approves.');
  const w = 2.25, gap = 0.22, h = 3.0, y0 = 1.95;
  const head = (x, y, n, t) => { s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h: 0.75, rectRadius: 0.12, fill: { color: K.acc }, line: { color: K.acc } }); s.addShape(pres.shapes.RECTANGLE, { x, y: y + 0.45, w, h: 0.3, fill: { color: K.acc }, line: { color: K.acc } }); text(s, `${n}  ${t}`, x + 0.15, y + 0.05, w - 0.3, 0.68, { fontSize: 12, bold: true, color: 'FFFFFF', valign: 'middle' }); };
  for (let i = 0; i < 5; i++) {
    const x = X0 + i * (w + gap), y = y0 + Math.abs(i - 2) * 0.12;
    box(s, x, y, w, h);
    head(x, y, i + 1, ['Your site today', 'What is costing you customers', 'Before and after', 'Why us', 'The plan'][i]);
    const bx = x + 0.2, by = y + 0.95, bw = w - 0.4;
    if (i === 0) { text(s, '64', bx, by + 0.1, bw, 1.0, { fontSize: 54, bold: true, color: K.bad, align: 'center' }); text(s, '/ 100 · grade D', bx, by + 1.2, bw, 0.35, { fontSize: 11, color: K.muted, align: 'center' }); }
    if (i === 1) [['Speed', 40], ['UX', 60], ['AI search', 62]].forEach(([n, v], k) => { const yy = by + 0.15 + k * 0.5; text(s, n, bx, yy, 0.85, 0.3, { fontSize: 10 }); s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: bx + 0.85, y: yy + 0.08, w: 0.95 * v / 100, h: 0.16, rectRadius: 0.08, fill: { color: K.bad }, line: { color: K.bad } }); text(s, String(v), bx + 1.55, yy, 0.3, 0.3, { fontSize: 10, bold: true, align: 'right' }); });
    if (i === 2) { const iw = (bw - 0.1) / 2; s.addImage({ path: A('allbirds-before.jpg'), x: bx, y: by + 0.05, w: iw, h: iw * 1.25, altText: 'Allbirds homepage before' }); s.addImage({ path: A('allbirds-after.jpg'), x: bx + iw + 0.1, y: by + 0.05, w: iw, h: iw * 1.25, altText: 'Allbirds homepage after' }); text(s, 'Accessibility 70 → 98', bx, by + 1.5, bw, 0.3, { fontSize: 10, color: K.muted, align: 'center' }); }
    if (i === 3) { ['speed', 'mobile', 'ux', 'redesign'].forEach((id, k) => s.addImage({ path: BOT(id), x: bx + 0.12 + k * 0.42, y: by + 0.1, w: 0.36, h: 0.5 })); text(s, '88/100', bx, by + 0.75, bw, 0.5, { fontSize: 22, bold: true, color: K.good, align: 'center' }); text(s, 'organisation match', bx, by + 1.25, bw, 0.3, { fontSize: 10, color: K.muted, align: 'center' }); }
    if (i === 4) [['Team', 'named'], ['Effort', 'person-days'], ['Timeline', 'weeks'], ['Price', 'range']].forEach(([a, b], k) => { const yy = by + k * 0.42; text(s, a, bx, yy, 0.9, 0.35, { fontSize: 11 }); text(s, b, bx + 0.8, yy, bw - 0.8, 0.35, { fontSize: 11, bold: true, color: K.acc, align: 'right' }); });
  }
  text(s, '9 slides plus a written proposal. Every number is read from the audit, the redesign and the match. **Nothing is sent until a human approves.**', X0, 5.45, CW, 0.9, { fontSize: 18, color: K.muted, align: 'center' });
};
S.answers = () => {
  const s = slide('CONTENT', 'Pain → answer', 'Every pain, answered. Honestly.', 'Six of the eight pains are answered today. The audit gives a concrete angle to open with, which partly answers the lack of direction. Contact finding and outreach drafts are not built yet and are the first items on the roadmap.');
  const rows = [['Slow, expensive pitches', 'Agents do the research; experts only review', 'Today'], ['Talent between projects', 'Matches available developers to the job and shows the capacity put to work', 'Today'], ['Demos are slow to build', 'A redesigned homepage in about 40 seconds', 'Today'], ['Not personalised', 'Built from their own site, stack, colours and content', 'Today'], ['Skills not matched', 'Org match score, per-skill coverage, gaps and named people (sample data)', 'Today'], ['No proof in the room', 'Before and after on their own site, during the meeting', 'Today'], ['No direction', 'The audit gives a concrete, evidence-backed angle to open with', 'Partly'], ['No contacts', 'Contact finder and outreach drafts', 'Next']];
  const head = (t) => ({ text: t, options: { bold: true, color: K.muted, fontSize: 11, fill: { color: K.bg } } });
  const tone = (t) => (t === 'Today' ? [K.okbg, K.good] : t === 'Partly' ? [K.warnbg, K.warn] : [K.badbg, K.bad]);
  s.addTable([[head('THE PAIN'), head('WHAT NITRO DOES'), head('STATUS')], ...rows.map(([p, a, st]) => [{ text: p, options: { bold: true, fontSize: 14 } }, { text: a, options: { fontSize: 13, color: K.muted } }, { text: st, options: { bold: true, fontSize: 12, align: 'center', color: tone(st)[1], fill: { color: tone(st)[0] } } }])],
    { x: X0, y: 1.95, w: CW, colW: [3.2, 7.2, CW - 10.4], rowH: 0.5, fontFace: FONT, color: K.fg, border: { type: 'solid', color: K.line, pt: 0.75 }, fill: { color: K.panel }, valign: 'middle' });
  note(s, 'Contact finding and outreach drafts are not built yet; they are the next items on the roadmap.', 6.55);

};
S.fullstack = () => {
  const s = slide('CONTENT', 'Insights across the stack', 'From web front end to back end to DevOps', 'One URL gives a full-stack view. Today Nitro covers the front end, detects back-end and cloud technologies, measures performance and checks AI readiness. Deeper back-end checks, automated tests, journeys and locales are next.');
  grid(s, [
    { icon: 'desktop', title: 'Web front end', tags: [['today', 'today']], body: 'Frameworks (React, Next.js, Vue), layout, mobile, accessibility, UX and design, with HTML improvements.' },
    { icon: 'db', title: 'Back end', tags: [['today', 'today']], body: 'Server languages (Java, .NET, Python, PHP), CMS and commerce. Next: API speed, errors, caching.' },
    { icon: 'cloud', title: 'DevOps and cloud', tags: [['today', 'today']], body: 'CDN, hosting and cloud (Cloudflare, Azure, AWS), security and cache headers. Next: TLS, HTTP/3.' },
    { icon: 'bolt', title: 'Performance first', tags: [['today', 'today']], body: 'Lighthouse and Core Web Vitals (LCP, CLS, TBT), heavy scripts and third-party weight.' },
    { icon: 'test', title: 'Quality and testing', tags: [['next', 'next']], body: 'Automated tests, agent-driven user journeys and checks across locales and languages.' },
    { icon: 'robot', title: 'AI readiness', tags: [['today', 'today']], body: 'Visibility in AI search, structured data and llms.txt. If needed, a simple RAG chat demo.' },
  ], 3, 1.9, 1.85);
  banner(s, 'One URL, a full-stack view, and every insight mapped to the available experts who can deliver it.', 6.15, 'info');

};
S.journeys = () => {
  const s = slide('CONTENT', 'Automated tests and agent-driven journeys', 'Agents use the site like a real customer', 'Next in the marketplace: the Journey Runner walks key journeys (search, product, cart, checkout), the Test Writer turns them into Playwright tests the client keeps, and the Locale Tester runs them across languages and regions. Each step gets an LLM score with a reason. ');
  flow(s, [
    { icon: 'home', title: 'Home', sub: 'Page loads' }, { icon: 'search', title: 'Search', sub: 'Finds a product' }, { icon: 'shoe', title: 'Product', sub: 'Options work' },
    { icon: 'cart', title: 'Cart ✕', sub: 'Example: button hidden on phones', tone: 'bad' }, { icon: 'card', title: 'Checkout', sub: 'Not reached' },
  ], 1.9, 1.6);
  text(s, 'Locales to test', X0, 3.85, 5.2, 0.4, { fontSize: 16, bold: true });
  chips(s, ['en-IN', 'hi-IN', 'en-US', 'de-DE', 'ja-JP', 'ar-AE (right-to-left)'], X0, 4.35, 5.4, 14);
  note(s, 'Planned agents: Journey Runner, Test Writer and Locale Tester.', 5.55, 0.35);
  checks(s, ['Each journey becomes an **automated Playwright test** the client keeps', 'Runs across **locales**: languages, currency, dates, right-to-left', 'Every step gets an **LLM score** with a reason and a screenshot', 'Shows exactly where real customers get stuck'], 6.3, 3.85, 6.4, 2.6, 16);

};
S.outputs = () => {
  const s = slide('CONTENT', 'What the prospect gets', 'Not just a report: things they can use', 'Outputs: LLM scores with reasons using one rubric (beta), a redesigned homepage in real HTML (today), a simple RAG chat assistant built from their pages if needed (next), and a personalised deck and proposal (today).');
  grid(s, [
    { icon: 'scale', title: 'LLM scores', tags: [['beta', 'beta']], body: 'Clear scores with reasons, same rubric for every site. Tools measure; the model judges design and clarity.' },
    { icon: 'brick', title: 'HTML fixes', tags: [['today', 'today']], body: 'A redesigned homepage in real HTML, built from their brand. Next: ready-to-paste fixes per issue.' },
    { icon: 'chat', title: 'RAG chat', tags: [['if needed', 'next']], body: 'A small chat assistant built from their own pages, answering with source links.' },
    { icon: 'chart', title: 'Deck + proposal', tags: [['today', 'today']], body: 'A personalised pitch deck and proposal with a named team, effort and price.' },
  ], 4, 1.95, 2.55);
  stats(s, [['1 URL', 'is all we need to start', K.good], ['~3 min', 'for a full run'], ['0', 'things sent without a human', K.good]], 4.85, 1.35);

};
S.office = () => {
  const s = slide('CONTENT', 'Watch it work', 'The whole run, live', 'In the app every tool call posts to a live feed, results land as cards, and a pixel-art office shows which agent is busy and who hands work to whom. Every run is saved and can be replayed for free. At the end, the Coordinator asks a human to review.');
  s.addImage({ path: A('pptx/office.png'), x: X0, y: 1.95, w: 6.9, h: 6.9 * 547 / 812, altText: 'Pixel-art office where the AI agents work' });
  checks(s, ['Every tool call posts to the **live feed**', 'Results land as **cards**; the office shows who is busy', 'Agents **hand work** to each other', 'Every run is saved: **replayed for free**, at any speed', 'At the end, the Coordinator asks a **human to review**'], 7.85, 2.1, 4.9, 4.3, 17);

};
S.experts = () => {
  const s = slide('CONTENT', 'Agents + people', 'AI speed, combined with our amazing developers', 'Agents do the heavy lifting at scale, around the clock. Our experts check the numbers, add real project know-how, adjust plan, team and price, and own the CTO conversation. The result is fast, streamlined and fine-tuned.');
  const w = 5.6;
  box(s, X0, 1.95, w, 2.75); text(s, '🤖  The agents do the heavy lifting', X0 + 0.3, 2.1, w - 0.6, 0.5, { fontSize: 19, bold: true });
  checks(s, ['Crawl, measure and test the site', 'Detect the full tech stack', 'Score, redesign and draft the pitch', 'Work 24x7, run after run'], X0 + 0.3, 2.75, w - 0.6, 2.5, 16);
  text(s, '+', X0 + w, 2.7, CW - 2 * w, 1.2, { fontSize: 60, bold: true, color: K.acc, align: 'center', valign: 'middle' });
  box(s, X0 + CW - w, 1.95, w, 2.75); text(s, '🧑‍💻  Our experts fine-tune it', X0 + CW - w + 0.3, 2.1, w - 0.6, 0.5, { fontSize: 19, bold: true });
  checks(s, ['Check every finding and number', 'Add real project know-how', 'Adjust the plan, team and price', 'Own the conversation with the CTO'], X0 + CW - w + 0.3, 2.75, w - 0.6, 2.5, 16);
  banner(s, '= A pitch that is fast, streamlined and fine-tuned, with real experts behind every word.', 5.05, 'info');

};
S.engage = () => {
  const s = slide('CONTENT', 'Engaging our people', 'Every review puts an available expert to work', 'When a run finishes, the Review Assigner (planned) gives it to an available developer with the right skills. They get a notification, review and fine-tune, sign off, and get credit on the pitch. Time between projects becomes useful, visible work.');
  flow(s, [
    { bot: 'lead', title: 'Run finishes', sub: 'Report ready' }, { bot: 'bench', title: 'Assigned', sub: 'To an expert with the right skills' }, { icon: 'bell', title: 'Notified', sub: 'Gets the review task' },
    { icon: 'dev', title: 'Reviews', sub: 'Fine-tunes and signs off' }, { icon: 'trophy', title: 'Credited', sub: 'Name on the pitch', tone: 'good' },
  ], 1.95, 1.8);
  checks(s, ['Time between projects turns into **useful, visible work**', 'Developers **learn new stacks** from real client sites', 'The client meets the **named expert** who reviewed their site', 'More engaged people, and a team ready to start on day one'], X0, 4.1, CW, 2.6, 18);

};
S.cto = () => {
  const s = slide('CONTENT', 'Reaching CTOs', 'Reach CTOs quickly, even during a live meeting', 'During a CTO meeting we paste their URL and, about three minutes later, show the score, tech stack and redesign on screen. By minute ten we discuss their real issues with a named team and price range. The next day they get a deck reviewed by an expert.');
  const T = [['0:00', 'Meeting starts', 'The CTO mentions their website or app.'], ['0:30', 'Paste the URL', 'Nitro starts while we keep talking.'], ['3:00', 'Show results', 'Score, tech stack and redesign on screen.'], ['10:00', 'Talk specifics', 'Their real issues, our named team, a price range.'], ['Next day', 'Follow up', 'Deck and proposal, reviewed by an expert.']];
  const w = CW / 5;
  s.addShape(pres.shapes.LINE, { x: X0 + 0.1, y: 2.25, w: CW - 0.2, h: 0, line: { color: K.acc, width: 3 } });
  T.forEach(([t, h, p], i) => { const x = X0 + i * w; s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 2.05, w: 1.25, h: 0.42, rectRadius: 0.21, fill: { color: K.panel }, line: { color: K.acc, width: 2 } }); text(s, t, x, 2.05, 1.25, 0.42, { fontSize: 14, bold: true, align: 'center', valign: 'middle' }); text(s, h, x, 2.7, w - 0.2, 0.4, { fontSize: 17, bold: true }); text(s, p, x, 3.1, w - 0.25, 0.8, { fontSize: 13, color: K.muted }); });
  checks(s, ['Personal outreach to **many CTOs a week**, each about their own site', 'Proof in the room, not promises a week later', 'Saved runs **replay for free**, so a demo never depends on the network'], X0, 4.35, CW, 2.2, 18);

};
S.always = () => {
  const s = slide('CONTENT', 'Always on', 'Agents that work in the background, 24x7', 'Planned Night Watch agent: keeps a watchlist of target accounts, re-checks every site overnight, alerts sales when a site slows down, breaks or relaunches, and sends a morning digest with the best leads and a drafted pitch.');
  s.addShape(pres.shapes.OVAL, { x: X0 + 0.3, y: 2.2, w: 3.0, h: 3.0, fill: { color: K.hl }, line: { color: K.acc, width: 3 } });
  s.addImage({ path: ICON('moon'), x: X0 + 1.05, y: 2.95, w: 1.5, h: 1.5 });
  text(s, '24x7', X0 + 0.3, 5.35, 3.0, 0.5, { fontSize: 22, bold: true, color: K.acc, align: 'center' });
  checks(s, ['Keep a **watchlist** of target accounts', 'Re-check every site **overnight**, automatically', 'Alert sales when a prospect\'s site **slows down, breaks or relaunches**', 'A **morning digest**: the best leads, with the pitch already drafted', 'Every run is saved and can be reviewed or replayed later'], 4.5, 2.1, 8.2, 3.6, 18);
  banner(s, 'The team sleeps. The pipeline keeps growing. (Night Watch agent, next in the marketplace.)', 6.15, 'info');

};
S.effort = () => {
  const s = slide('CONTENT', 'Effort saved', 'Many more analyses, with far less effort', 'Manual research of a prospect\'s site, stack and pitch takes days of senior time. A Nitro run takes about 1.5 to 3 minutes in our tests, and the app runs up to 3 at the same time, so experts spend their time reviewing instead of researching. We will measure the real time saved.');
  const w = (CW - 0.3) / 2;
  box(s, X0, 1.95, w, 3.0); text(s, 'Today: by hand', X0 + 0.3, 2.1, w - 0.6, 0.5, { fontSize: 19, bold: true, color: K.bad });
  checks(s, ['Open the site and check it manually', 'Guess the tech stack', 'Find who is free', 'Write the proposal from scratch', 'Takes **days** of senior time'], X0 + 0.3, 2.7, w - 0.6, 2.2, 16, 'cross');
  box(s, X0 + w + 0.3, 1.95, w, 3.0); text(s, 'With Nitro', X0 + w + 0.6, 2.1, w - 0.6, 0.5, { fontSize: 19, bold: true, color: K.good });
  checks(s, ['Agents measure the site with real tools', 'Tech stack read from network traffic', 'Available experts matched automatically', 'Deck and proposal drafted', 'A run takes **minutes**; an expert reviews it'], X0 + w + 0.6, 2.7, w - 0.6, 2.2, 16);
  stats(s, [['1.5–3 min', 'per run in our tests'], ['3', 'runs at the same time in the app'], ['24x7', 'agents can keep running', K.good]], 5.2, 1.3);

};
S.market = () => {
  const s = slide('CONTENT', 'Agent marketplace · built in the app', 'A marketplace of agents to showcase across the org', `The marketplace lists ${MARKET.length} agents: ${MARKET.filter((a) => a.status === 'live').length} live, ${MARKET.filter((a) => a.status === 'beta').length} beta and ${MARKET.filter((a) => a.status === 'planned').length} planned, with what each takes in, produces and how to showcase it. It is built in the code: config/marketplace.json, the /api/marketplace endpoint and the /marketplace.html page, with tests.`);
  const cols = 6, gap = 0.12, w = (CW - gap * (cols - 1)) / cols, h = 0.5;
  MARKET.forEach((a, i) => {
    const x = X0 + (i % cols) * (w + gap), y = 1.9 + Math.floor(i / cols) * (h + gap);
    box(s, x, y, w, h, { line: a.status === 'live' ? K.good : a.status === 'beta' ? K.warn : K.line, dash: a.status === 'planned' ? 'dash' : undefined, flat: true, lineW: 1.25 });
    if (a.status === 'live') s.addImage({ path: BOT(a.id), x: x + 0.1, y: y + 0.06, w: 0.28, h: 0.38 });
    else { const k = { judge: 'scale', tenders: 'gov', journey: 'walk', testgen: 'test', locale: 'globe2', backend: 'db', devops: 'cloud', htmlfix: 'tools', rag: 'chat', meeting: 'mic', outreach: 'mail', watch: 'moon', reviewer: 'raise' }[a.id]; if (k) s.addImage({ path: ICON(k), x: x + 0.08, y: y + 0.08, w: 0.34, h: 0.34 }); }
    text(s, a.name, x + 0.47, y, w - 0.52, h, { fontSize: 11, bold: true, valign: 'middle' });
  });
  const y0 = 1.9 + Math.ceil(MARKET.length / cols) * (h + gap) + 0.15;
  checks(s, ['One catalogue of **every agent**: what it takes in, produces, how to showcase it', 'Teams **reuse agents** instead of rebuilding: **Connect** links any agent over MCP', 'Sales shows clients the agents by category: audit, test, build, people, sell, always on'], X0, y0, 7.3, 6.85 - y0, 15);
  box(s, 8.2, y0, 4.53, 6.75 - y0);
  text(s, 'In the code', 8.45, y0 + 0.15, 4, 0.4, { fontSize: 17, bold: true });
  text(s, 'config/marketplace.json → /api/marketplace → /marketplace.html, with search and filters. Tests check every running agent is listed as live.', 8.45, y0 + 0.6, 4.05, 6.6 - y0 - 0.6, { fontSize: 13, color: '44506B' });

};
S.hood = () => {
  const s = slide('CONTENT', 'Under the hood', 'Small, honest, and no build step', 'TypeScript on Node.js 20; Playwright, Lighthouse 12, axe-core and the Chrome DevTools Protocol to measure; Claude through the Anthropic Messages API with streaming and vision; pptxgenjs for the deck; vanilla HTML, CSS and JavaScript for the interface; Node test runner, a guardrailed planner and offline fallbacks.');
  const C = [['Runtime', 'TypeScript · Node.js 20 · tsx · Server-Sent Events'], ['Measuring the web', 'Playwright · Lighthouse 12 · axe-core · Chrome DevTools Protocol'], ['The model', 'Claude Sonnet 5.5 · Anthropic Messages API · streaming · vision'], ['Output', 'pptxgenjs (PPTX) · Markdown proposal · files in runs/'], ['Interface', 'Vanilla HTML/CSS/JS · canvas pixel art · light and dark themes'], ['Quality', 'Node test runner · guardrailed planner · offline fallbacks']];
  grid(s, C.map(([t, b]) => ({ title: t, body: b })), 3, 1.9, 1.45);
  const N = [['13', 'agents'], [String(MARKET.length), 'in marketplace'], ['12', 'skills'], ['132', 'tech signatures'], ['43', 'logged decisions'], ['49', 'tests']];
  const w = (CW - 0.2 * 5) / 6;
  N.forEach(([v, l], i) => { const x = X0 + i * (w + 0.2); box(s, x, 5.25, w, 1.25); text(s, v, x, 5.35, w, 0.65, { fontSize: 30, bold: true, align: 'center', valign: 'middle' }); text(s, l, x, 6.0, w, 0.4, { fontSize: 12, color: K.muted, align: 'center' }); });

};
S.trust = () => {
  const s = slide('CONTENT', 'Why you can trust it', 'Models judge. Tools measure. Humans decide.', 'Real numbers come from tools; the model only judges design and clarity. Code guardrails control the planner. Offline mode and free replay mean it always works. Everything is documented: 43 decisions, 49 tests and tagged releases. Sample data is labelled as sample data.');
  grid(s, [
    { icon: 'check', title: 'Real numbers', body: 'Speed, accessibility, traffic and technologies are measured by tools. Models only judge design and clarity. Findings carry evidence.' },
    { icon: 'tools', title: 'Guardrails', body: 'The planning model chooses the next step, but code enforces order, retry limits and a step budget. A bad answer falls back to rules.' },
    { icon: 'bolt', title: 'Always works', body: 'No model key or network? Offline mode still runs end to end. Any past run replays for free.' },
    { icon: 'doc', title: 'Fully documented', body: '43 logged decisions, 49 tests, and tagged releases to fall back to: v0.1.0, v0.2.0, v0.2.1.' },
  ], 4, 1.95, 2.45, 0.22);
  banner(s, 'Talent roster, org skills and pricing constants are labelled sample data until real data is connected.', 4.75, 'info');

};
S.business = () => {
  const s = slide('CONTENT', 'The business case', 'From very few proposals to a pipeline', 'Nitro lets us reach many more prospects with personalised proof, puts developers between projects to work, and shortens the path to a staffed project. We will measure the real impact: proposals sent, replies, conversions, revenue and talent utilisation.');
  grid(s, [
    { icon: 'growth', title: 'More reach', body: 'Many more prospects analysed and contacted, each with a pitch about their own site.' },
    { icon: 'target', title: 'Better pitches', body: 'Real findings, a redesign and a named team instead of a generic proposal.' },
    { icon: 'dev', title: 'Talent put to work', body: 'Developers between projects review, fine-tune and get matched to new work.' },
  ], 3, 1.95, 1.9);
  box(s, X0, 4.15, CW, 2.35);
  text(s, 'What we will measure', X0 + 0.3, 4.3, CW - 0.6, 0.45, { fontSize: 19, bold: true });
  chips(s, ['Proposals sent per week', 'Replies from CTOs', 'Conversions', 'Revenue from new clients', 'Talent utilisation', 'Time from first contact to project start'], X0 + 0.3, 4.95, CW - 0.6, 14);
  note(s, 'We do not claim numbers we have not measured yet. The app\'s ROI panel takes real figures once they are available.', 6.6, 0.35);

};
S.who = () => {
  const s = slide('CONTENT', 'Who wins', 'Good for everyone involved', 'Sales get more, faster, personal pitches. Developers between projects get real work and credit. Delivery heads get projects scoped from data. Leadership gets lower unallocated cost and a measurable pipeline. The client CTO gets free, useful insight. The organisation shows its AI and engineering skill in every pitch.');
  grid(s, [
    { icon: 'growth', title: 'Sales and pre-sales', body: 'More pitches, faster, each one personal. Better meetings with CTOs.' },
    { icon: 'dev', title: 'Developers between projects', body: 'Real work, new skills and their name on the pitch.' },
    { icon: 'build', title: 'Delivery heads', body: 'Projects scoped from real data, with a team that is free now.' },
    { icon: 'brief', title: 'Leadership and finance', body: 'Lower unallocated cost, higher win rate, a measurable pipeline.' },
    { icon: 'target', title: 'The client\'s CTO', body: 'Free, useful insight on their own site, before signing anything.' },
    { icon: 'office', title: 'The organisation', body: 'Shows our AI and engineering skill in every single pitch.' },
  ], 3, 1.95, 2.0);

};
S.next = () => {
  const s = slide('CONTENT', 'What\'s next', 'Built in a hackathon. Ready to grow.', 'Now: the full URL-to-pitch pipeline, planner-driven lead agent, live feed, office and replay, review window and agent marketplace. Next: journeys and tests, locale testing, LLM scores and HTML fixes, back-end and DevOps inspectors, real talent data, review assignment. Later: 24x7 agents, RAG chat generator, live-meeting assistant, CRM and multi-page redesign.');
  const R = [['Now · v0.2.1', K.good, ['URL to audit, stack, redesign, team, deck', 'Planner-driven lead agent', 'Live feed, office and free replay', 'Review window', 'Agent marketplace']], ['Next', K.acc, ['Agent-driven journeys and automated tests', 'Locale testing', 'LLM scores and HTML fixes for every finding', 'Back-end and DevOps inspectors', 'Real talent and skills data (HR adapter)', 'Review assignment and notifications']], ['Later', K.muted, ['24x7 background agents and watchlists', 'Simple RAG chat generator', 'Live-meeting assistant', 'CRM, approved send and win/loss loop', 'Multi-page redesign']]];
  const w = (CW - 0.5) / 3;
  R.forEach(([t, c, items], i) => { const x = X0 + i * (w + 0.25); box(s, x, 1.95, w, 4.6); s.addShape(pres.shapes.OVAL, { x: x + 0.3, y: 2.2, w: 0.3, h: 0.3, fill: { color: c }, line: { color: c } }); text(s, t, x + 0.75, 2.12, w - 1, 0.45, { fontSize: 19, bold: true, color: c, valign: 'middle' }); text(s, items.map((it, j) => ({ text: it, options: { bullet: true, breakLine: j < items.length - 1, paraSpaceAfter: 6 } })), x + 0.3, 2.75, w - 0.55, 3.6, { fontSize: 15 }); });

};
S.recap = () => {
  const s = slide('CONTENT', 'Nitro in one slide', 'The whole idea, in short', 'Problem, solution, how, proof, impact and next steps on one page, followed by the key ideas as tags.');
  const R = [['Problem', 'Pre-sales is slow, expensive and generic, while skilled developers wait between projects.'], ['Solution', 'Paste a URL. AI agents audit the site, read the tech stack, redesign the homepage, match our available experts and write the pitch.'], ['How', 'A coordinator agent plans the work. Tools measure (Lighthouse, axe-core, Playwright). The model judges and designs. A human approves.'], ['Proof', 'Real runs on allbirds.com, stripe.com and Samsung India. Live feed, office view, free replay, review window.'], ['Impact', 'Many more prospects analysed, personalised outreach to CTOs, better use of our talent, engaged employees.'], ['Next', 'Agent journeys, automated tests, locale testing, HTML fixes, RAG chat, 24x7 agents, all in the agent marketplace.']];
  R.forEach(([k, v], i) => { const y = 1.85 + i * 0.6; text(s, k, X0, y, 1.6, 0.55, { fontSize: 16, bold: true, color: K.acc }); text(s, v, X0 + 1.7, y, CW - 1.7, 0.55, { fontSize: 15 }); });
  chips(s, ['Pre-sales automation', 'Multi-agent AI', 'Talent utilisation', 'Personalised pitches', 'Front end · back end · DevOps', 'Performance', 'LLM scores', 'Automated tests', 'Agent journeys', 'Locales', 'HTML improvements', 'RAG chat', '24x7 agents', 'Agent marketplace', 'Human in the loop'], X0, 5.6, CW, 12);

};
S.close = () => {
  const s = slide('DARK', 'Nitro', 'Great developers, in front of every client.', 'Close: every prospect sees their better website before they sign. Run npm start and open localhost:3000 to watch it work live.');
  s.addText([{ text: 'Every prospect sees their better website before they sign.', options: { bold: true, color: 'A9B8FF', breakLine: true } }, { text: 'Watch it work, live: npm start → localhost:3000', options: { fontSize: 16 } }], { placeholder: 'body' });
  botRow(s, 5.65, 0.62);

};

// ── main track (what is presented live) ──
S.bang = () => {
  const s = slide('CONTENT', 'The problem', 'Pre-sales today', 'The six pain points of pre-sales today: proposals are slow, expensive to create and generic; we cannot target the right customers; demos take too long; and skilled developers wait between projects. So conversion stays low. In the live deck each point appears on a click.');
  const P = [['Slow to propose', 'Days of research before a single proposal goes out.'], ['Expensive to create', 'Senior architects spend days on each pitch.'], ['Generic content', 'The same slides for every client.'], ['Can\'t target customers', 'We don\'t know who to approach, or with what.'], ['Demos take too long', 'Built only when a deal is almost won.'], ['Talent waiting', 'Skilled developers sit between projects.']];
  const gap = 0.25, w = (CW - 2 * gap) / 3, h = 1.75;
  P.forEach(([t, b], i) => {
    const x = X0 + (i % 3) * (w + gap), y = 1.95 + Math.floor(i / 3) * (h + gap);
    box(s, x, y, w, h);
    text(s, String(i + 1).padStart(2, '0'), x + 0.3, y + 0.22, 1, 0.3, { fontSize: 11, bold: true, color: K.acc, charSpacing: 2 });
    text(s, t, x + 0.3, y + 0.5, w - 0.6, 0.5, { fontSize: 21, bold: true });
    text(s, b, x + 0.3, y + 1.0, w - 0.6, 0.6, { fontSize: 13, color: K.muted });
  });
  text(s, 'So conversion stays low.', X0, 6.0, CW, 0.6, { fontSize: 24, bold: true, align: 'center', valign: 'middle' });
};
S.target = () => {
  const s = slide('CONTENT', 'Why conversion is low', 'Don\'t wait for RFPs. Reach the CTO first, at scale.', 'Waiting for RFPs gives us a few chances a month, and an RFP arrives late: the shortlist is set and every vendor answers the same questions. Nitro prepares a personalised analysis in about 2.5 minutes, three at a time, so 72 an hour; at about 18 cents of model tokens each, 100 prospects cost about 18 dollars. These are measured on our saved runs (103 to 150 seconds, 11 to 18 cents). So we analyse hundreds, pick the best fits (clear problems on their platform and skills we have), and go to the CTO first, already knowing their stack, their news and their gaps.');
  // chart: pitches we can prepare
  box(s, X0, 1.85, 7.0, 2.7);
  text(s, 'PERSONALISED PITCHES WE CAN PREPARE', X0 + 0.3, 2.0, 6.5, 0.3, { fontSize: 11, bold: true, color: K.muted, charSpacing: 2 });
  [['Waiting for RFPs', 0.04, K.bad, 'a few a month'], ['With Nitro', 1, K.good, 'hundreds a month']].forEach(([l, f, c, v], i) => {
    const y = 2.45 + i * 0.85;
    text(s, l, X0 + 0.3, y, 1.9, 0.42, { fontSize: 14, bold: true, valign: 'middle' });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: X0 + 2.25, y: y + 0.02, w: Math.max(4.4 * f, 0.12), h: 0.38, rectRadius: 0.08, fill: { color: c }, line: { color: c } });
    text(s, v, X0 + 2.25, y + 0.42, 4.4, 0.3, { fontSize: 13, bold: true, color: c });
  });
  text(s, 'An RFP arrives late: the shortlist is set and every vendor answers it.', X0 + 0.3, 4.1, 6.5, 0.35, { fontSize: 12, color: K.muted });
  // the maths
  const eq = (y, parts) => {
    box(s, 7.85, y, 4.88, 1.08);
    const w = 4.88 / 5;
    parts.forEach(([v, l], k) => {
      const x = 7.85 + k * w;
      if (l === null) { text(s, v, x, y, w, 1.08, { fontSize: 22, color: K.muted, align: 'center', valign: 'middle' }); return; }
      text(s, v, x, y + 0.14, w, 0.55, { fontSize: 22, bold: true, align: 'center', valign: 'middle', color: k === 4 ? K.acc : K.fg });
      text(s, l, x, y + 0.66, w, 0.3, { fontSize: 10, color: K.muted, align: 'center' });
    });
  };
  eq(1.85, [['2.5 min', 'per analysis'], ['×', null], ['3', 'in parallel'], ['=', null], ['72', 'an hour']]);
  eq(3.05, [['$0.18', 'per analysis'], ['×', null], ['100', 'prospects'], ['=', null], ['≈ $18', 'model cost']]);
  text(s, 'Measured on our saved runs: 103 to 150 s and $0.11 to $0.18 each.', 7.85, 4.2, 4.88, 0.3, { fontSize: 10.5, italic: true, color: K.muted });
  // the play
  const F = [['globe', 'Analyse hundreds', 'Every target account, 24x7'], ['target', 'Pick the best fits', 'Clear problems + skills we have'], ['handshake', 'Talk to the CTO first', 'Already knowing their stack, news and gaps']];
  const fw = (CW - 2 * 0.5) / 3;
  F.forEach(([ic, t, b], k) => {
    const x = X0 + k * (fw + 0.5), y = 4.95;
    box(s, x, y, fw, 1.2, { line: k === 2 ? K.acc : undefined, lineW: k === 2 ? 2 : 1 });
    s.addImage({ path: ICON(ic), x: x + 0.25, y: y + 0.3, w: 0.6, h: 0.6 });
    text(s, t, x + 1.05, y + 0.2, fw - 1.2, 0.42, { fontSize: 16, bold: true, valign: 'middle' });
    text(s, b, x + 1.05, y + 0.62, fw - 1.2, 0.45, { fontSize: 12, color: K.muted });
    if (k < 2) arrow(s, x + fw + 0.06, y + 0.6, 0.38);
  });
};
S.how = () => {
  const s = slide('CONTENT', 'How it works', 'One URL in. A personalised pitch out.', 'Paste a URL, or take a government tender the Tender Scout found; the Coordinator plans; the Market Researcher reads the latest news on the company; seven checks run in parallel; the Designer and Team Matcher build; the Deck Writer writes; a human approves. The checks find speed, mobile, accessibility, UX, AI-search visibility, the tech stack from front end to DevOps, third-party weight and the brand kit. A run takes about 1.5 to 3 minutes.');
  flow(s, [
    { icon: 'gov', title: 'URL or tender', sub: 'Site or govt tender' }, { bot: 'lead', title: 'Plan', sub: 'Coordinator agent' }, { bot: 'research', title: 'Research', sub: 'Latest news on the company' },
    { bots: ['audit', 'tech', 'speed'], title: 'Audit', sub: '7 checks in parallel' }, { bots: ['redesign', 'bench'], title: 'Build', sub: 'Redesign + team' },
    { bot: 'deck', title: 'Write', sub: 'Deck + proposal' }, { icon: 'person', title: 'Review', sub: 'Human approves', tone: 'good' },
  ], 1.85, 1.55);
  checks(s, ['Tools measure: Lighthouse, axe-core, Playwright, Chrome DevTools Protocol', 'The model (Claude) researches, plans, judges design and clarity, and designs', 'Code guardrails keep the order, retries and step budget safe', 'A human reviews everything before it is sent'], X0, 3.8, CW, 2.3, 17);
  note(s, 'A full run takes about 1.5 to 3 minutes. Every step streams live, and every run can be replayed.', 6.3, 0.35);
};
S.finds = () => {
  const s = slide('CONTENT', 'A sample of the checks · real Allbirds run', 'Evidence from outside, before we ever meet.', 'Speed 40/100 (16.9 s until the main content appears, 6.3 MB page). Mobile 87/100 (12 of 84 tap targets too small). Accessibility 70/100 (3 rules failed, 2 critical). UX 60/100 (weakest: call-to-action clarity). AI search 62/100 (no structured data, llms.txt present). 9 technologies detected; they open talks on logistics, data, finance and cloud. Customer data goes to 5 tools (GA4, Clarity, Tag Manager, Meta Pixel, Google Ads). Brand kit: #000000 and #ece9e2, Geograph typeface, Shop All call to action.');
  const P = [
    ['Backend & stack', '9 found', K.acc, 'Opens talks on logistics,\ndata, finance and cloud'],
    ['Customer data flows', '5 tools', K.warn, 'GA4, Clarity, Tag Manager,\nMeta Pixel, Google Ads'],
    ['Speed', '40 / 100', K.bad, '16.9 s until main content\n6.3 MB page weight'],
    ['Mobile', '87 / 100', K.good, '12 of 84 tap targets\ntoo small'],
    ['Accessibility', '70 / 100', K.warn, '3 rules failed,\n2 of them critical'],
    ['UX and design', '60 / 100', K.bad, 'Weakest area:\ncall-to-action clarity'],
    ['AI-search visibility', '62 / 100', K.bad, 'No structured data\nllms.txt present'],
    ['Brand kit', 'Geograph', K.fg, '#000000 · #ece9e2\nCTA: Shop All'],
  ];
  const gx = X0, gw = 9.0, gap = 0.18, w = (gw - gap * 3) / 4, h = 2.25;
  P.forEach(([t, v, c, d], i) => {
    const x = gx + (i % 4) * (w + gap), y = 1.85 + Math.floor(i / 4) * (h + gap);
    box(s, x, y, w, h);
    text(s, String(i + 1).padStart(2, '0'), x + 0.18, y + 0.15, 0.6, 0.3, { fontSize: 10, bold: true, color: K.acc, charSpacing: 2 });
    text(s, t, x + 0.18, y + 0.42, w - 0.3, 0.4, { fontSize: 14, bold: true });
    text(s, v, x + 0.18, y + 0.85, w - 0.3, 0.6, { fontSize: 26, bold: true, color: c, valign: 'middle' });
    text(s, d, x + 0.18, y + 1.5, w - 0.3, 0.7, { fontSize: 11, color: K.muted });
  });
  const ix = gx + gw + 0.3, iw = W - X0 - ix;
  s.addImage({ path: A('pptx/allbirds-desktop.jpg'), x: ix, y: 1.85, w: iw, h: iw * 10 / 16, altText: 'Allbirds homepage, desktop screenshot from the run' });
  const ph = 4.68 - iw * 10 / 16 - 0.15, pw = ph * 375 / 700;
  s.addImage({ path: A('pptx/allbirds-mobile.jpg'), x: ix + (iw - pw) / 2, y: 1.85 + iw * 10 / 16 + 0.15, w: pw, h: ph, altText: 'Allbirds homepage on a phone, screenshot from the run' });
  note(s, 'Screenshots and numbers are from a saved run on allbirds.com.', 6.65, 0.3);
};
S.depth = () => {
  const s = slide('CONTENT', 'Beyond the website', 'The website is the way in. The backend is the business.', 'The website is only the entry point. From outside, the agents already read the server and language, APIs and third parties, CDN and hosting, commerce platform, CMS, payments, analytics, monitoring, security and consent, performance, accessibility and AI search: 132 technologies in 17 categories. That earns the room with the CTO, where the conversation moves to cloud infrastructure, data pipelines, logistics systems, ERP and CRM integration, DevOps and SRE, AI and data platforms, cybersecurity and modernisation.');
  // entry point
  box(s, X0, 3.0, 1.7, 2.0, { line: K.acc, lineW: 2 });
  s.addImage({ path: ICON('globe'), x: X0 + 0.5, y: 3.2, w: 0.7, h: 0.7 });
  text(s, 'Website', X0, 4.0, 1.7, 0.4, { fontSize: 16, bold: true, align: 'center' });
  text(s, 'the entry point', X0, 4.4, 1.7, 0.3, { fontSize: 11, color: K.muted, align: 'center' });
  arrow(s, X0 + 1.8, 4.0, 0.45);
  // what the agents read
  const mx = 3.0;
  text(s, 'WHAT THE AGENTS READ FROM OUTSIDE', mx, 1.95, 5.2, 0.3, { fontSize: 11, bold: true, color: K.muted, charSpacing: 2 });
  const R = [['dev', 'Server & language'], ['plug', 'APIs & third parties'], ['cloud', 'CDN & hosting'], ['cart', 'Commerce platform'], ['brick', 'CMS'], ['card', 'Payments'], ['chart', 'Analytics & tags'], ['desktop', 'Monitoring'], ['shield', 'Security & consent'], ['bolt', 'Performance'], ['a11y', 'Accessibility'], ['search', 'AI search']];
  const cw = 1.68, ch = 0.5;
  R.forEach(([ic, t], k) => {
    const x = mx + (k % 3) * (cw + 0.08), y = 2.35 + Math.floor(k / 3) * (ch + 0.1);
    box(s, x, y, cw, ch, { flat: true });
    s.addImage({ path: ICON(ic), x: x + 0.08, y: y + 0.1, w: 0.3, h: 0.3 });
    text(s, t, x + 0.45, y, cw - 0.5, ch, { fontSize: 10.5, bold: true, valign: 'middle' });
  });
  text(s, [{ text: '132', options: { bold: true, color: K.fg } }, { text: ' technologies · ', options: {} }, { text: '17', options: { bold: true, color: K.fg } }, { text: ' categories · from traffic, headers and code', options: {} }], mx, 4.85, 5.2, 0.3, { fontSize: 11, color: K.muted });
  arrow(s, 8.35, 4.0, 0.45);
  // where the CTO conversation goes
  const ox = 9.0;
  text(s, 'WHERE THE CTO CONVERSATION GOES', ox, 1.95, 3.8, 0.3, { fontSize: 11, bold: true, color: K.muted, charSpacing: 2 });
  const O = [['cloud', 'Cloud infrastructure'], ['pipe', 'Data pipelines'], ['truck', 'Logistics systems'], ['link', 'ERP & CRM integration'], ['tools', 'DevOps & SRE'], ['robot', 'AI & data platforms'], ['lock', 'Cybersecurity'], ['build', 'Modernisation']];
  O.forEach(([ic, t], k) => {
    const y = 2.35 + k * 0.55;
    s.addShape(pres.shapes.RECTANGLE, { x: ox, y, w: 3.73, h: 0.47, fill: { color: K.hl }, line: { color: K.hl } });
    s.addShape(pres.shapes.RECTANGLE, { x: ox, y, w: 0.06, h: 0.47, fill: { color: K.acc }, line: { color: K.acc } });
    s.addImage({ path: ICON(ic), x: ox + 0.16, y: y + 0.07, w: 0.33, h: 0.33 });
    text(s, t, ox + 0.6, y, 3.05, 0.47, { fontSize: 15, bold: true, valign: 'middle' });
  });
};
S.mapping = () => {
  const s = slide('CONTENT', 'From their stack to our people · real Allbirds run', 'Every technology becomes a skill, a person and a plan', 'On the Allbirds run, Vue.js maps to Vue/Nuxt skills (partial coverage), Shopify to commerce (a gap), GA4 and Tag Manager to web analytics (strong), Cloudflare and Azure to DevOps and cloud (strong). The matcher then names available experts and start dates. Integrating with our project management system (PMS) brings live availability, skills and rates in, and gives billing visibility in advance and upcoming projects. Today the roster is sample data behind an adapter.');
  const cols = [['FOUND ON THEIR SITE', [['Vue.js', 'front end'], ['Shopify', 'commerce'], ['GA4 + Tag Manager', 'analytics'], ['Cloudflare + Azure', 'CDN, cloud']], null],
    ['SKILL WE NEED · OUR COVERAGE', [['Vue / Nuxt', 'partial'], ['Shopify / commerce', 'gap'], ['Web analytics', 'strong'], ['DevOps / CDN / cloud', 'strong']], [K.warn, K.bad, K.good, K.good]],
    ['WHO IS FREE · FROM PMS', [['Available experts', 'named'], ['Start dates', 'from roster'], ['Organisation match', 'score'], ['Billing forecast', 'next']], [null, null, null, K.acc]]];
  const w = 3.6, gap = (CW - 3 * w) / 2;
  cols.forEach(([h, rows, tones], c) => {
    const x = X0 + c * (w + gap);
    text(s, h, x, 1.85, w, 0.35, { fontSize: 11, bold: true, color: K.muted, charSpacing: 2 });
    rows.forEach(([a, b], i) => { const y = 2.25 + i * 0.6; box(s, x, y, w, 0.5, { line: tones?.[i] ?? K.line, lineW: tones?.[i] ? 1.75 : 1, dash: c === 2 && i === 3 ? 'dash' : undefined, flat: true }); text(s, a, x + 0.15, y, w - 1.4, 0.5, { fontSize: 14, bold: true, valign: 'middle' }); text(s, b, x + w - 1.3, y, 1.15, 0.5, { fontSize: 11, color: K.muted, align: 'right', valign: 'middle' }); });
    if (c < 2) arrow(s, x + w + 0.08, 3.3, gap - 0.16);
  });
  box(s, X0, 4.85, CW, 1.25);
  s.addImage({ path: ICON('plug'), x: X0 + 0.3, y: 5.15, w: 0.6, h: 0.6 });
  text(s, 'Integrating with our project management system (PMS)', X0 + 1.15, 4.97, CW - 1.4, 0.4, { fontSize: 17, bold: true });
  text(s, 'Live availability, skills and rates in; billing visible in advance, upcoming projects and staffing plans out. Today the roster is sample data behind an adapter, ready for PMS.', X0 + 1.15, 5.38, CW - 1.4, 0.65, { fontSize: 13, color: '44506B' });
};
S.report = () => {
  const s = slide('CONTENT', 'What it generates', 'A report and a pitch, ready for review', 'Each run produces an audit (64/100, grade D on Allbirds, with evidence and ranked fixes), a redesigned homepage (accessibility 70 to 98, mobile 87 to 100), an estimate (named team, person-days, hours per skill, timeline and a price range computed from the findings and the rate card), a personalised PowerPoint deck and a written proposal. A human approves before anything is sent.');
  const w = (CW - 0.5) / 3, y = 1.9, h = 3.05;
  box(s, X0, y, w, h); text(s, 'AUDIT', X0 + 0.25, y + 0.15, w, 0.35, { fontSize: 12, bold: true, color: K.muted, charSpacing: 2 });
  ring(s, X0 + 0.15, y + 0.5, 2.0, 64, K.bad, 'grade D');
  text(s, 'Speed, mobile, accessibility, UX and AI search, each with evidence and ranked fixes.', X0 + 2.2, y + 0.75, w - 2.4, 1.6, { fontSize: 13, color: '44506B' });
  const x2 = X0 + w + 0.25; box(s, x2, y, w, h); text(s, 'REDESIGN', x2 + 0.25, y + 0.15, w, 0.35, { fontSize: 12, bold: true, color: K.muted, charSpacing: 2 });
  const iw = (w - 0.6) / 2;
  s.addImage({ path: A('allbirds-before.jpg'), x: x2 + 0.2, y: y + 0.6, w: iw, h: iw * 10 / 16, altText: 'Allbirds homepage before' });
  s.addImage({ path: A('allbirds-after.jpg'), x: x2 + 0.4 + iw, y: y + 0.6, w: iw, h: iw * 10 / 16, altText: 'Allbirds homepage after the redesign' });
  text(s, 'Accessibility 70 → 98\nMobile 87 → 100', x2 + 0.25, y + 0.75 + iw * 10 / 16, w - 0.5, 0.8, { fontSize: 15, bold: true, color: K.good });
  const x3 = x2 + w + 0.25; box(s, x3, y, w, h); text(s, 'ESTIMATE', x3 + 0.25, y + 0.15, w, 0.35, { fontSize: 12, bold: true, color: K.muted, charSpacing: 2 });
  [['Team', 'named experts'], ['Effort', 'person-days'], ['Hours', 'per skill'], ['Timeline', 'weeks'], ['Cost', 'price range']].forEach(([a, b], i) => { const yy = y + 0.6 + i * 0.4; text(s, a, x3 + 0.25, yy, 1.5, 0.35, { fontSize: 14 }); text(s, b, x3 + 1.6, yy, w - 1.85, 0.35, { fontSize: 14, bold: true, color: K.acc, align: 'right' }); });
  text(s, 'Computed from the findings and the rate card.', x3 + 0.25, y + 2.65, w - 0.5, 0.3, { fontSize: 10, color: K.muted, italic: true });
  grid(s, [{ icon: 'chart', title: 'Pitch deck', body: 'PowerPoint, personalised to their site.', size: 13 }, { icon: 'memo', title: 'Proposal', body: 'Written, with scope and team.', size: 13 }, { icon: 'person', title: 'Human review', body: 'Nothing is sent without approval.', size: 13 }], 3, 5.2, 1.3);
};
S.cost = () => {
  const s = slide('CONTENT', 'What one analysis costs', 'Only the AI model costs money. Everything else is free.', 'The only paid part of a run is model tokens: Claude Sonnet 5.5 costs 2 dollars per million input tokens and 10 dollars per million output tokens. Four agents call the model (the Coordinator\'s planner, the UX Reviewer, the AI-Search Checker and the Designer); the other seven use free, open-source tools. The dashboard now shows the tokens and cost of every agent and the total for each run. Replaying a saved run costs nothing.');
  const w = (CW - 0.3) / 2;
  box(s, X0, 1.9, w, 3.0); s.addImage({ path: ICON('card'), x: X0 + 0.25, y: 2.05, w: 0.42, h: 0.42 }); text(s, 'Paid: model tokens', X0 + 0.8, 2.03, w - 1, 0.45, { fontSize: 18, bold: true, valign: 'middle' });
  text(s, [{ text: '$2', options: { fontSize: 40, bold: true } }, { text: '  per 1M input tokens', options: { fontSize: 14, color: K.muted } }], X0 + 0.3, 2.6, w - 0.5, 0.75, { valign: 'middle' });
  text(s, [{ text: '$10', options: { fontSize: 40, bold: true } }, { text: '  per 1M output tokens', options: { fontSize: 14, color: K.muted } }], X0 + 0.3, 3.35, w - 0.5, 0.75, { valign: 'middle' });
  text(s, 'Claude Sonnet 5.5. The dashboard now shows the tokens and cost of every agent, and the total for each run.', X0 + 0.3, 4.15, w - 0.6, 0.65, { fontSize: 12, color: '44506B' });
  const x2 = X0 + w + 0.3; box(s, x2, 1.9, w, 3.0); s.addImage({ path: ICON('free'), x: x2 + 0.25, y: 2.05, w: 0.42, h: 0.42 }); text(s, 'Free: everything else', x2 + 0.8, 2.03, w - 1, 0.45, { fontSize: 18, bold: true, valign: 'middle' });
  checks(s, ['Lighthouse, Playwright and axe-core are open source', 'Tech detection reads network traffic locally', 'Replay of any past run costs nothing', 'Offline mode runs with no model at all'], x2 + 0.3, 2.7, w - 0.6, 2.1, 15);
  stats(s, [['1.5–3 min', 'per run in our tests'], ['4', 'agents call the model; 7 use only tools'], ['$0', 'to replay a saved run', K.good]], 5.15, 1.3);
};
S.impact = () => {
  const s = slide('CONTENT', 'What this leads to', 'From a few generic pitches to a pipeline of personal ones', 'Nitro lets us reach many more prospects with proof about their own site, improve conversion with personal findings and a named team, put available experts to work, and scale with an agent marketplace and agents that can run 24x7. Next: a live demo replaying one real run.');
  grid(s, [
    { icon: 'growth', title: 'Reach many more', body: 'Analyse and contact many more prospects, each with proof about their own site.' },
    { icon: 'target', title: 'Better conversion', body: 'Personal findings, a redesign and a named team instead of a generic deck.' },
    { icon: 'dev', title: 'Talent at work', body: 'Available experts review, fine-tune and get matched to new projects.' },
    { icon: 'robot', title: 'Agents that scale', body: 'An agent marketplace, and agents that can run 24x7 in the background.' },
  ], 4, 2.0, 2.1);
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 4.2, y: 4.75, w: 4.93, h: 0.9, rectRadius: 0.45, fill: { color: K.acc }, line: { color: K.acc }, shadow: shadow() });
  text(s, '▶  Live demo: one real run', 4.2, 4.75, 4.93, 0.9, { fontSize: 22, bold: true, color: 'FFFFFF', align: 'center', valign: 'middle' });
};
S.appendix = () => {
  const s = slide('DARK', 'Appendix', 'More detail', 'The appendix keeps the full detail: every pain point, each step of the run, the agent marketplace, the technology, trust, the business case, the roadmap and a one-slide recap.');
  s.addText('Every pain point, each step of the run, the agent marketplace, the technology, trust, the roadmap and a one-slide recap.', { placeholder: 'body' });
};

const MAIN = ['title', 'bang', 'target', 'p6', 'p4', 'whatif', 'paste', 'team', 'how', 'tenders', 'finds', 'depth', 'tech', 'redesign', 'people', 'mapping', 'report', 'cost', 'pitch', 'close'];
section = 'Main presentation'; pres.addSection({ title: section });
for (const k of MAIN) S[k]();
section = 'Appendix'; pres.addSection({ title: section });
S.appendix();
for (const k of Object.keys(S)) if (!MAIN.includes(k) && k !== 'appendix') S[k]();

await pres.writeFile({ fileName: OUT });
console.log(`Wrote ${OUT}`);
