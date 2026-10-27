import { newRun, saveTrace } from './core/context.js';
import { PERSONAS } from './core/events.js';
import { runLead } from './agents/lead.js';
import { closeBrowser } from './tools/browser.js';
import { createServer } from 'node:http';
import { createReadStream, existsSync } from 'node:fs';
import { join } from 'node:path';

// Headless run for testing: serves ./runs on a random port so the prototype can be re-audited.
const target = process.argv[2];
if (!target) { console.error('usage: npm run cli -- <url>'); process.exit(1); }
const srv = createServer((req, res) => {
  const f = join(process.cwd(), (req.url ?? '').split('?')[0]);
  if (f.startsWith(join(process.cwd(), 'runs')) && existsSync(f)) { res.writeHead(200, { 'content-type': f.endsWith('.html') ? 'text/html' : 'application/octet-stream' }); createReadStream(f).pipe(res); } else { res.writeHead(404); res.end(); }
});
srv.listen(0, '127.0.0.1', async () => {
  const port = (srv.address() as { port: number }).port;
  const run = newRun(target, `http://127.0.0.1:${port}`);
  const t0 = Date.now();
  run.bus.subscribe((e) => { const p = PERSONAS[e.from]; console.log(`[${((Date.now() - t0) / 1000).toFixed(1).padStart(5)}s] ${p.emoji} ${p.name.padEnd(16)} ${e.kind.padEnd(13)} ${e.friendly}`); });
  try { await runLead(run); } catch (e) { console.error('Run failed:', e instanceof Error ? e.message : e); } finally { saveTrace(run); await closeBrowser(); srv.close(); }
  console.log(`\nOutput: ${run.dir}`);
});
