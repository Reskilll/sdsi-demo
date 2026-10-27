<template>
  <div class="app">
    <aside class="side">
      <div class="brand"><b>EBC</b><span>External Business Center</span></div>
      <nav class="nav">
        <div class="sec s0">Work</div>
        <router-link to="/">Dashboard<span class="n" v-if="alerts">{{ alerts }}</span></router-link>
        <router-link to="/pipeline">Pipeline</router-link>
        <div class="sec s2">Money</div>
        <router-link to="/bid-check">Bid Check</router-link>
        <div class="sec s3">Intelligence</div>
        <router-link to="/learnings">Learnings</router-link>
      </nav>
      <div class="foot">
        <button class="btn small" @click="toggleTheme">{{ theme === 'dark' ? '☀ Light' : '🌙 Dark' }}</button>
      </div>
    </aside>
    <main class="main">
      <router-view @refresh="loadAlerts" />
    </main>
    <div class="toast" v-if="toastMsg" role="status">{{ toastMsg }}</div>
  </div>
</template>

<script>
import { ref, provide, onMounted } from 'vue'
import api from './api/index.js'

export default {
  name: 'App',
  setup() {
    const toastMsg = ref('')
    const alerts = ref(0)
    const theme = ref('dark')

    const toast = (msg) => { toastMsg.value = msg; setTimeout(() => toastMsg.value = '', 2600) }
    provide('toast', toast)
    provide('api', api)

    const loadAlerts = () => {
      api.getDashboard().then(r => {
        if (r.data.openCount > 0) alerts.value = r.data.openCount
      }).catch(() => alerts.value = 0)
    }

    const toggleTheme = () => {
      theme.value = theme.value === 'dark' ? 'light' : 'dark'
      document.documentElement.setAttribute('data-theme', theme.value)
    }

    onMounted(() => { loadAlerts(); document.documentElement.setAttribute('data-theme', 'dark') })

    return { toastMsg, alerts, theme, toggleTheme }
  }
}
</script>
