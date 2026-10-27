<template>
  <div class="app">
    <header class="app-header">
      <h1>URL Shortener</h1>
      <p class="subtitle">Shorten, resolve, and see how your links are used.</p>
    </header>

    <section class="panel">
      <h2>Shorten a URL</h2>
      <form @submit.prevent="shorten">
        <input v-model="url" type="url" placeholder="https://example.com/some/long/path" class="input" />
        <div class="row">
          <input v-model="alias" type="text" placeholder="custom alias (optional)" class="input grow" />
          <input v-model="ttl" type="number" min="0" placeholder="ttl seconds (optional)" class="input grow" />
        </div>
        <button type="submit" :disabled="busy" class="btn">Shorten</button>
        <p v-if="error" class="error">{{ error }}</p>
      </form>

      <div v-if="result" class="result">
        <p>Short URL:</p>
        <a :href="result.shortUrl" target="_blank" rel="noopener" class="short-link">{{ result.shortUrl }}</a>
        <p class="code-line">
          code <code>{{ result.code }}</code>
          <span v-if="result.custom" class="tag">custom</span>
          <span v-if="result.expiresAt" class="tag expired">expires {{ new Date(result.expiresAt).toLocaleString() }}</span>
        </p>
        <button @click="loadStats(result.code)" class="btn secondary">View stats</button>
      </div>
    </section>

    <section class="panel" v-if="stats">
      <h2>Stats for <code>{{ stats.code }}</code></h2>
      <p>Total clicks: <strong>{{ stats.totalClicks }}</strong></p>
      <p v-if="stats.lastAccessedAt">Last accessed: {{ new Date(stats.lastAccessedAt).toLocaleString() }}</p>
      <table v-if="stats.clicksPerDay.length" class="table">
        <thead>
          <tr><th>Day</th><th>Clicks</th></tr>
        </thead>
        <tbody>
          <tr v-for="row in stats.clicksPerDay" :key="row.day">
            <td>{{ row.day }}</td>
            <td>{{ row.count }}</td>
          </tr>
        </tbody>
      </table>
      <p v-else class="muted">No clicks yet.</p>
    </section>
  </div>
</template>

<script>
export default {
  name: 'App',
  data() {
    return {
      url: '',
      alias: '',
      ttl: '',
      busy: false,
      result: null,
      stats: null,
      error: '',
    };
  },
  methods: {
    async shorten() {
      this.busy = true;
      this.error = '';
      this.result = null;
      this.stats = null;
      try {
        const payload = { url: this.url };
        if (this.alias) payload.alias = this.alias;
        if (this.ttl !== '' && this.ttl !== null) payload.ttl = Number(this.ttl);
        const res = await fetch('/api/shorten', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
        this.result = data;
      } catch (e) {
        this.error = e.message;
      } finally {
        this.busy = false;
      }
    },
    async loadStats(code) {
      this.error = '';
      try {
        const res = await fetch(`/api/stats/${code}`);
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
        this.stats = data;
      } catch (e) {
        this.error = e.message;
      }
    },
  },
};
</script>

<style>
:root {
  --bg: #f7f8fa;
  --panel: #ffffff;
  --ink: #1f2430;
  --muted: #6b7280;
  --accent: #2563eb;
  --error: #dc2626;
  --border: #e5e7eb;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink); font-family: system-ui, -apple-system, sans-serif; }
.app { max-width: 720px; margin: 0 auto; padding: 2rem 1rem; }
.app-header h1 { margin: 0 0 0.25rem; }
.subtitle { color: var(--muted); margin: 0 0 1.5rem; }
.panel { background: var(--panel); border: 1px solid var(--border); border-radius: 10px; padding: 1.25rem; margin-bottom: 1.25rem; }
.panel h2 { margin: 0 0 1rem; font-size: 1.1rem; }
.input { width: 100%; padding: 0.6rem 0.7rem; border: 1px solid var(--border); border-radius: 6px; margin-bottom: 0.75rem; font-size: 1rem; }
.row { display: flex; gap: 0.75rem; }
.grow { flex: 1; }
.btn { background: var(--accent); color: #fff; border: none; padding: 0.6rem 1.2rem; border-radius: 6px; font-size: 1rem; cursor: pointer; }
.btn:disabled { opacity: 0.6; cursor: not-allowed; }
.btn.secondary { background: transparent; color: var(--accent); border: 1px solid var(--accent); }
.error { color: var(--error); margin: 0.75rem 0 0; }
.result { margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--border); }
.short-link { color: var(--accent); font-weight: 600; word-break: break-all; }
.code-line { color: var(--muted); font-size: 0.9rem; }
.tag { display: inline-block; margin-left: 0.5rem; padding: 0.1rem 0.45rem; border-radius: 999px; background: #eef2ff; color: var(--accent); font-size: 0.75rem; }
.tag.expired { background: #fef2f2; color: var(--error); }
.table { width: 100%; border-collapse: collapse; margin-top: 0.5rem; }
.table th, .table td { text-align: left; padding: 0.4rem 0.5rem; border-bottom: 1px solid var(--border); }
.muted { color: var(--muted); }
</style>