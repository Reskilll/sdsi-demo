// A small pixel-art office. Every robot sits at its desk; the scene is driven only by the events the feed shows,
// so live runs and replays animate identically.
const OFFICE = (() => {
  const W = 320, H = 216, LANE_Y = 128, SPEED = 46;
  const DESK_X = [40, 100, 160, 220, 280];
  const ROWS = [{ d: 76, stand: 120, ids: ['audit', 'speed', 'mobile', 'a11y', 'ux'] }, { d: 164, stand: 142, ids: ['tech', 'geo', 'redesign', 'bench', 'deck'] }];
  const SKY = ['#d6ecff', '#e9f5ff'], BLOCKS = ['#bcd6ef', '#a9c6e6', '#c9ddf2'];
  const rnd = (a, b) => a + Math.random() * (b - a);

  class Office {
    constructor(canvas, plateHost, personas, signEl) {
      this.canvas = canvas; this.g = canvas.getContext('2d'); this.plateHost = plateHost; this.personas = personas; this.signEl = signEl;
      this.agents = {}; this.plates = {}; this.confetti = []; this.last = 0; this.k = 2; this.running = false;
      ROWS.forEach((row, r) => row.ids.forEach((id, i) => { this.agents[id] = this.newAgent(id, DESK_X[i] - 6, row.d + 4, DESK_X[i], r); }));
      this.agents.lead = this.newAgent('lead', 160, LANE_Y, null, -1);
      this.agents.research = this.newAgent('research', 64, LANE_Y, null, -1); // no desk: out and about, reading the news
      this.buildPlates(); this.resize(); window.addEventListener('resize', () => this.resize());
    }
    newAgent(id, hx, hy, deskX, row) {
      return { id, hx, hy, deskX, row, x: hx, y: hy, flip: false, path: [], jobs: [], job: null, pauseUntil: 0, open: new Set(), pulseUntil: 0, flash: null, cheerUntil: 0, nextWander: 0, blinkUntil: 0, nextBlink: rnd(1500, 4500), lastWorking: false };
    }
    buildPlates() {
      this.plateHost.innerHTML = '';
      for (const [id, a] of Object.entries(this.agents)) {
        if (a.row < 0) continue;
        const el = document.createElement('div'); el.className = 'plate'; el.textContent = this.personas[id]?.name ?? id;
        el.style.left = (a.deskX / W) * 100 + '%'; el.style.top = ((ROWS[a.row].d + 14) / H) * 100 + '%';
        this.plateHost.appendChild(el); this.plates[id] = el;
      }
    }
    setPersonas(p) { this.personas = p; for (const [id, el] of Object.entries(this.plates)) el.textContent = p[id]?.name ?? id; }
    resize() {
      const w = this.canvas.parentElement.clientWidth || 600;
      this.k = Math.max(2, Math.round((w * (window.devicePixelRatio || 1)) / W));
      this.canvas.width = W * this.k; this.canvas.height = H * this.k;
      this.plateHost.style.fontSize = Math.max(8, (w / W) * 5.2) + 'px';
      if (this.signEl) this.signEl.style.fontSize = Math.max(9, (w / W) * 6.4) + 'px';
    }
    reset() {
      for (const a of Object.values(this.agents)) Object.assign(a, { x: a.hx, y: a.hy, path: [], jobs: [], job: null, open: new Set(), pulseUntil: 0, flash: null, cheerUntil: 0, flip: false });
      this.confetti = [];
    }
    /** Stand everyone down (a replay was stopped): nobody is mid-task, visiting or showing a bubble. */
    calm() {
      for (const a of Object.values(this.agents)) {
        a.open.clear(); a.pulseUntil = 0; a.flash = null; a.jobs = []; a.job = null;
        a.path = a.deskX == null || (a.x === a.hx && a.y === a.hy) ? [] : [{ x: a.x, y: LANE_Y }, { x: a.hx, y: LANE_Y }, { x: a.hx, y: a.hy }];
      }
    }
    start() { if (this.running) return; this.running = true; const loop = (t) => { if (!this.running) return; if (t - this.last > 66) { this.tick(t); this.last = t; } requestAnimationFrame(loop); }; requestAnimationFrame(loop); }

    // ── events ──
    handle(ev) {
      const now = performance.now(), a = this.agents[ev.from];
      if (a) {
        if (ev.tool && /_start$/.test(ev.kind)) a.open.add(ev.tool.callId);
        else if (ev.tool && /_end$/.test(ev.kind)) { a.open.delete(ev.tool.callId); a.flash = { icon: ev.tool.ok ? 'check' : 'warn', until: now + 2200 }; }
        else if (ev.kind === 'warning' || ev.kind === 'error') a.flash = { icon: 'warn', until: now + 2400 };
        else if (ev.kind === 'partial_result' || (ev.kind === 'finding' && ev.card)) a.flash = { icon: 'check', until: now + 2200 };
        else a.pulseUntil = now + 2500;
      }
      const to = ev.to && ev.to !== 'all' ? this.agents[ev.to] : null;
      if (a && to && to !== a && ['handoff', 'question', 'answer'].includes(ev.kind)) a.jobs.push({ target: to, phase: 'go' });
      if (ev.kind === 'plan') { const c = this.agents.lead; c.path = [{ x: 160, y: LANE_Y }]; c.flash = { icon: 'flag', until: now + 2800 }; }
      if (ev.kind === 'done') this.celebrate(now);
    }
    celebrate(now) {
      for (const a of Object.values(this.agents)) { a.cheerUntil = now + 3000; a.flash = { icon: 'check', until: now + 3000 }; }
      const cols = ['#ff7a59', '#2f6fed', '#10b981', '#fbbf24', '#e0457b', '#8b5cf6'];
      this.confetti = Array.from({ length: 60 }, () => ({ x: rnd(0, W), y: rnd(-40, 0), vy: rnd(18, 42), vx: rnd(-8, 8), c: cols[Math.floor(rnd(0, cols.length))], t: now + 3500 }));
    }
    working(a, now) { return a.open.size > 0 || now < a.pulseUntil; }

    // ── movement ──
    standFor(t) { return { x: t.hx + 12, y: ROWS[t.row]?.stand ?? LANE_Y }; }
    route(a, tx, ty) { const pts = []; if (Math.abs(a.y - LANE_Y) > 3) pts.push({ x: a.x, y: LANE_Y }); pts.push({ x: tx, y: LANE_Y }); if (Math.abs(ty - LANE_Y) > 3) pts.push({ x: tx, y: ty }); return pts; }
    step(a, dt, now) {
      if (a.path.length) {
        const p = a.path[0], dx = p.x - a.x, dy = p.y - a.y, d = Math.hypot(dx, dy), m = SPEED * dt;
        if (d <= m) { a.x = p.x; a.y = p.y; a.path.shift(); } else { a.x += (dx / d) * m; a.y += (dy / d) * m; }
        if (Math.abs(dx) > 0.5) a.flip = dx < 0;
        return;
      }
      if (a.job) {
        if (a.job.phase === 'go') { a.job.phase = 'wait'; a.pauseUntil = now + 1400; a.flash = { icon: 'doc', until: now + 1400 }; }
        else if (a.job.phase === 'wait' && now >= a.pauseUntil) { a.job.phase = 'back'; a.path = a.deskX == null ? [] : [{ x: a.x, y: LANE_Y }, { x: a.hx, y: LANE_Y }, { x: a.hx, y: a.hy }]; }
        else if (a.job.phase === 'back') a.job = null;
        return;
      }
      if (a.jobs.length) {
        a.job = a.jobs.shift(); const s = this.standFor(a.job.target); a.path = this.route(a, s.x, s.y);
        return;
      }
      if (a.deskX == null && now > a.nextWander) { a.path = [{ x: rnd(40, 280), y: LANE_Y }]; a.nextWander = now + rnd(3500, 7000); }
    }
    seated(a) { return a.deskX != null && !a.path.length && !a.job && a.x === a.hx && a.y === a.hy; }

    // ── drawing ──
    tick(now) {
      const dt = Math.min(0.2, (now - (this._t ?? now)) / 1000); this._t = now;
      const g = this.g; g.setTransform(this.k, 0, 0, this.k, 0, 0); g.imageSmoothingEnabled = false;
      for (const a of Object.values(this.agents)) {
        this.step(a, dt, now);
        if (now > a.nextBlink) { a.blinkUntil = now + 160; a.nextBlink = now + rnd(2500, 5500); }
        const w = this.working(a, now);
        if (a.row >= 0 && w !== a.lastWorking) { a.lastWorking = w; this.plates[a.id]?.classList.toggle('on', w); }
      }
      this.drawBg(g, now);
      const all = Object.values(this.agents);
      all.filter((a) => this.seated(a)).forEach((a) => this.drawBot(g, a, now));
      for (const row of ROWS) row.ids.forEach((id, i) => this.drawDesk(g, DESK_X[i], row.d, this.agents[id], now));
      all.filter((a) => !this.seated(a)).sort((p, q) => p.y - q.y).forEach((a) => this.drawBot(g, a, now));
      all.forEach((a) => this.drawBubble(g, a, now));
      this.drawConfetti(g, now, dt);
    }
    drawBot(g, a, now) {
      const moving = a.path.length > 0, w = this.working(a, now), cheering = now < a.cheerUntil, f = Math.floor(now / 230) % 2;
      let pose = 'idle'; if (cheering) pose = 'cheer'; else if (moving) pose = 'walk'; else if (this.seated(a) && w) pose = 'type';
      const bob = cheering ? -Math.abs(Math.sin(now / 160)) * 3 : 0;
      const fr = botFrame(a.id, pose, f, now < a.blinkUntil);
      g.save(); g.translate(Math.round(a.x), Math.round(a.y + bob));
      if (a.flip) g.scale(-1, 1);
      g.drawImage(fr, -8, -BOT_H); g.restore();
    }
    drawDesk(g, cx, d, a, now) {
      const P = (x, y, w, h, c) => { g.fillStyle = c; g.fillRect(x, y, w, h); };
      P(cx - 21, d, 42, 14, OUTLINE); P(cx - 20, d + 1, 40, 4, '#efd3a8'); P(cx - 20, d + 5, 40, 8, '#d3a96f');
      P(cx - 10, d + 2, 11, 2, '#fff'); P(cx - 19, d - 3, 4, 3, '#fff'); P(cx - 19, d - 3, 4, 1, '#ff7a59'); // keyboard, mug
      const w = a ? this.working(a, now) : false, ok = a?.flash && now < a.flash.until && a.flash.icon === 'check';
      P(cx + 3, d - 11, 14, 11, OUTLINE); P(cx + 4, d - 10, 12, 8, ok ? '#7be0b0' : w ? '#7fb0ff' : '#56627c');
      if (w) { const s = Math.floor(now / 200) % 4; for (let i = 0; i < 3; i++) P(cx + 5, d - 9 + ((i * 2 + s) % 6), 6 + ((i + s) % 3) * 2, 1, '#fff'); }
      P(cx + 8, d - 2, 4, 2, OUTLINE);
    }
    drawBubble(g, a, now) {
      let icon = null, color = (SPECS[a.id] || SPECS.lead).accent;
      if (a.flash && now < a.flash.until) { icon = a.flash.icon; color = icon === 'check' ? '#10a56b' : icon === 'warn' ? '#e08a00' : color; }
      else if (this.working(a, now)) icon = Math.floor(now / 900) % 2 ? (AGENT_ICON[a.id] || 'dots') : 'dots';
      if (!icon) return;
      const bob = now < a.cheerUntil ? -Math.abs(Math.sin(now / 160)) * 3 : 0;
      const bx = Math.round(a.x) - 6, by = Math.round(a.y - BOT_H - 14 + bob);
      g.fillStyle = OUTLINE; g.fillRect(bx - 1, by, 13, 11); g.fillRect(bx, by - 1, 11, 13); g.fillRect(bx + 4, by + 12, 3, 2);
      g.fillStyle = '#fff'; g.fillRect(bx, by + 1, 11, 9); g.fillRect(bx + 1, by, 9, 11); g.fillRect(bx + 5, by + 11, 1, 2);
      drawIcon(g, icon, bx + 2, by + 2, color);
    }
    drawConfetti(g, now, dt) {
      this.confetti = this.confetti.filter((c) => now < c.t);
      for (const c of this.confetti) { c.y += c.vy * dt; c.x += c.vx * dt; g.fillStyle = c.c; g.fillRect(Math.round(c.x), Math.round(c.y), 2, 2); }
    }
    drawBg(g) {
      const P = (x, y, w, h, c) => { g.fillStyle = c; g.fillRect(x, y, w, h); };
      P(0, 0, W, 52, '#fbf1de'); P(0, 50, W, 2, '#e8d3ae');
      for (let y = 52; y < H; y += 16) for (let x = 0; x < W; x += 16) P(x, y, 16, 16, ((x + y) / 16) % 2 ? '#f3e6cb' : '#f7ecd6');
      // soft rug under the walking lane
      P(48, 100, 224, 56, '#e9eff8'); P(50, 102, 220, 52, '#eef3fa');
      // windows with a pale skyline
      [14, 68, 208, 262].forEach((x, wi) => {
        P(x - 1, 5, 46, 34, '#d8c3a0'); P(x, 6, 44, 32, SKY[0]); P(x, 22, 44, 16, SKY[1]);
        for (let i = 0; i < 6; i++) { const bh = 8 + ((i * 7 + wi * 3) % 13), bx = x + 2 + i * 7; P(bx, 38 - bh, 6, bh, BLOCKS[(i + wi) % 3]); }
        P(x + 22, 6, 1, 32, '#d8c3a0'); P(x + 6 + wi * 9, 11, 9, 2, '#fff');
      });
      // sign board (text is a DOM overlay)
      P(121, 6, 78, 26, '#8a5a35'); P(123, 8, 74, 22, '#b98b5e');
      // plants, couch, coffee corner
      const plant = (x, y) => { P(x + 2, y + 10, 8, 8, '#c0714a'); P(x + 1, y + 4, 10, 7, '#3fae6a'); P(x + 3, y, 6, 6, '#58c783'); P(x + 5, y + 6, 2, 5, '#2f8f55'); };
      plant(4, 60); plant(306, 60); plant(6, 190); plant(300, 190);
      P(104, 190, 64, 18, OUTLINE); P(105, 191, 62, 16, '#f2a56b'); P(105, 195, 62, 12, '#f7b883'); P(108, 188, 20, 6, '#f7c9a1'); P(144, 188, 20, 6, '#f7c9a1');
      P(176, 198, 16, 8, OUTLINE); P(177, 199, 14, 4, '#e7c9a0'); P(177, 203, 14, 2, '#cfa56f');
      P(238, 184, 22, 24, OUTLINE); P(239, 185, 20, 22, '#cfd6e2'); P(242, 188, 14, 6, '#56627c'); P(246, 198, 6, 6, '#ff7a59'); P(236, 207, 26, 2, '#cfa56f');
    }
  }
  return Office;
})();
