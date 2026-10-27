import { createServer, type IncomingMessage, type ServerResponse } from 'node:http';
import { createReadStream, existsSync, mkdirSync, readdirSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import { basename, extname, join, normalize, resolve } from 'node:path';
import { newRun, saveTrace, type RunContext } from './core/context.js';
import { PERSONAS, type FeedEvent } from './core/events.js';
import { assertPublicUrl } from './core/ssrf.js';
import { llmAvailable, MODEL } from './core/llm.js';
import { runLead } from './agents/lead.js';
import { loadMarketplace, marketplaceSummary } from './core/marketplace.js';
import { closeBrowser } from './tools/browser.js';
import { checkDeck, slideTexts } from './core/deckCheck.js';
import { handleMcp } from './core/mcp.js';

const PORT = Number(process.env.PORT ?? 3000);
const BASE = `http://127.0.0.1:${PORT}`;
const ROOT = process.cwd();
const MAX_CONCURRENT = 3;
/** Longest pause between replayed events at 1x, so a 70 s model call does not become a 70 s wait. */
const REPLAY_MAX_GAP_MS = 2500;
/** Shortest pause between replayed events at 1x, so bursts of events stay readable. */
const REPLAY_MIN_GAP_MS = 700;
const runs = new Map<string, RunContext & { finished?: boolean }>();

const MIME: Record<string, string> = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml', '.md': 'text/markdown; charset=utf-8',
  '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
};

function json(res: ServerResponse, code: number, body: unknown) {
  res.writeHead(code, { 'content-type': 'application/json' });
  res.end(JSON.stringify(body));
}

/** Pages from a run (the redesign) are written by a model from a third-party site, so they may never run scripts. */
const RUN_PAGE_CSP = "script-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'self'";
function serveFile(res: ServerResponse, base: string, rel: string, csp?: string) {
  const full = resolve(base, normalize(rel));
  if (!full.startsWith(resolve(base)) || !existsSync(full) || !statSync(full).isFile()) { res.writeHead(404); return res.end('Not found'); }
  res.writeHead(200, { 'content-type': MIME[extname(full)] ?? 'application/octet-stream', 'x-content-type-options': 'nosniff', ...(csp && extname(full) === '.html' ? { 'content-security-policy': csp } : {}) });
  createReadStream(full).pipe(res);
}

async function readBody(req: IncomingMessage): Promise<string> {
  let b = '';
  for await (const c of req) { b += c; if (b.length > 50_000) throw new Error('Body too large'); }
  return b;
}

interface RunInfo { id: string; hasTrace: boolean; url?: string; title?: string; overall?: number; orgScore?: number; seconds?: number; startedAt?: number; events?: number }

/** A file upload as raw bytes, with a size limit. */
async function readBytes(req: IncomingMessage, max: number): Promise<Buffer> {
  const parts: Buffer[] = []; let n = 0;
  for await (const c of req) { n += (c as Buffer).length; if (n > max) throw new Error('File too large (limit 25 MB)'); parts.push(c as Buffer); }
  return Buffer.concat(parts);
}

function readTrace(id: string): FeedEvent[] | null {
  const f = join(ROOT, 'runs', id, 'trace.json');
  try { return existsSync(f) ? (JSON.parse(readFileSync(f, 'utf8')) as FeedEvent[]) : null; } catch { return null; }
}

/** Past runs on disk, newest first. Details come from the saved trace, so this costs nothing. */
function listRuns(): RunInfo[] {
  const root = join(ROOT, 'runs');
  if (!existsSync(root)) return [];
  return readdirSync(root).filter((d) => /^\w+$/.test(d) && statSync(join(root, d)).isDirectory()).map((id): RunInfo => {
    const trace = readTrace(id);
    if (!trace?.length) {
      const prop = join(root, id, 'proposal.md');
      const title = existsSync(prop) ? readFileSync(prop, 'utf8').split('\n')[0].replace(/^#\s*Proposal:\s*/, '') : undefined;
      return { id, hasTrace: false, title, startedAt: statSync(join(root, id)).mtimeMs };
    }
    const panel = (n: string) => trace.find((e) => e.panel?.name === n)?.panel?.data as Record<string, unknown> | undefined;
    const audit = panel('audit'), team = panel('team');
    const done = trace.find((e) => e.kind === 'done');
    return { id, hasTrace: true, url: audit?.url as string | undefined, title: audit?.title as string | undefined, overall: audit?.overall as number | undefined, orgScore: team?.orgScore as number | undefined,
      seconds: done ? Math.round((done.ts - trace[0].ts) / 1000) : undefined, startedAt: trace[0].ts, events: trace.length };
  }).sort((a, b) => (b.startedAt ?? 0) - (a.startedAt ?? 0));
}

// TODO(next): login screen. Sign-in, a session cookie, and a check on the review, upload and MCP endpoints so
// approvals and Knox submissions belong to a named reviewer. Today the server is single-user on 127.0.0.1.
const server = createServer(async (req, res) => {
  const url = new URL(req.url ?? '/', BASE);
  const path = url.pathname;
  try {
    if (req.method === 'POST' && path === '/api/runs') {
      if ([...runs.values()].filter((r) => !r.finished).length >= MAX_CONCURRENT) return json(res, 429, { error: 'Too many runs in progress. Try again in a minute.' });
      const { url: target } = JSON.parse(await readBody(req) || '{}') as { url?: string };
      if (!target) return json(res, 400, { error: 'Missing url' });
      const safe = await assertPublicUrl(target);
      const run = newRun(safe.href, BASE) as RunContext & { finished?: boolean };
      runs.set(run.runId, run);
      void runLead(run)
        .catch((e) => run.bus.emit({ from: 'lead', kind: 'error', friendly: 'This run could not be completed.', detail: { summary: String(e) } }))
        .finally(() => { run.finished = true; saveTrace(run); });
      return json(res, 200, { runId: run.runId });
    }
    const ev = path.match(/^\/api\/runs\/([\w]+)\/events$/);
    if (req.method === 'GET' && ev) {
      const run = runs.get(ev[1]);
      if (!run) return json(res, 404, { error: 'Unknown run' });
      res.writeHead(200, { 'content-type': 'text/event-stream', 'cache-control': 'no-cache', connection: 'keep-alive' });
      const send = (e: unknown) => res.write(`data: ${JSON.stringify(e)}\n\n`);
      run.bus.events.forEach(send);
      const unsub = run.bus.subscribe(send);
      req.on('close', unsub);
      return;
    }
    if (req.method === 'GET' && path === '/api/runs') return json(res, 200, listRuns());
    // The saved feed of one run: the review window builds its report panels from it. Reads a file only.
    const tr = path.match(/^\/api\/runs\/(\w+)\/trace$/);
    if (req.method === 'GET' && tr) { const trace = readTrace(tr[1]); return trace ? json(res, 200, trace) : json(res, 404, { error: 'No saved trace for this run.' }); }
    // Replay: streams a saved trace with its original timing. No model, browser or network call is made.
    const rp = path.match(/^\/api\/replay\/(\w+)\/events$/);
    if (req.method === 'GET' && rp) {
      const trace = readTrace(rp[1]);
      if (!trace?.length) return json(res, 404, { error: 'No saved trace for this run.' });
      const speed = Math.max(0, Number(url.searchParams.get('speed') ?? 1)); // 0 = instant
      res.writeHead(200, { 'content-type': 'text/event-stream', 'cache-control': 'no-cache', connection: 'keep-alive' });
      let closed = false;
      req.on('close', () => { closed = true; });
      for (let i = 0; i < trace.length && !closed; i++) {
        if (speed > 0 && i > 0) await new Promise((r) => setTimeout(r, Math.max(REPLAY_MIN_GAP_MS, Math.min(trace[i].ts - trace[i - 1].ts, REPLAY_MAX_GAP_MS)) / speed));
        res.write(`data: ${JSON.stringify(trace[i])}\n\n`);
      }
      if (!closed) res.write('event: end\ndata: {}\n\n');
      return res.end();
    }
    // Your own deck: stored with the run, then checked against the analysis we already have (text matching, no model).
    const dk = path.match(/^\/api\/runs\/(\w+)\/deck$/);
    if (dk) {
      const dir = join(ROOT, 'runs', dk[1], 'uploads'), saved = join(dir, 'deck-review.json');
      if (req.method === 'GET') return existsSync(saved) ? json(res, 200, JSON.parse(readFileSync(saved, 'utf8'))) : json(res, 404, { error: 'No deck uploaded yet.' });
      if (req.method === 'POST') {
        const trace = readTrace(dk[1]);
        if (!trace) return json(res, 404, { error: 'Unknown run' });
        const name = basename(String(req.headers['x-file-name'] ?? 'deck.pptx')).replace(/[^\w.\- ]/g, '_').slice(0, 80);
        if (!/\.pptx$/i.test(name)) return json(res, 400, { error: 'Please upload a PowerPoint file (.pptx).' });
        const buf = await readBytes(req, 25 * 1024 * 1024);
        if (buf.subarray(0, 2).toString() !== 'PK') return json(res, 400, { error: 'That file is not a valid .pptx.' });
        const texts = await slideTexts(buf).catch(() => null);
        if (!texts?.length) return json(res, 400, { error: 'No slides could be read from that file.' });
        const panel = <T>(n: string) => trace.find((e) => e.panel?.name === n)?.panel?.data as T | undefined;
        const result = checkDeck(texts, { audit: panel('audit'), stack: panel('stack'), prototype: panel('prototype'), team: panel('team'), research: panel('research') }, name);
        mkdirSync(dir, { recursive: true });
        writeFileSync(join(dir, `${Date.now()}-${name}`), buf);
        writeFileSync(saved, JSON.stringify(result));
        return json(res, 200, result);
      }
    }
    // MCP: reuse an agent directly from Claude or another MCP client (read-only tools on saved runs).
    if (path === '/mcp') {
      const origin = req.headers.origin;
      if (origin && !/^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(origin)) return json(res, 403, { error: 'Origin not allowed' });
      if (req.method !== 'POST') { res.writeHead(405, { allow: 'POST' }); return res.end(); }
      const agent = url.searchParams.get('agent');
      const body = JSON.parse(await readBody(req) || 'null');
      const deps = { listRuns, readTrace };
      const out = Array.isArray(body) ? body.map((m) => handleMcp(m, agent, deps)).filter((x) => x !== null) : handleMcp(body, agent, deps);
      if (out === null || (Array.isArray(out) && !out.length)) { res.writeHead(202); return res.end(); }
      return json(res, 200, out);
    }
    // Which agents are working right now in live runs on this server (the marketplace shows them as active).
    if (path === '/api/activity') {
      const active = new Set<string>();
      for (const r of runs.values()) {
        if (r.finished) continue;
        const open = new Map<string, string>();
        for (const e of r.bus.events) { if (e.tool && /_start$/.test(e.kind)) open.set(e.tool.callId, e.from); if (e.tool && /_end$/.test(e.kind)) open.delete(e.tool.callId); }
        open.forEach((a) => active.add(a)); active.add('lead');
      }
      return json(res, 200, { active: [...active] });
    }
    if (path === '/api/health') return json(res, 200, { ok: true, llm: llmAvailable, model: llmAvailable ? MODEL : null, runsInProgress: [...runs.values()].filter((r) => !r.finished).length, maxConcurrent: MAX_CONCURRENT });
    if (path === '/api/marketplace') { const agents = loadMarketplace(); return json(res, 200, { summary: marketplaceSummary(agents), agents }); }
    if (path === '/api/config') return json(res, 200, { personas: PERSONAS, llm: llmAvailable, model: llmAvailable ? MODEL : null });
    const file = path.match(/^\/runs\/([\w]+)\/([\w.\-]+)$/);
    if (file) return serveFile(res, join(ROOT, 'runs', file[1]), file[2], RUN_PAGE_CSP);
    // The landing screen is the front door; the live feed, office and replay are the workspace.
    if (path === '/' || path === '/home.html') return serveFile(res, join(ROOT, 'web'), 'home.html');
    if (path === '/workspace.html' || path === '/index.html') return serveFile(res, join(ROOT, 'web'), 'index.html');
    if (path === '/review.html') return serveFile(res, join(ROOT, 'web'), 'review.html');
    if (path === '/marketplace.html') return serveFile(res, join(ROOT, 'web'), 'marketplace.html');
    if (path === '/presentation.html') return serveFile(res, join(ROOT, 'web'), 'presentation.html');
    if (path.startsWith('/web/')) return serveFile(res, join(ROOT, 'web'), path.slice(5));
    res.writeHead(404); res.end('Not found');
  } catch (e) {
    json(res, 400, { error: e instanceof Error ? e.message : 'Bad request' });
  }
});

server.listen(PORT, '127.0.0.1', () => console.log(`Nitro running at ${BASE}  (LLM: ${llmAvailable ? MODEL : 'offline mode'})`));
process.on('SIGINT', () => { void closeBrowser().then(() => process.exit(0)); });
