<script setup>
import { ref } from 'vue';
import { shorten } from '../api.js';

const url = ref('');
const customAlias = ref('');
const expiresAt = ref('');
const loading = ref(false);
const error = ref('');
const result = ref(null);

async function submit() {
  error.value = '';
  result.value = null;
  loading.value = true;
  try {
    const payload = { url: url.value.trim() };
    if (customAlias.value.trim()) payload.customAlias = customAlias.value.trim();
    if (expiresAt.value) payload.expiresAt = expiresAt.value;
    result.value = await shorten(payload);
  } catch (e) {
    error.value = e.message;
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <section>
    <h1>Shorten a URL</h1>
    <p class="muted">Paste a long link, get a short code back with click analytics.</p>

    <form class="card" @submit.prevent="submit">
      <input v-model="url" type="url" placeholder="https://example.com/very/long/path" autofocus required />
      <div class="row" style="margin-top: 12px;">
        <input v-model="customAlias" placeholder="Custom alias (optional)" maxlength="64" />
        <input v-model="expiresAt" type="datetime-local" title="Expiry (optional)" />
      </div>
      <div class="row" style="margin-top: 16px;">
        <button type="submit" :disabled="loading">{{ loading ? 'Shortening…' : 'Shorten' }}</button>
      </div>
      <p v-if="error" class="error">{{ error }}</p>
      <div v-if="result" class="result">
        <p>Short URL: <a :href="result.shortUrl" target="_blank" rel="noopener">{{ result.shortUrl }}</a></p>
        <p class="muted">
          <router-link :to="`/stats/${result.code}`">View analytics →</router-link>
        </p>
      </div>
    </form>
  </section>
</template>
