package com.claudecutter.dashboard;

import com.claudecutter.accounting.TokenLedger;
import com.claudecutter.cost.CostCalculator;
import com.claudecutter.model.Pricing;
import com.claudecutter.model.UsageRecord;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Writes a self-contained HTML dashboard (inline CSS + JS + data) so the user can
 * open it directly from disk without a web server or fetch/CORS concerns.
 */
public final class DashboardExporter {

    private final TokenLedger ledger;
    private final Pricing pricing;
    private final ObjectMapper json = new ObjectMapper()
            .enable(SerializationFeature.INDENT_OUTPUT);

    public DashboardExporter(TokenLedger ledger, Pricing pricing) {
        this.ledger = ledger;
        this.pricing = pricing;
    }

    public void export(Path out) {
        try {
            String data = json.writeValueAsString(rows());
            Files.writeString(out, template().replace("/*__DATA__*/", data));
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    private List<Map<String, Object>> rows() {
        List<Map<String, Object>> out = new ArrayList<>();
        for (UsageRecord r : ledger.records()) {
            var b = CostCalculator.compute(r, pricing);
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("ts", r.timestamp().toString());
            row.put("prompt", r.prompt());
            row.put("route", r.route().target());
            row.put("qwenIn", r.qwenUsage() != null ? r.qwenUsage().inputTokens() : 0L);
            row.put("qwenOut", r.qwenUsage() != null ? r.qwenUsage().outputTokens() : 0L);
            row.put("claudeIn", r.claudeUsage() != null ? r.claudeUsage().inputTokens() : 0L);
            row.put("claudeOut", r.claudeUsage() != null ? r.claudeUsage().outputTokens() : 0L);
            row.put("cacheRead", r.claudeUsage() != null ? r.claudeUsage().cacheReadTokens() : 0L);
            row.put("fullContext", r.fullContextTokensEst());
            row.put("compressed", r.compressedContextTokens());
            row.put("cost", b.totalCostUsd());
            row.put("baseline", b.baselineCostUsd());
            out.add(row);
        }
        return out;
    }

    private static String template() {
        return """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ClaudeCutter — Token Savings</title>
<style>
  :root { color-scheme: light; }
  body {
    margin: 0; font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
    background: #f9f9f7; color: #0b0b0b;
  }
  .viz-root {
    --surface-1: #fcfcfb; --text-primary: #0b0b0b; --text-secondary: #52514e;
    --series-1: #2a78d6; --series-2: #eb6834; --series-3: #1baf7a;
    --grid: #e1e0d9; --baseline: #c3c2b7; --muted: #898781;
  }
  @media (prefers-color-scheme: dark) {
    :root { color-scheme: dark; }
    body { background: #0d0d0d; color: #f0efec; }
    .viz-root {
      --surface-1: #1a1a19; --text-primary: #f0efec; --text-secondary: #c3c2b7;
      --series-1: #3987e5; --series-2: #d95926; --series-3: #199e70;
      --grid: #2c2c2a; --baseline: #383835; --muted: #898781;
    }
  }
  header { padding: 28px 32px 8px; max-width: 1080px; margin: 0 auto; }
  h1 { font-size: 26px; margin: 0 0 4px; }
  .sub { color: var(--text-secondary); font-size: 13px; }
  main { max-width: 1080px; margin: 0 auto; padding: 16px 32px 40px; }
  .kpi { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 24px; }
  .tile { background: var(--surface-1); border: 1px solid rgba(11,11,11,0.10); border-radius: 8px; padding: 16px; }
  .tile .label { font-size: 12px; color: var(--text-secondary); }
  .tile .value { font-size: 24px; font-weight: 600; margin-top: 6px; font-variant-numeric: tabular-nums; }
  .tile .delta { font-size: 12px; margin-top: 4px; }
  .up { color: #006300; }
  .down { color: #d03b3b; }
  @media (prefers-color-scheme: dark) { .up { color: #0ca30c; } }
  .panel { background: var(--surface-1); border: 1px solid rgba(11,11,11,0.10); border-radius: 8px; padding: 20px; margin-bottom: 20px; }
  .panel h2 { font-size: 15px; margin: 0 0 16px; }
  .cmp { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .cmp-card { border: 1px solid rgba(11,11,11,0.10); border-radius: 8px; padding: 16px; }
  .cmp-card .ttl { font-size: 12px; color: var(--text-secondary); }
  .cmp-card .big { font-size: 28px; font-weight: 700; margin: 6px 0; font-variant-numeric: tabular-nums; }
  .cmp-card.without { background: #fdf0ee; }
  .cmp-card.with { background: #eaf4ec; }
  @media (prefers-color-scheme: dark) {
    .cmp-card.without { background: #2a1c1a; }
    .cmp-card.with { background: #14261a; }
  }
  .cmp-sub { font-size: 12px; color: var(--text-secondary); }
  .cmp-save { text-align: center; font-size: 13px; margin-top: 12px; }
  .bars { display: flex; flex-direction: column; gap: 10px; }
  .bar-row { display: grid; grid-template-columns: 140px 1fr 90px; align-items: center; gap: 12px; font-size: 12px; }
  .bar-track { background: var(--grid); border-radius: 4px; height: 20px; position: relative; overflow: hidden; }
  .bar-fill { height: 100%; border-radius: 4px; }
  .bar-num { text-align: right; font-variant-numeric: tabular-nums; color: var(--text-secondary); }
  table { width: 100%; border-collapse: collapse; font-size: 12px; }
  th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--grid); }
  th { color: var(--text-secondary); font-weight: 600; }
  td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
  .pill { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; }
  .pill-qwen { background: #e6e0fa; color: #4a3aa7; }
  .pill-claude { background: #cde2fb; color: #184f95; }
  @media (prefers-color-scheme: dark) {
    .pill-qwen { background: #2c2450; color: #b7a6f0; }
    .pill-claude { background: #12314f; color: #86b6ef; }
  }
  svg { display: block; }
  .axis text { fill: var(--muted); font-size: 10px; }
  .gridline { stroke: var(--grid); stroke-width: 1; }
  .axisline { stroke: var(--baseline); stroke-width: 1; }
  .legend { display: flex; gap: 16px; font-size: 11px; color: var(--text-secondary); margin-bottom: 8px; }
  .legend .sw { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 5px; vertical-align: -1px; }
</style>
</head>
<body>
<header>
  <h1>ClaudeCutter</h1>
  <div class="sub">Token reduction dashboard — "saved vs baseline" is an estimate; token/cost totals are measured.</div>
</header>
<main class="viz-root">
  <div class="panel">
    <h2>With plugin vs without plugin — total tokens</h2>
    <div class="cmp" id="cmp"></div>
  </div>

  <div class="kpi" id="kpi"></div>

  <div class="panel">
    <h2>Cost per request — actual vs baseline</h2>
    <div id="costChart"></div>
  </div>

  <div class="panel">
    <h2>Context tokens — full vs compressed</h2>
    <div class="bars" id="ctxBars"></div>
  </div>

  <div class="panel">
    <h2>Requests</h2>
    <div style="overflow-x:auto"><table id="tbl"></table></div>
  </div>
</main>

<script>
const DATA = /*__DATA__*/;

const fmtInt = n => new Intl.NumberFormat('en-US').format(Math.round(n));
const fmtUsd = n => '$' + n.toFixed(4);
const pct = (a,b) => b > 0 ? (a/b*100) : 0;

// ---- KPI row ----
const totalCost = DATA.reduce((s,d)=>s+d.cost,0);
const totalBaseline = DATA.reduce((s,d)=>s+d.baseline,0);
const saved = totalBaseline - totalCost;
const savedPct = pct(saved, totalBaseline);
const fullCtx = DATA.reduce((s,d)=>s+d.fullContext,0);
const compCtx = DATA.reduce((s,d)=>s+d.compressed,0);
const claudeCalls = DATA.filter(d=>d.route==='claude').length;
const qwenCalls = DATA.filter(d=>d.route==='qwen').length;

// "Without plugin" = Claude reads the full codebase + writes the answer.
// "With plugin" = Claude reads only the compressed spec + writes the answer.
// Qwen's routing/compression overhead is shown separately, labeled, so the
// comparison stays apples-to-apples on the metric that matters: Claude tokens.
const claudeIn = DATA.reduce((s,d)=>s+d.claudeIn,0);
const claudeOut = DATA.reduce((s,d)=>s+d.claudeOut,0);
const qwenTok = DATA.reduce((s,d)=>s+d.qwenIn+s+d.qwenOut,0);
const withoutTok = fullCtx + claudeOut;
const withTok = claudeIn + claudeOut;
const tokenSaved = withoutTok - withTok;
const tokenSavedPct = pct(tokenSaved, withoutTok);
document.getElementById('cmp').innerHTML = `
  <div class="cmp-card without">
    <div class="ttl">Without plugin — Claude tokens</div>
    <div class="big">${fmtInt(withoutTok)}</div>
    <div class="cmp-sub">Claude reads the full codebase + writes the answer</div>
  </div>
  <div class="cmp-card with">
    <div class="ttl">With plugin — Claude tokens</div>
    <div class="big">${fmtInt(withTok)}</div>
    <div class="cmp-sub">Claude reads only the compressed spec + writes the answer</div>
  </div>
  <div class="cmp-save" style="grid-column:1/3">
    <strong>${fmtInt(Math.max(0,tokenSaved))} fewer Claude tokens (${tokenSavedPct.toFixed(1)}%)</strong>
    — in dollars: ${fmtUsd(saved)} saved. Qwen routing overhead: ${fmtInt(qwenTok)} tokens
    (a fraction of Claude's per-token cost).
  </div>`;

const kpi = [
  ['Requests', DATA.length, DATA.length+' total'],
  ['Saved vs baseline', fmtUsd(saved), (saved>=0?'▲ ':'▼ ')+Math.abs(savedPct).toFixed(1)+'%', saved>=0],
  ['Context cut', Math.round(pct(fullCtx-compCtx, fullCtx))+'%', fmtInt(fullCtx)+' → '+fmtInt(compCtx)+' tok', true],
  ['Routed to Qwen', qwenCalls+' / '+DATA.length, 'Claude called '+claudeCalls+'×', qwenCalls>0]
];
document.getElementById('kpi').innerHTML = kpi.map(([l,v,d,good])=>`
  <div class="tile">
    <div class="label">${l}</div>
    <div class="value">${v}</div>
    <div class="delta ${good?'up':'down'}">${d}</div>
  </div>`).join('');

// ---- Cost chart (line: actual vs baseline) ----
(function(){
  const el = document.getElementById('costChart');
  const W = el.clientWidth || 900, H = 240, pad = {l:50,r:16,t:12,b:28};
  const n = DATA.length;
  if (n === 0) { el.innerHTML = '<div class="sub">No data yet.</div>'; return; }
  const max = Math.max(...DATA.map(d=>d.baseline)) * 1.1 || 1;
  const x = i => pad.l + (n===1? 0 : i*(W-pad.l-pad.r)/(n-1));
  const y = v => H - pad.b - (v/max)*(H-pad.t-pad.b);

  const line = (fn, color, dash) => {
    let d = DATA.map((r,i)=>(i?'L':'M')+x(i).toFixed(1)+','+y(fn(r)).toFixed(1)).join('');
    return `<path d="${d}" fill="none" stroke="${color}" stroke-width="2" ${dash?'stroke-dasharray="4 4"':''}/>`;
  };
  // gridlines + y labels
  let g = '';
  for (let t=0; t<=4; t++) {
    const v = max*t/4, yy = y(v).toFixed(1);
    g += `<line class="gridline" x1="${pad.l}" y1="${yy}" x2="${W-pad.r}" y2="${yy}"/>`;
    g += `<text class="axis" x="${pad.l-6}" y="${yy}" text-anchor="end" dominant-baseline="middle">${fmtUsd(v)}</text>`;
  }
  el.innerHTML = `
    <div class="legend">
      <span><span class="sw" style="background:var(--series-1)"></span>Actual cost</span>
      <span><span class="sw" style="background:var(--muted)"></span>Baseline (est.)</span>
    </div>
    <svg width="${W}" height="${H}">
      ${g}
      <line class="axisline" x1="${pad.l}" y1="${H-pad.b}" x2="${W-pad.r}" y2="${H-pad.b}"/>
      ${line(r=>r.baseline, 'var(--muted)', true)}
      ${line(r=>r.cost, 'var(--series-1)', false)}
    </svg>`;
})();

// ---- Context bars (before/after) ----
(function(){
  const el = document.getElementById('ctxBars');
  const full = fullCtx || 1;
  const rows = [['Baseline (full context)', fullCtx, 'var(--series-2)'],
                ['Compressed (sent to Claude)', compCtx, 'var(--series-3)']];
  el.innerHTML = rows.map(([l,v,color])=>{
    const w = Math.max(2, v/full*100);
    return `<div class="bar-row">
      <div>${l}</div>
      <div class="bar-track"><div class="bar-fill" style="width:${w}%;background:${color}"></div></div>
      <div class="bar-num">${fmtInt(v)} tok</div>
    </div>`;
  }).join('');
})();

// ---- Table ----
(function(){
  const head = ['Time','Request','Route','Qwen in','Claude in','Claude out','Full ctx','Compressed','Cost','Baseline'];
  const rows = DATA.map(d=>`<tr>
    <td>${new Date(d.ts).toLocaleString()}</td>
    <td>${d.prompt.length>40? d.prompt.slice(0,40)+'…' : d.prompt}</td>
    <td><span class="pill pill-${d.route}">${d.route}</span></td>
    <td class="num">${fmtInt(d.qwenIn)}</td>
    <td class="num">${fmtInt(d.claudeIn)}</td>
    <td class="num">${fmtInt(d.claudeOut)}</td>
    <td class="num">${fmtInt(d.fullContext)}</td>
    <td class="num">${fmtInt(d.compressed)}</td>
    <td class="num">${fmtUsd(d.cost)}</td>
    <td class="num">${fmtUsd(d.baseline)}</td>
  </tr>`).join('');
  document.getElementById('tbl').innerHTML =
    `<thead><tr>${head.map(h=>`<th class="${/in$|out$|ctx$|sed$|ost$|ine$/.test(h)?'num':''}">${h}</th>`).join('')}</tr></thead>
     <tbody>${rows}</tbody>`;
})();
</script>
</body>
</html>
""";
    }
}
