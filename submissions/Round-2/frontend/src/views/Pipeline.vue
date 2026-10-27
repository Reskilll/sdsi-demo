<template>
  <div>
    <div class="top">
      <div><h1>Pipeline</h1><p>Every external opportunity, where it stands and who owns it.</p></div>
      <button class="btn primary" @click="showNew=true">New Opportunity</button>
    </div>

    <!-- New Opp Form -->
    <div class="ov" v-if="showNew" @click.self="showNew=false">
      <div class="dlg">
        <h2>New Opportunity</h2>
        <div class="fg">
          <label class="f">Client<input type="text" v-model="form.clientId" placeholder="Client name"></label>
          <label class="f">What are they buying?<input type="text" v-model="form.title" placeholder="Service name"></label>
          <label class="f">Business Model<select v-model="form.businessModel"><option v-for="m in models" :key="m">{{ m }}</option></select></label>
          <label class="f">Region<select v-model="form.region"><option v-for="r in regions" :key="r">{{ r }}</option></select></label>
          <label class="f">Source<select v-model="form.source"><option v-for="s in sources" :key="s">{{ s }}</option></select></label>
          <label class="f">Leader<select v-model="form.leaderId"><option v-for="l in leaders" :key="l.id" :value="l.id">{{ l.name }}</option></select></label>
          <label class="f">Value (₹ lakh)<input type="number" v-model.number="form.valueLakh" min="5"></label>
        </div>
        <div class="acts">
          <button class="btn ghost" @click="showNew=false">Cancel</button>
          <button class="btn primary" @click="createOpp">Add to Pipeline</button>
        </div>
      </div>
    </div>

    <!-- Close Form -->
    <div class="ov" v-if="closing" @click.self="closing=null">
      <div class="dlg">
        <h2>Close: {{ closing.title }}</h2>
        <select v-model="closeOutcome" class="full" style="width:100%;margin:8px 0">
          <option value="won">Brought in</option>
          <option value="lost">Missed</option>
          <option value="dropped">Paused</option>
        </select>
        <textarea v-model="closeLesson" rows="3" placeholder="Lesson learned..." style="width:100%;margin:8px 0"></textarea>
        <div class="acts">
          <button class="btn ghost" @click="closing=null">Cancel</button>
          <button class="btn primary" @click="doClose">Save Review</button>
        </div>
      </div>
    </div>

    <!-- Kanban -->
    <div class="kan">
      <div class="col" v-for="(stage,i) in stages" :key="i">
        <h3>{{ stage }}<span>{{ getStage(i).length }} &middot; &amp;#8377;{{ stageValue(i) }} L</span></h3>
        <button class="card" v-for="opp in getStage(i)" :key="opp.id" style="width:100%">
          <div class="c">{{ opp.title }}</div>
          <div class="t">ID: {{ opp.id }}</div>
          <div class="m"><b>&amp;#8377;{{ opp.valueLakh }} L</b><span>{{ opp.leaderId }}</span></div>
          <div class="w">
            <span class="chip acc">{{ opp.source }}</span>
            <button class="btn small" @click.stop="advance(opp.id)" v-if="opp.stage < 3">Advance</button>
            <button class="btn small lost" @click.stop="openClose(opp)">Close</button>
          </div>
        </button>
        <div class="empty" v-if="getStage(i).length===0">No deals here.</div>
      </div>
    </div>

    <!-- Closed -->
    <div class="panel flat mt">
      <div style="padding:16px 20px 4px"><h2>Recently Closed</h2></div>
      <div class="scroll"><table>
        <thead><tr><th>Title</th><th>Outcome</th><th>Value</th><th>Closed</th></tr></thead>
        <tbody>
          <tr v-for="opp in closed" :key="opp.id">
            <td>{{ opp.title }}</td>
            <td><span class="chip" :class="opp.status==='won'?'won':opp.status==='lost'?'lost':''">{{ opp.status }}</span></td>
            <td>&amp;#8377;{{ opp.valueLakh }} L</td>
            <td>{{ opp.closeDate ? opp.closeDate.slice(0,10) : '-' }}</td>
          </tr>
        </tbody>
      </table></div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, inject } from 'vue'
export default {
  name: 'Pipeline',
  setup() {
    const api = inject('api')
    const toast = inject('toast')
    const stages = ['Lead generation','RFP received','Go/No-Go','Proposal submitted']
    const sources = ['Leader network','Client portal','Referral','Repeat client','Cold outreach','Partner']
    const regions = ['North America','Europe','Asia-Pacific','Middle East']
    const models = ['Offshore','Software Development','Infra','Security']
    const leaders = [
      {id:'L1',name:'Anita Rao'},{id:'L2',name:'Rohit Verma'},{id:'L5',name:'Priya Menon'},
      {id:'L6',name:'Sanjay Iyer'},{id:'L7',name:'Divya Kapoor'},{id:'L9',name:'Neha Gupta'}
    ]

    const opportunities = ref([])
    const closed = ref([])
    const showNew = ref(false)
    const closing = ref(null)
    const closeOutcome = ref('won')
    const closeLesson = ref('')
    const form = ref({ clientId:'', title:'', businessModel:'Offshore', region:'Europe', source:'Leader network', leaderId:'L5', valueLakh:150 })

    const load = async () => {
      try { const r = await api.getPipeline(); const s = r.data.stages;
        opportunities.value = Object.values(s).flat(); closed.value = r.data.closed || []; }
      catch(e) { console.error(e) }
    }
    const getStage = (i) => opportunities.value.filter(o => o.stage === i)
    const stageValue = (i) => getStage(i).reduce((s,o) => s + (o.valueLakh||0), 0)

    const createOpp = async () => {
      try {
        await api.createOpportunity({
          id: 'OPP-' + (2000 + Math.floor(Math.random()*9000)),
          leaderId: form.value.leaderId, clientId: 1, source: form.value.source,
          businessModel: form.value.businessModel, pricing: 'Monthly rate per resource',
          valueLakh: form.value.valueLakh, title: form.value.title, status: 'open',
          stage: 0, reached: 0, createdAt: new Date().toISOString(),
          expectedClose: new Date(Date.now() + 90*86400000).toISOString()
        })
        showNew.value = false
        toast(form.value.title + ' added to pipeline')
        load()
      } catch(e) { toast('Error: ' + e.message) }
    }

    const advance = async (id) => {
      try { await api.advanceStage(id); toast('Advanced to next stage'); load() } catch(e) { toast(e.message) }
    }

    const openClose = (opp) => { closing.value = opp; closeOutcome.value = 'won'; closeLesson.value = '' }
    const doClose = async () => {
      try {
        await api.closeOpportunity(closing.value.id, { outcome: closeOutcome.value,
          reasons: ['Competitive pricing'], competitor: '', lesson: closeLesson.value || 'No lesson recorded.' })
        closing.value = null; toast('Review saved'); load()
      } catch(e) { toast(e.message) }
    }

    onMounted(load)
    return { stages, sources, regions, models, leaders, opportunities, closed, showNew, form, closing, closeOutcome, closeLesson,
      getStage, stageValue, createOpp, advance, openClose, doClose }
  }
}
</script>
