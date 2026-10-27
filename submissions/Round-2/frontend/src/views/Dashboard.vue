<template>
  <div>
    <section class="hero panel">
      <div>
        <span class="live"><i></i>Live</span>
        <h1>{{ stats.wonCount }} brought to Samsung. {{ stats.totalOpportunities }} opportunities pursued.</h1>
        <p>{{ stats.totalWonValue }} lakh won. {{ stats.openCount }} open deals. {{ Math.round(stats.winRate * 100) }}% bring-in rate.</p>
        <div class="row-f" style="margin-top:18px">
          <router-link to="/pipeline" class="btn primary">Pipeline</router-link>
          <router-link to="/bid-check" class="btn">Bid Check</router-link>
        </div>
      </div>
    </section>

    <div class="kpis mt">
      <div class="kpi"><div class="l">Open Pipeline</div><div class="v">₹{{ stats.totalOpenValue }} L</div><div class="s">{{ stats.openCount }} deals</div></div>
      <div class="kpi"><div class="l">Brought in</div><div class="v">₹{{ stats.totalWonValue }} L</div><div class="s">{{ stats.wonCount }} projects</div></div>
      <div class="kpi"><div class="l">Bring-in Rate</div><div class="v">{{ Math.round(stats.winRate * 100) }}%</div><div class="s">{{ stats.wonCount }} of {{ stats.wonCount + stats.lostCount }} decided</div></div>
      <div class="kpi"><div class="l">Weighted Pipeline</div><div class="v">₹{{ Math.round(stats.weightedPipeline) }} L</div><div class="s">Stage-weighted</div></div>
    </div>

    <div class="grid g2 mt">
      <div class="panel"><h2>Source Performance</h2><div style="margin-top:8px" v-if="sources">
        <div v-for="(s,k) in sources" :key="k" style="display:flex;align-items:center;gap:10px;padding:4px 0">
          <span style="width:100px">{{ k }}</span>
          <span class="barbg"><span class="bar" :style="{width: s.rate*100+'%'}"></span></span>
          <b>{{ Math.round(s.rate*100) }}%</b>
        </div>
      </div></div>
      <div class="panel"><h2>Quick Actions</h2>
        <div style="margin-top:10px;display:flex;flex-direction:column;gap:8px">
          <router-link to="/pipeline" class="btn">View Pipeline</router-link>
          <router-link to="/bid-check" class="btn primary">Run Bid Check</router-link>
          <router-link to="/learnings" class="btn">View Learnings</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, inject } from 'vue'
export default {
  name: 'Dashboard',
  setup() {
    const api = inject('api')
    const stats = ref({ wonCount:0, lostCount:0, openCount:0, totalOpportunities:0, totalWonValue:0, totalOpenValue:0, winRate:0, weightedPipeline:0 })
    const sources = ref(null)
    onMounted(async () => {
      try { const r = await api.getDashboard(); stats.value = r.data; const s = await api.getSourceStats(); sources.value = s.data; }
      catch(e) { console.error(e) }
    })
    return { stats, sources }
  }
}
</script>
