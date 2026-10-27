<template>
  <div>
    <div class="top"><div><h1>Should we bid?</h1><p>Check probability, margin and capacity before committing.</p></div></div>
    <div class="bidwrap">
      <div class="panel form">
        <label class="f">Business Model<select v-model="form.businessModel"><option v-for="m in models" :key="m">{{ m }}</option></select></label>
        <label class="f">Region<select v-model="form.region"><option v-for="r in regions" :key="r">{{ r }}</option></select></label>
        <label class="f">Source<select v-model="form.source"><option v-for="s in sources" :key="s">{{ s }}</option></select></label>
        <label class="f">Leader<select v-model="form.leaderId"><option v-for="l in leaders" :key="l.id" :value="l.id">{{ l.name }}</option></select></label>
        <label class="f">Deal Value (Rs lakh)<input type="number" v-model.number="form.value" min="25" max="2000"></label>
        <label class="f">Start Week from now<input type="number" v-model.number="form.start" min="0" max="10"></label>
        <label class="f">Duration (weeks)<input type="number" v-model.number="form.dur" min="6" max="78"></label>
        <label class="f">Price vs Standard (%)<input type="range" v-model.number="form.price" min="-15" max="10"> {{ form.price > 0 ? '+' : '' }}{{ form.price }}%</label>
        <button class="btn primary ai-btn" @click="check" style="margin-top:12px">Run Bid Check</button>
      </div>
      <div id="result">
        <div class="panel" v-if="result">
          <div class="gauge">
            <svg viewBox="0 0 220 130" style="width:220px">
              <path d="M20 110 A90 90 0 0 1 200 110" fill="none" stroke="var(--drop-soft)" stroke-width="18" stroke-linecap="round"/>
              <path d="M20 110 A90 90 0 0 1 200 110" fill="none" :stroke="verdictColor" stroke-width="18" stroke-linecap="round" :stroke-dasharray="(result.winProbability*100) + ' 100'"/>
              <text x="110" y="100" text-anchor="middle" font-size="40" font-weight="700" fill="var(--ink)">{{ Math.round(result.winProbability*100) }}%</text>
              <text x="110" y="124" text-anchor="middle" font-size="13" fill="var(--muted)">chance of landing it</text>
            </svg>
            <div style="flex:1">
              <div class="verdict" :class="verdictClass">{{ result.verdict }}</div>
              <p style="margin-top:8px">Margin: {{ Math.round(result.margin*100) }}%. Team average: {{ Math.round(result.teamAverage*100) }}%.</p>
            </div>
          </div>
        </div>
        <div class="empty" v-if="!result" style="margin-top:20px">Fill the form and run the bid check.</div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, inject } from 'vue'
export default {
  name: 'BidCheck',
  setup() {
    const api = inject('api')
    const models = ['Offshore','Software Development','Infra','Security']
    const regions = ['North America','Europe','Asia-Pacific','Middle East']
    const sources = ['Leader network','Client portal','Referral','Repeat client','Cold outreach','Partner']
    const leaders = [{id:'L1',name:'Anita Rao'},{id:'L2',name:'Rohit Verma'},{id:'L5',name:'Priya Menon'},{id:'L7',name:'Divya Kapoor'}]
    const form = ref({ businessModel:'Offshore', region:'Europe', source:'Referral', leaderId:'L5', value:150, start:3, dur:30, price:0 })
    const result = ref(null)
    const verdictClass = computed(() => {
      if (!result.value) return ''
      return result.value.verdict === 'Bid' ? 'Bid' : result.value.verdict.includes('condition') ? 'cond' : 'No'
    })
    const verdictColor = computed(() => result.value && result.value.verdict.startsWith('Bid') ? 'var(--won)' : 'var(--warn)')
    const check = async () => {
      try { const r = await api.getBidCheck(form.value); result.value = r.data }
      catch(e) { console.error(e) }
    }
    return { models, regions, sources, leaders, form, result, verdictClass, verdictColor, check }
  }
}
</script>
