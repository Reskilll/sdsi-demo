// Shared helpers, report panels and the ROI calculator. Used by the main page and the review window.
const $ = (s, r = document) => r.querySelector(s);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
const inr = (n) => '₹' + new Intl.NumberFormat('en-IN').format(Math.round(n));
let panels = {}, lastPrice = 1200000;
const TABS = [['research', 'Market research'], ['audit', 'Site audit'], ['stack', 'Tech stack'], ['prototype', 'Redesign'], ['team', 'Organisation match'], ['estimate', 'Estimate'], ['deck', 'Deck'], ['roi', 'ROI']];
const roiDefaults = { idle: 12, cost: 250000, margin: 30, base: 2, target: 10, winBase: 10, winTarget: 20 };
let roi = { ...roiDefaults };
function showTab(k) { document.querySelectorAll('#tabs button').forEach((b) => b.classList.toggle('on', b.dataset.t === k)); document.querySelectorAll('.pane').forEach((p) => p.classList.toggle('on', p.dataset.p === k)); }
function initTabs() { $('#tabs').innerHTML = TABS.map(([k, l], i) => `<button data-t="${k}" class="${i ? '' : 'on'}">${l}</button>`).join(''); $('#tabs').onclick = (e) => { const k = e.target.dataset.t; if (k) showTab(k); }; }

// Light/dark theme shared by every page.
function applyTheme(t) { document.documentElement.dataset.theme = t; const b = $('#themeBtn'); if (b) b.textContent = t === 'light' ? '🌙 Dark' : '☀️ Light'; try { localStorage.setItem('nitro-theme', t); } catch {} }
function initTheme() { let t = 'light'; try { t = localStorage.getItem('nitro-theme') || 'light'; } catch {} applyTheme(t); const b = $('#themeBtn'); if (b) b.onclick = () => applyTheme(document.documentElement.dataset.theme === 'light' ? 'dark' : 'light'); }
function initLightbox() { const lb = $('#lb'); if (!lb) return; lb.onclick = () => lb.classList.remove('on'); document.addEventListener('keydown', (e) => { if (e.key === 'Escape') lb.classList.remove('on'); }); }

// ── panels ──

// ── dashboard helpers (v0.4.4): big numbers, one accent colour, status colour only where it means something ──
const CATNAME = { geo: 'AI search', a11y: 'Accessibility', ux: 'UX', speed: 'Speed', mobile: 'Mobile' };
const KEYMETRIC = { speed: 'LCP', mobile: 'Small tap targets', a11y: 'Rules failed', geo: 'Answerability (1-5)' };
const lakhs = (n) => (n / 100000).toFixed(1);
const clipText = (t, n) => { t = String(t ?? ''); return t.length > n ? t.slice(0, n - 1).trimEnd() + '…' : t; };
const statusOf = (f) => (f >= 0.85 ? 'strong' : f >= 0.5 ? 'partial' : 'gap');
const statusWord = { strong: 'Strong', partial: 'Partial', gap: 'Gap' };
/** A ring with the number inside. One accent colour; the meaning is in the number, not the hue. */
function bigRing(value, suffix = '', size = 170) {
  const C = 2 * Math.PI * 52;
  return `<div class="hring" style="width:${size}px;height:${size}px"><svg viewBox="0 0 120 120" aria-hidden="true"><circle cx="60" cy="60" r="52" fill="none" style="stroke:var(--inset)" stroke-width="10"/><circle cx="60" cy="60" r="52" fill="none" style="stroke:var(--acc)" stroke-width="10" stroke-linecap="round" stroke-dasharray="${(C * Math.min(100, value) / 100).toFixed(1)} ${C.toFixed(1)}" transform="rotate(-90 60 60)"/></svg><b><span>${value}</span><small>${suffix}</small></b></div>`;
}
function keyMetric(c) {
  if (c.category === 'ux') { const w = Object.entries(c.metrics).sort((a, b) => a[1] - b[1])[0]; return w ? [`Weakest: ${w[0].toLowerCase()}`, `${w[1]}/5`] : null; }
  const k = KEYMETRIC[c.category]; return k && c.metrics[k] !== undefined ? [k, c.metrics[k]] : (Object.entries(c.metrics)[0] ?? null);
}
const monogram = (n) => String(n).replace(/\(.*?\)/g, '').split(/[\s./-]+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join('').toUpperCase();
/** A technology's logo from web/assets/tech (see scripts/build-tech-icons.ts), or a neutral monogram badge when there is none. */
const techIcon = (id, name, size = 28) => (typeof TECH_ICON_IDS !== 'undefined' && TECH_ICON_IDS.has(id)
  ? `<span class="ticon" style="--s:${size}px"><img src="/web/assets/tech/${esc(id)}.svg" alt="" loading="lazy"></span>`
  : `<span class="ticon mono" style="--s:${size}px">${esc(monogram(name))}</span>`);
const G = (g) => `<span class="grade g${g}">${esc(g)}</span>`;
function renderPanel(name) {
  const d = panels[name]; const pane = $(`.pane[data-p="${name}"]`); if (!pane) return;
  document.querySelector(`#tabs [data-t="${name}"]`)?.classList.add('has');
  if (name === 'research') { // the Market Researcher's brief: what is happening at the company, and what we can do about it
    pane.innerHTML = `<div class="rsum"><div class="hlabel">Market research · ${esc(d.company)}</div><p>${esc(d.summary)}</p><div class="muted">Sources read: ${esc((d.sources ?? []).join(', '))}</div></div>
      <div class="rgrid">${(d.items ?? []).map((i) => `<div class="ritem ${i.tone === 'bad' ? 'bad' : 'warn'}"><div class="rk">${i.kind === 'news' ? '📰 In the news' : '📈 Market trend'}</div><h3>${esc(i.title)}</h3><p>${esc(i.headline)}</p><div class="rangle"><span>What we can do</span><b>${esc(i.angle)}</b></div></div>`).join('')}</div>`;
    return;
  }
  if (name === 'audit') {
    const team = panels.team, stk = panels.stack;
    const allFindings = d.categories.flatMap((c) => c.findings.map((f) => ({ ...f, area: CATNAME[c.category] })));
    const strongN = team ? team.skills.filter((x) => statusOf(x.fit) === 'strong').length : 0;
    const cards = [
      `<div class="herocard"><div class="hlabel">Site score</div>${bigRing(d.overall, '/100')}<div class="hcap"><span class="grade g${esc(d.grade)}">${esc(d.grade)}</span> Grade ${esc(d.grade)} · ${esc(new URL(d.url).hostname.replace(/^www\./, ''))}</div></div>`,
      team ? `<div class="herocard focus"><div class="hlabel">Organisation match</div>${bigRing(team.orgScore, '/100')}<div class="hcap">${strongN} of ${team.skills.length} needed skills are strong${team.gaps.length ? ` · ${team.gaps.length} gap${team.gaps.length > 1 ? 's' : ''}` : ''}</div></div>` : '',
      stk ? `<div class="herocard"><div class="hlabel">Stack coverage</div>${bigRing(stk.coverage.score, '%')}<div class="hcap">of their ${stk.technologies.length} technologies we can staff now</div></div>` : '',
    ].join('');
    pane.innerHTML = `<div class="hero3">${cards}</div>
    <div class="sec">Scorecard</div>
    <div class="sc5">${d.categories.map((c) => { const km = keyMetric(c); return `<div class="sctile" title="${esc(c.headline)}"><div class="sclabel">${esc(CATNAME[c.category] || c.category)}</div><div class="scnum">${c.score}<span class="grade g${esc(c.grade)}">${esc(c.grade)}</span></div><div class="scbar"><i style="width:${c.score}%"></i></div>${km ? `<div class="scmetric"><span>${esc(km[0])}</span><b>${esc(km[1])}</b></div>` : ''}</div>`; }).join('')}</div>
    <div class="sec">What to fix first</div>
    <div class="fixes">${d.topFixes.slice(0, 3).map((f, i) => `<div class="fx"><div class="n">${i + 1}</div><div class="fxb"><h4>${esc(clipText(f.title, 90))}</h4><p>${esc(clipText(f.impact, 130))}</p><details><summary>Evidence and fix</summary><div class="fxd"><div><span>Evidence</span>${esc(f.evidence)}</div><div><span>Fix</span>${esc(f.fix)}</div></div></details></div></div>`).join('')}</div>
    ${allFindings.length > 3 ? `<details class="allf"><summary>All ${allFindings.length} findings</summary><ul>${allFindings.map((f) => `<li><em>${esc(f.area)}</em>${esc(clipText(f.title, 110))}</li>`).join('')}</ul></details>` : ''}
    <div class="sec">What we saw</div><div class="shots"><img src="${esc(d.screenshot)}" alt="Desktop screenshot of the prospect homepage" data-zoom="${esc(d.screenshot)}"><img src="${esc(d.mobileShot)}" alt="Mobile screenshot" data-zoom="${esc(d.mobileShot)}" onerror="this.style.display='none'"></div>`;
  }
  if (name === 'stack') {
    const t = d.traffic, cov = d.coverage, mbs = (b) => (b / 1e6).toFixed(1) + ' MB', kb = (b) => (b >= 1e6 ? mbs(b) : Math.round(b / 1e3) + ' KB');
    const cnt = { strong: 0, partial: 0, gap: 0 }; cov.skills.forEach((x) => cnt[x.status]++);
    const cover = Object.fromEntries(cov.skills.map((x) => [x.techId, x.status]));
    const cats = {}; d.technologies.forEach((x) => (cats[x.category] ||= []).push(x));
    const rowsHtml = (list) => list.map((x) => `<tr><td class="tn"><span class="tcell">${techIcon(x.techId, x.tech, 30)}${esc(x.tech)}</span></td><td>${esc(x.skillLabel)}</td><td>${x.available} of ${x.headcount}${x.availableFrom && x.available ? `<small> from ${esc(x.availableFrom)}</small>` : ''}</td><td><span class="dot2 d-${x.status}"></span>${statusWord[x.status]}</td></tr>`).join('');
    const head = '<thead><tr><th>Technology</th><th>Our skill</th><th>People free</th><th>Status</th></tr></thead>';
    const shades = [1, 0.8, 0.62, 0.46, 0.32, 0.2, 0.12];
    const total = t.byType.reduce((a, x) => a + x.bytes, 0) || 1, maxDom = Math.max(1, ...t.topDomains.map((x) => x.bytes));
    pane.innerHTML = `<div class="hero3 stk">
      <div class="herocard wide"><div class="hlabel">How well we cover their stack</div><div class="covrow"><div class="covbig">${cov.score}<small>%</small></div><div class="covlist"><div><i class="dot2 d-strong"></i><b>${cnt.strong}</b><span>technologies we can staff now</span></div><div><i class="dot2 d-partial"></i><b>${cnt.partial}</b><span>with limited capacity</span></div><div><i class="dot2 d-gap"></i><b class="${cnt.gap ? 'gapnum' : ''}">${cnt.gap}</b><span>with nobody free</span></div></div></div></div>
      <div class="herocard"><div class="hlabel">Technologies</div><div class="kbig">${d.technologies.length}</div><div class="icostrip">${d.technologies.slice(0, 7).map((x) => techIcon(x.id, x.name, 30)).join('')}</div></div>
      <div class="herocard"><div class="hlabel">Third-party traffic</div><div class="kbig">${t.thirdParty.requestShare}<small>%</small></div><div class="hcap">of ${t.totalRequests} requests</div></div></div>
    <div class="sec">Their technologies</div>
    <div class="techgrid">${Object.entries(cats).map(([c, list]) => `<div class="techcat"><div class="tcl">${esc(c)}</div>${list.map((x) => `<div class="techrow ${x.confidence === 'likely' ? 'likely' : ''}" title="${esc(x.confidence + ': ' + x.evidence.join('; '))}">${techIcon(x.id, x.name, 30)}<span class="tnm">${esc(x.name)}</span><span class="dot2 d-${cover[x.id] || 'none'}"></span></div>`).join('')}</div>`).join('') || '<div class="empty">No known technologies matched.</div>'}</div>
    <div class="legend2"><span><i class="dot2 d-strong"></i>we have people free</span><span><i class="dot2 d-partial"></i>some capacity</span><span><i class="dot2 d-gap"></i>nobody free</span><span><i class="dot2 d-none"></i>not in our skills list</span><span class="faint">faded = seen in one place only, not confirmed</span></div>
    ${cov.skills.length ? `<div class="sec">Where we can help</div><table class="tbl2">${head}<tbody>${rowsHtml(cov.skills.slice(0, 8))}</tbody></table>${cov.skills.length > 8 ? `<details class="allf"><summary>Show ${cov.skills.length - 8} more</summary><table class="tbl2"><tbody>${rowsHtml(cov.skills.slice(8))}</tbody></table></details>` : ''}` : ''}
    <div class="sec">Network traffic</div>
    <div class="netgrid"><div><div class="nlabel">Page weight · ${mbs(t.totalBytes)} · ${t.totalRequests} requests · ${t.uniqueDomains} domains</div>
      <div class="stack2" role="img" aria-label="Page weight by resource type">${t.byType.map((x, i) => `<i style="width:${(100 * x.bytes / total).toFixed(1)}%;opacity:${shades[i % shades.length]}" title="${esc(x.type)}"></i>`).join('')}</div>
      <div class="leg2">${t.byType.slice(0, 5).map((x, i) => `<span><i style="opacity:${shades[i % shades.length]}"></i>${esc(x.type)} ${kb(x.bytes)}</span>`).join('')}</div></div>
      <div><div class="nlabel">Busiest domains</div>${t.topDomains.slice(0, 6).map((x) => `<div class="domrow"><span>${esc(x.domain)}${x.thirdParty ? '' : ' <em>own</em>'}</span><div class="dbar"><i class="${x.thirdParty ? 'tp' : ''}" style="width:${Math.max(3, 100 * x.bytes / maxDom)}%"></i></div><b>${kb(x.bytes)}</b></div>`).join('')}</div></div>
    <p class="note" style="margin-top:14px">Detection reads requests, headers, cookies, page markup and script globals. It is a strong hint, not a certainty. Skills are sample data until connected to the real inventory.</p>`;
  }
  if (name === 'prototype') {
    pane.innerHTML = `<div class="row"><button class="on" data-v="cmp">Before / after</button><button data-v="live">Clickable prototype</button><a class="btn" href="${esc(d.url)}" target="_blank" rel="noopener">Open full page ↗</a></div>
    <div id="pv"></div>
    <div class="chips">${d.reaudit.map((r) => `<span class="chip">${esc(r.category)} ${r.before} → <b>${r.after}</b></span>`).join('')}</div>
    <p class="note">${d.usedLLM ? 'Designed by the model from the brand kit and audit findings.' : 'Offline template mode: layout from the extracted brand kit. Add an API key for fully designed output.'} Concept for pitch purposes.</p>
    <h3>What changed</h3>${d.changes.map((c) => `<div class="fix"><b>${esc(c.fixes)}</b><small>${esc(c.change)}</small></div>`).join('')}`;
    const pv = (v) => { pane.querySelectorAll('.row button').forEach((b) => b.classList.toggle('on', b.dataset.v === v));
      $('#pv').innerHTML = v === 'cmp' ? `<div class="cmp"><img src="${esc(d.after)}" alt="After: redesigned homepage"><img class="top" id="topimg" src="${esc(d.before)}" alt="Before: current homepage"><div class="handle" id="hd"></div><span class="lbl" style="left:10px">BEFORE</span><span class="lbl" style="right:10px">AFTER</span><input type="range" min="0" max="100" value="50" aria-label="Before and after slider"></div>`
        : `<iframe sandbox="allow-popups" src="${esc(d.url)}" title="Redesigned homepage prototype"></iframe>`;
      const r = $('#pv input'); if (r) r.oninput = () => { $('#topimg').style.clipPath = `inset(0 ${100 - r.value}% 0 0)`; $('#hd').style.left = r.value + '%'; }; };
    pane.querySelector('.row').onclick = (e) => { if (e.target.dataset.v) pv(e.target.dataset.v); }; pv('cmp');
  }
  if (name === 'team') {
    const est = d.estimate; lastPrice = (est.priceLow + est.priceHigh) / 2;
    const status = (f) => (f >= 0.85 ? 'strong' : f >= 0.5 ? 'partial' : 'gap');
    const counts = { strong: 0, partial: 0, gap: 0 }; d.skills.forEach((x) => counts[status(x.fit)]++);
    const tone = d.orgScore >= 80 ? 'var(--good)' : d.orgScore >= 60 ? 'var(--warn)' : 'var(--bad)';
    const C = 2 * Math.PI * 52;
    const ring = `<svg class="omring" viewBox="0 0 120 120" role="img" aria-label="Organisation match ${d.orgScore} out of 100"><circle cx="60" cy="60" r="52" fill="none" style="stroke:var(--inset)" stroke-width="12"/><circle cx="60" cy="60" r="52" fill="none" style="stroke:${tone}" stroke-width="12" stroke-linecap="round" stroke-dasharray="${(C * d.orgScore / 100).toFixed(1)} ${C.toFixed(1)}" transform="rotate(-90 60 60)"/><text x="60" y="68" text-anchor="middle" style="fill:var(--fg)" font-size="34" font-weight="800">${d.orgScore}</text></svg>`;
    const gapRows = d.skills.filter((x) => status(x.fit) === 'gap');
    const strong = d.skills.filter((x) => status(x.fit) === 'strong').slice(0, 6);
    const initials = (n) => n.split(' ').map((w) => w[0]).slice(0, 2).join('');
    const hue = (n) => [...n].reduce((a, c) => a + c.charCodeAt(0), 0) % 360;
    pane.innerHTML = `<div class="om-head">${ring}<div class="om-txt"><h3 class="omh">Organisation match</h3><p>How well our skills cover what this prospect needs, weighted by how much each skill matters for the work.</p>
      <div class="om-legend"><span class="st strong">${counts.strong} strong</span><span class="st partial">${counts.partial} partial</span><span class="st gap">${counts.gap} gap${counts.gap === 1 ? '' : 's'}</span><span class="note">of ${d.skills.length} skills needed</span></div></div></div>
    <div class="callouts"><div class="co good"><h4>Where we are strong</h4>${strong.length ? strong.map((x) => `<span class="chip2 strong">${esc(x.label)}</span>`).join('') : '<span class="note">None yet</span>'}</div>
      <div class="co ${gapRows.length ? 'bad' : 'good'}"><h4>${gapRows.length ? 'Gaps to cover' : 'No gaps'}</h4>${gapRows.length ? gapRows.map((x) => `<div class="gaprow"><b>${esc(x.label)}</b><span>${x.available ? x.available + ' free' : 'nobody free'}${x.availableFrom ? ' · from ' + esc(x.availableFrom) : ''}. Plan a partner or a hire.</span></div>`).join('') : '<span class="note">Every needed skill has someone available.</span>'}</div></div>
    <h3>Skill by skill</h3>
    <table class="tbl omt"><thead><tr><th>Skill</th><th>Matters</th><th>Our level</th><th>People free</th><th>Fit</th><th></th></tr></thead><tbody>
    ${d.skills.map((x) => { const st = status(x.fit); const col = st === 'strong' ? 'var(--good)' : st === 'partial' ? 'var(--warn)' : 'var(--bad)'; return `<tr><td class="sk">${esc(x.label)}</td>
      <td><div class="mini"><i style="width:${Math.round(x.weight * 100)}%;background:var(--acc)"></i></div></td>
      <td>${'●'.repeat(x.level)}<span class="dim">${'●'.repeat(Math.max(0, 5 - x.level))}</span></td>
      <td>${x.available} of ${x.headcount}${x.availableFrom ? `<small> · ${esc(x.availableFrom)}</small>` : ''}</td>
      <td><div class="mini"><i style="width:${Math.round(x.fit * 100)}%;background:${col}"></i></div></td>
      <td><span class="st ${st}">${st === 'strong' ? 'Strong' : st === 'partial' ? 'Partial' : 'Gap'}</span></td></tr>`; }).join('')}</tbody></table>
    <h3>Matched team</h3>
    <div class="teamgrid">${d.team.map((t) => `<div class="tcard"><div class="avt" style="background:hsl(${hue(t.name)} 55% 45%)">${esc(initials(t.name))}</div>
      <div class="tinfo"><b>${esc(t.name)}</b><span>${esc(t.role)}</span><div class="tchips">${t.skills.slice(0, 4).map((k) => `<em>${esc(k)}</em>`).join('')}</div><small>Free from ${esc(t.availableFrom)} · level ${t.level}/5</small></div>
      <div class="tfit"><b>${Math.round(t.fit * 100)}%</b><span>fit</span></div></div>`).join('')}</div>
    <p class="note" style="margin-top:12px">Score = 100 × Σ(weight × fit) ÷ Σ(weight), where fit = 60% proficiency + 40% availability. Sample talent data: replace config/bench.json and config/org-skills.json with real data.</p>`;
    renderRoi();
  }
  if (name === 'estimate') {
    const t = panels.team; if (!t) { pane.innerHTML = '<div class="empty">No estimate in this run.</div>'; return; }
    const est = t.estimate; lastPrice = (est.priceLow + est.priceHigh) / 2;
    const ws = est.workstreams, total = ws.reduce((a, w) => a + w.days, 0) || 1, weeks = Math.max(2, est.weeks), cw = Math.ceil(weeks);
    const per = total / weeks;
    // Indicative schedule: the build starts first, fixes run alongside, QA closes, management spans everything.
    const sched = ws.map((w, i) => {
      const isQA = /QA/i.test(w.name), isPM = /management/i.test(w.name);
      const dur = isPM ? weeks : Math.min(weeks, Math.max(0.6, (w.days / per) * 1.6));
      const start = isPM || i === 0 ? 0 : isQA ? Math.max(0, weeks - dur) : Math.min(weeks - dur, 0.35 * weeks * ((i - 1) / Math.max(1, ws.length - 3)));
      return { ...w, start: Math.max(0, start), dur, quiet: isPM };
    });
    const byDays = [...ws].sort((a, b) => b.days - a.days), maxD = byDays[0]?.days || 1;
    pane.innerHTML = `<div class="e2-hero"><div class="e2-label">Estimated investment</div><div class="e2-price">₹${lakhs(est.priceLow)} <span>to</span> ₹${lakhs(est.priceHigh)} <small>lakh</small></div><div class="e2-sub">A range until discovery is complete. Puts ${t.team.length} people to work, recovering about ₹${lakhs(t.idleCostRecovered)} lakh of idle capacity.</div></div>
    <div class="e2-kpis"><div><b>${est.weeks}</b><span>weeks</span></div><div><b>${est.totalDays}</b><span>person-days</span></div><div><b>${t.team.length}</b><span>people</span></div></div>
    <div class="sec">Timeline</div>
    <div class="g2"><div class="g2h" style="--w:${cw}"><span></span>${Array.from({ length: cw }, (_, i) => `<span>Week ${i + 1}</span>`).join('')}</div>
    ${sched.map((w) => `<div class="g2r"><span class="g2l">${esc(clipText(w.name.replace(/ \(.*\)$/, ''), 34))}</span><div class="g2t"><i class="${w.quiet ? 'quiet' : ''}" style="left:${(100 * w.start / cw).toFixed(1)}%;width:${(100 * w.dur / cw).toFixed(1)}%"></i></div></div>`).join('')}</div>
    <div class="sec">Where the effort goes</div>
    <div class="e2bars">${byDays.map((w) => `<div class="e2b"><span>${esc(clipText(w.name.replace(/ \(.*\)$/, ''), 34))}</span><div class="e2bt"><i style="width:${(100 * w.days / maxD).toFixed(1)}%"></i></div><b>${w.days} d<small> ${Math.round(100 * w.days / total)}%</small></b></div>`).join('')}</div>
    <details class="allf"><summary>Assumptions</summary><ul class="assume">${est.assumptions.map((a) => `<li>${esc(a)}</li>`).join('')}</ul><p class="note">Rates, margin and days per issue are sample constants; replace them with real commercial data.</p></details>`;
    renderRoi();
  }
  if (name === 'deck') {
    pane.innerHTML = `<h3>Ready for review</h3><p>The deck and proposal are built from the run's data. Nothing is sent automatically.</p>
    <div class="row"><a class="btn" href="${esc(d.pptx)}" download>⬇ Pitch deck (.pptx)</a><a class="btn" href="${esc(d.proposal)}" target="_blank" rel="noopener">Proposal (.md)</a></div>
    <p class="note">9 slides: title, your site today, top fixes, before/after, proof, plan, why us, investment, next steps.</p>`;
  }
}

// ── ROI ──
function renderRoi() {
  const pane = $('.pane[data-p="roi"]'); if (!pane) return;
  const idleMonthly = roi.idle * roi.cost, project = lastPrice, margin = project * roi.margin / 100;
  const winsBase = roi.base * 4.33 * roi.winBase / 100, winsNew = roi.target * 4.33 * roi.winTarget / 100;
  const field = (k, l, step = 1) => `<label class="f">${l}<input type="number" data-k="${k}" value="${roi[k]}" step="${step}"></label>`;
  pane.innerHTML = `<h3>Cost of unallocated capacity vs. one win</h3>
  ${field('idle', 'Developers between projects')}${field('cost', 'Loaded monthly cost per developer (₹)', 10000)}${field('margin', 'Project margin (%)')}
  ${field('base', 'Proposals / week today')}${field('winBase', 'Win rate today (%)')}${field('target', 'Proposals / week with Nitro')}${field('winTarget', 'Win rate with Nitro (%)')}
  <div class="kpi"><div><b style="color:var(--bad)">${inr(idleMonthly)}</b><span>unallocated capacity cost per month</span></div>
  <div><b>${inr(margin)}</b><span>margin on one project (${inr(project)} at ${roi.margin}%)</span></div>
  <div><b style="color:var(--good)">${(margin / idleMonthly).toFixed(1)} months</b><span>of unallocated cost covered by one win</span></div>
  <div><b>${winsBase.toFixed(1)} → ${winsNew.toFixed(1)}</b><span>wins per month</span></div>
  <div style="grid-column:span 2"><b style="color:var(--good)">+${inr((winsNew - winsBase) * margin)} / month</b><span>extra margin at the project size of the current pitch</span></div></div>
  <p class="note">All inputs are editable placeholders until real talent and pipeline data is available. Project size comes from the latest estimate.</p>`;
  pane.oninput = (e) => { const k = e.target.dataset.k; if (k) { roi[k] = +e.target.value || 0; const pos = e.target.selectionStart; renderRoi(); const el = pane.querySelector(`[data-k="${k}"]`); el.focus(); try { el.setSelectionRange(pos, pos); } catch {} } };
}
