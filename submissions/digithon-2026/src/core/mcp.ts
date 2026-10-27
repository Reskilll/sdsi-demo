import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import type { FeedEvent } from './events.js';

// A small MCP server (JSON-RPC over HTTP, the "streamable HTTP" transport with plain JSON replies), so another team can
// reuse an agent's work directly from Claude or any MCP client. Every tool is read-only and works on saved runs, so a
// call never starts a browser or spends model tokens. Connect to /mcp for all agents, or /mcp?agent=<id> for one.

export interface McpDeps { listRuns: () => { id: string; hasTrace: boolean; url?: string; title?: string; overall?: number }[]; readTrace: (id: string) => FeedEvent[] | null }
interface Tool { agent: string; name: string; description: string; input: Record<string, unknown>; run: (args: Record<string, unknown>, d: McpDeps) => unknown }

const RUN_ID = { type: 'object', properties: { run_id: { type: 'string', description: 'A saved run id, from lead_list_runs' } }, required: ['run_id'] };
const panelOf = (d: McpDeps, args: Record<string, unknown>, name: string) => {
  const id = String(args.run_id ?? '');
  if (!/^\w+$/.test(id)) throw new Error('run_id is missing or not valid');
  const trace = d.readTrace(id);
  if (!trace) throw new Error(`No saved run ${id}`);
  const p = trace.find((e) => e.panel?.name === name)?.panel?.data;
  if (p === undefined) throw new Error(`Run ${id} has no ${name} result`);
  return p as Record<string, unknown>;
};
const category = (cat: string) => (args: Record<string, unknown>, d: McpDeps) => {
  const audit = panelOf(d, args, 'audit') as { categories?: { category: string }[] };
  return audit.categories?.find((c) => c.category === cat) ?? null;
};

/** Words in a tender that point to a skill we have (the Tender Scout's triage, without a model). */
function triage(title: string, description: string) {
  const text = `${title} ${description}`.toLowerCase();
  const skills = (JSON.parse(readFileSync(join(process.cwd(), 'config', 'org-skills.json'), 'utf8')) as { skills: { id: string; label: string }[] }).skills;
  const RULES: [RegExp, string][] = [[/website|portal|web\b|homepage/, 'Web'], [/mobile|app\b/, 'Mobile'], [/accessib|gigw|wcag/, 'Accessibility'], [/speed|performance/, 'Performance'], [/language|multilingual|locali/, 'Localisation'], [/cloud|hosting|devops/, 'Cloud and DevOps']];
  const matched = RULES.filter(([re]) => re.test(text)).map(([, s]) => s);
  const notOurs = /civil works|construction|hardware supply|cctv|furniture|vehicles/.test(text);
  const relevant = matched.length > 0 && !notOurs;
  return { relevant, matched, reason: relevant ? `Matches our skills: ${matched.join(', ')}.` : notOurs ? 'Physical goods or civil works: not our kind of work.' : 'No digital skills we offer are named.', ourSkills: skills.length };
}

export const TOOLS: Tool[] = [
  { agent: 'lead', name: 'lead_list_runs', description: 'List saved analyses: run id, website, title and site score.', input: { type: 'object', properties: {} },
    run: (_a, d) => d.listRuns().filter((r) => r.hasTrace).map(({ id, url, title, overall }) => ({ id, url, title, overall })) },
  { agent: 'research', name: 'research_get_brief', description: 'Market research on the company of a run: news and trend signals, what we can do about each, and a summary.', input: RUN_ID, run: (a, d) => panelOf(d, a, 'research') },
  { agent: 'audit', name: 'audit_get_report', description: 'The site audit of a run: overall score, grade, category scores and the top fixes with evidence.', input: RUN_ID, run: (a, d) => panelOf(d, a, 'audit') },
  { agent: 'tech', name: 'tech_get_stack', description: 'Technologies detected on the site, third-party traffic, and how well our people cover each one.', input: RUN_ID, run: (a, d) => panelOf(d, a, 'stack') },
  { agent: 'speed', name: 'speed_get_result', description: 'Speed result of a run: Lighthouse score, Core Web Vitals and findings.', input: RUN_ID, run: category('speed') },
  { agent: 'mobile', name: 'mobile_get_result', description: 'Mobile result of a run: score, tap targets, text size and findings.', input: RUN_ID, run: category('mobile') },
  { agent: 'a11y', name: 'a11y_get_result', description: 'Accessibility result of a run: score and WCAG rules that failed.', input: RUN_ID, run: category('a11y') },
  { agent: 'ux', name: 'ux_get_result', description: 'UX review of a run: rubric scores and design findings.', input: RUN_ID, run: category('ux') },
  { agent: 'geo', name: 'geo_get_result', description: 'AI-search visibility of a run: structured data, llms.txt and answerability.', input: RUN_ID, run: category('geo') },
  { agent: 'redesign', name: 'redesign_get_result', description: 'The redesigned homepage of a run: link to the HTML and the before/after scores.', input: RUN_ID, run: (a, d) => panelOf(d, a, 'prototype') },
  { agent: 'bench', name: 'bench_get_team', description: 'Organisation match, the named team of available experts, gaps and the estimate.', input: RUN_ID, run: (a, d) => panelOf(d, a, 'team') },
  { agent: 'deck', name: 'deck_get_files', description: 'The pitch deck and proposal of a run (download links).', input: RUN_ID, run: (a, d) => panelOf(d, a, 'deck') },
  { agent: 'tenders', name: 'tenders_triage', description: 'Triage a government tender: is it relevant to the skills we offer, and why.',
    input: { type: 'object', properties: { title: { type: 'string' }, description: { type: 'string' } }, required: ['title'] },
    run: (a) => triage(String(a.title ?? ''), String(a.description ?? '')) },
];

export const toolsFor = (agent?: string | null) => TOOLS.filter((t) => !agent || t.agent === agent || t.name === 'lead_list_runs');

type Rpc = { jsonrpc: '2.0'; id?: string | number | null; method: string; params?: Record<string, unknown> };
const ok = (id: Rpc['id'], result: unknown) => ({ jsonrpc: '2.0', id, result });
const fail = (id: Rpc['id'], code: number, message: string) => ({ jsonrpc: '2.0', id: id ?? null, error: { code, message } });

/** One JSON-RPC message in, one reply out (null for a notification, which needs no reply). */
export function handleMcp(msg: Rpc, agent: string | null, d: McpDeps): unknown {
  if (msg?.jsonrpc !== '2.0' || typeof msg.method !== 'string') return fail(msg?.id, -32600, 'Invalid request');
  if (msg.id === undefined) return null; // notifications/initialized and friends
  const tools = toolsFor(agent);
  switch (msg.method) {
    case 'initialize':
      return ok(msg.id, { protocolVersion: String(msg.params?.protocolVersion ?? '2025-06-18'), capabilities: { tools: {} }, serverInfo: { name: agent ? `nitro-${agent}` : 'nitro', version: '1.0.0' },
        instructions: 'Nitro agents: read-only access to saved prospect analyses. Start with lead_list_runs to get a run_id.' });
    case 'ping': return ok(msg.id, {});
    case 'tools/list': return ok(msg.id, { tools: tools.map((t) => ({ name: t.name, description: t.description, inputSchema: t.input, annotations: { readOnlyHint: true } })) });
    case 'tools/call': {
      const t = tools.find((x) => x.name === msg.params?.name);
      if (!t) return fail(msg.id, -32602, `Unknown tool: ${String(msg.params?.name)}`);
      try { return ok(msg.id, { content: [{ type: 'text', text: JSON.stringify(t.run((msg.params?.arguments ?? {}) as Record<string, unknown>, d), null, 2) }] }); }
      catch (e) { return ok(msg.id, { content: [{ type: 'text', text: e instanceof Error ? e.message : String(e) }], isError: true }); }
    }
    default: return fail(msg.id, -32601, `Method not found: ${msg.method}`);
  }
}
