<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { fetchStats } from '../api.js';

const route = useRoute();
const code = computed(() => route.params.code);
const loading = ref(true);
const error = ref('');
const stats = ref(null);

onMounted(async () => {
  try {
    stats.value = await fetchStats(code.value);
  } catch (e) {
    error.value = e.message;
  } finally {
    loading.value = false;
  }
});

const days = computed(() => Object.entries(stats.value?.clicksPerDay ?? {}));
</script>

<template>
  <section>
    <h1>Analytics</h1>
    <p class="muted" v-if="stats">Code: <code>{{ stats.code }}</code></p>

    <div v-if="loading" class="muted">Loading…</div>
    <p v-else-if="error" class="error">{{ error }}</p>

    <template v-else-if="stats">
      <div class="card">
        <p class="muted">Destination</p>
        <p><a :href="stats.url" target="_blank" rel="noopener">{{ stats.url }}</a></p>
        <div class="grid">
          <div class="stat"><div class="value">{{ stats.totalClicks }}</div><div class="label">Total clicks</div></div>
          <div class="stat">
            <div class="value">{{ stats.lastAccessedAt ? new Date(stats.lastAccessedAt).toLocaleString() : '—' }}</div>
            <div class="label">Last accessed</div>
          </div>
        </div>
      </div>

      <div class="card" style="margin-top: 16px;">
        <h1 style="font-size: 16px;">Clicks per day</h1>
        <table v-if="days.length">
          <thead><tr><th>Date</th><th>Clicks</th></tr></thead>
          <tbody>
            <tr v-for="[day, clicks] in days" :key="day">
              <td>{{ day }}</td><td>{{ clicks }}</td>
            </tr>
          </tbody>
        </table>
        <p v-else class="muted">No clicks recorded yet.</p>
      </div>
    </template>
  </section>
</template>
