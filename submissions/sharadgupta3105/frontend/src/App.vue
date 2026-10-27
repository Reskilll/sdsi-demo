<script setup>
</script>

<template>
  <header class="topbar">
    <router-link to="/" class="brand">🔗 Shortly</router-link>
  </header>
  <main class="page">
    <router-view />
  </main>
</template>

<style>
:root {
  color-scheme: light dark;
  --bg: #f6f7f9;
  --card: #ffffff;
  --text: #1f2430;
  --muted: #6b7280;
  --accent: #2563eb;
  --danger: #dc2626;
  --border: #e5e7eb;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #111827;
    --card: #1f2937;
    --text: #f3f4f6;
    --muted: #9ca3af;
    --accent: #60a5fa;
    --danger: #f87171;
    --border: #374151;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  background: var(--bg);
  color: var(--text);
}
.topbar {
  padding: 16px 24px;
  border-bottom: 1px solid var(--border);
}
.brand {
  font-weight: 700;
  font-size: 18px;
  text-decoration: none;
  color: var(--text);
}
.page {
  max-width: 720px;
  margin: 0 auto;
  padding: 32px 24px;
}
.card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 24px;
}
h1 { font-size: 22px; margin: 0 0 8px; }
.muted { color: var(--muted); font-size: 14px; }
.row { display: flex; gap: 12px; flex-wrap: wrap; }
input, button {
  font: inherit;
  padding: 10px 14px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--card);
  color: var(--text);
}
input { flex: 1 1 260px; }
button {
  background: var(--accent);
  color: #fff;
  border: none;
  cursor: pointer;
}
button:disabled { opacity: 0.6; cursor: not-allowed; }
.error { color: var(--danger); margin-top: 12px; font-size: 14px; }
.result { margin-top: 16px; }
.result a { color: var(--accent); word-break: break-all; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 12px; margin: 16px 0; }
.stat { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 14px; text-align: center; }
.stat .value { font-size: 24px; font-weight: 700; }
.stat .label { font-size: 12px; color: var(--muted); }
table { width: 100%; border-collapse: collapse; margin-top: 16px; }
th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--border); font-size: 14px; }
</style>
