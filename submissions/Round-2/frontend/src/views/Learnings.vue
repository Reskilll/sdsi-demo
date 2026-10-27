<template>
  <div>
    <div class="top"><div><h1>Learnings from closed bids</h1><p>Search reviews. Filter by outcome and region.</p></div></div>
    <div class="panel mt">
      <div class="row-f">
        <input type="text" v-model="query" placeholder="Search reviews..." style="flex:1;min-width:200px">
        <select v-model="filter"><option value="all">All outcomes</option><option value="won">Brought in</option><option value="lost">Missed</option></select>
      </div>
      <div v-if="filtered.length" style="margin-top:12px">
        <div class="lcard" v-for="o in filtered" :key="o.id">
          <div class="h"><span class="chip" :class="o.status==='won'?'won':'lost'">{{ o.status }}</span><b>{{ o.title || o.id }}</b></div>
          <p>{{ o.lesson || 'No review recorded.' }}</p>
          <div class="mt2">Leader: {{ o.leaderId }} &middot; Rs{{ o.valueLakh }} L &middot; {{ o.source }}</div>
        </div>
      </div>
      <div class="empty" v-if="filtered.length===0">No reviews match. Try different filters.</div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, inject } from 'vue'
export default {
  name: 'Learnings',
  setup() {
    const api = inject('api')
    const opportunities = ref([])
    const query = ref('')
    const filter = ref('all')
    onMounted(async () => {
      try { const r = await api.getOpportunities(); opportunities.value = r.data || [] }
      catch(e) { console.error(e) }
    })
    const filtered = computed(() => {
      return opportunities.value.filter(o =>
        (filter.value === 'all' || o.status === filter.value) &&
        (!query.value || ((o.title||'')+(o.lesson||'')+(o.leaderId||'')+(o.source||'')).toLowerCase().includes(query.value.toLowerCase()))
      ).slice(0, 30)
    })
    return { query, filter, filtered }
  }
}
</script>
