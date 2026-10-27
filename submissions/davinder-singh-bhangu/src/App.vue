<template>
  <div class="app">
    <header class="app-header">
      <h1>🕐 IT Service-Desk SLA Tracker</h1>
      <p class="subtitle">Compute SLA breaches for support tickets — business hours, holidays &amp; hold-aware</p>
    </header>

    <section class="controls">
      <div class="control-group">
        <label class="control-label">Load Sample Data</label>
        <div class="button-row">
          <button
            v-for="opt in sampleOptions"
            :key="opt.key"
            :class="['btn', currentSample === opt.key ? 'btn-active' : 'btn-outline']"
            @click="loadSample(opt.key)"
          >
            {{ opt.label }}
          </button>
        </div>
      </div>

      <div class="control-group">
        <label class="control-label">Or Upload Custom Files</label>
        <div class="upload-row">
          <label class="btn btn-outline file-label">
            Tickets
            <input type="file" accept=".json" @change="e => uploadFile('tickets', e)" hidden />
          </label>
          <label class="btn btn-outline file-label">
            SLA Policy
            <input type="file" accept=".json" @change="e => uploadFile('policy', e)" hidden />
          </label>
          <label class="btn btn-outline file-label">
            Holidays
            <input type="file" accept=".json" @change="e => uploadFile('holidays', e)" hidden />
          </label>
        </div>
        <div class="file-status" v-if="fileStatus">
          <span v-for="(v, k) in fileStatus" :key="k" :class="v === 'loaded' ? 'status-ok' : 'status-pending'">
            {{ k }}: {{ v }}
          </span>
        </div>
      </div>

      <button class="btn btn-primary" @click="compute" :disabled="!ready">
        Compute SLA
      </button>
    </section>

    <section v-if="computed" class="results">
      <TicketTable :tickets="results" />
      <SummaryPanel :prioritySummary="summary.prioritySummary" :groupSummary="summary.groupSummary" />
    </section>

    <section v-else-if="loading" class="loading">Computing SLA results…</section>

    <footer class="app-footer">
      <p>SLA targets: P1=4h &middot; P2=8h &middot; P3=24h &middot; P4=72h (business hours Mon–Fri 09:00–18:00, excluding holidays)</p>
    </footer>
  </div>
</template>

<script>
import { computeSLA, computeSummary } from './utils/slaEngine.js';
import TicketTable from './components/TicketTable.vue';
import SummaryPanel from './components/SummaryPanel.vue';

const SAMPLES = {
  default: { tickets: '/tickets.json', policy: '/sla_policy.json', holidays: '/holidays.json' },
};

export default {
  name: 'App',
  components: { TicketTable, SummaryPanel },
  data() {
    return {
      ticketsData: null,
      slaPolicy: null,
      holidays: null,
      results: null,
      summary: null,
      computed: false,
      loading: false,
      currentSample: 'default',
      fileStatus: null,
      sampleOptions: [
        { key: 'default', label: 'Default' },
      ],
    };
  },
  computed: {
    ready() {
      return this.ticketsData && this.slaPolicy && this.holidays;
    },
  },
  methods: {
    async loadSample(key) {
      this.currentSample = key;
      this.fileStatus = null;
      this.computed = false;
      const sample = SAMPLES[key];
      try {
        const [ticketsRes, policyRes, holidaysRes] = await Promise.all([
          fetch(sample.tickets),
          fetch(sample.policy),
          fetch(sample.holidays),
        ]);
        this.ticketsData = await ticketsRes.json();
        this.slaPolicy = await policyRes.json();
        this.holidays = await holidaysRes.json();
      } catch (e) {
        console.error('Failed to load sample data', e);
      }
    },
    uploadFile(type, event) {
      const file = event.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => {
        try {
          const data = JSON.parse(reader.result);
          if (type === 'tickets') this.ticketsData = data;
          else if (type === 'policy') this.slaPolicy = data;
          else if (type === 'holidays') this.holidays = data;
          if (!this.fileStatus) this.fileStatus = {};
          this.fileStatus[type] = 'loaded';
          this.computed = false;
        } catch (e) {
          if (!this.fileStatus) this.fileStatus = {};
          this.fileStatus[type] = 'parse error';
        }
      };
      reader.readAsText(file);
    },
    compute() {
      if (!this.ready) return;
      this.loading = true;
      // Small delay so the loading state renders
      setTimeout(() => {
        try {
          this.results = this.ticketsData.map(ticket => {
            const sla = computeSLA(ticket, this.slaPolicy, this.holidays);
            return {
              id: ticket.id,
              priority: ticket.priority,
              assigneeGroup: ticket.assigneeGroup,
              createdAt: ticket.createdAt,
              resolvedAt: ticket.resolvedAt,
              elapsedMin: sla.elapsedMin,
              targetMin: sla.targetMin,
              dueBy: sla.dueBy,
              breach: sla.breach,
              breachMin: sla.breachMin,
            };
          });
          this.summary = computeSummary(this.results);
          this.computed = true;
        } catch (e) {
          console.error('SLA computation error', e);
        } finally {
          this.loading = false;
        }
      }, 50);
    },
  },
  async mounted() {
    await this.loadSample('default');
  },
};
</script>

<style>
/* ---- Reset & Tokens ---- */
*,
*::before,
*::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

:root {
  --bg: #f5f6fa;
  --surface: #ffffff;
  --text: #1a1a2e;
  --text-secondary: #6b7280;
  --border: #e5e7eb;
  --brand: #4f46e5;
  --brand-hover: #4338ca;
  --breach: #dc2626;
  --breach-bg: #fef2f2;
  --ok: #16a34a;
  --ok-bg: #f0fdf4;
  --warn: #ea580c;
  --radius: 8px;
  --shadow: 0 1px 3px rgba(0, 0, 0, 0.08), 0 1px 2px rgba(0, 0, 0, 0.06);
}

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
}

.app {
  max-width: 1280px;
  margin: 0 auto;
  padding: 24px 16px;
}

/* ---- Header ---- */
.app-header {
  text-align: center;
  margin-bottom: 32px;
}
.app-header h1 {
  font-size: 2rem;
  font-weight: 700;
  letter-spacing: -0.02em;
}
.subtitle {
  color: var(--text-secondary);
  margin-top: 4px;
}

/* ---- Controls ---- */
.controls {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px;
  margin-bottom: 32px;
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: flex-end;
  box-shadow: var(--shadow);
}
.control-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.control-label {
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-secondary);
}
.button-row,
.upload-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.btn {
  display: inline-flex;
  align-items: center;
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.15s ease;
}
.btn-primary {
  background: var(--brand);
  color: #fff;
}
.btn-primary:hover { background: var(--brand-hover); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-active {
  background: var(--brand);
  color: #fff;
}
.btn-outline {
  background: var(--surface);
  border-color: var(--border);
  color: var(--text);
}
.btn-outline:hover {
  border-color: var(--brand);
  color: var(--brand);
}
.file-label {
  cursor: pointer;
}
.file-status {
  display: flex;
  gap: 12px;
  font-size: 0.8rem;
}
.status-ok { color: var(--ok); }
.status-pending { color: var(--text-secondary); }

/* ---- Loading ---- */
.loading {
  text-align: center;
  padding: 48px;
  color: var(--text-secondary);
  font-size: 1.1rem;
}

/* ---- Footer ---- */
.app-footer {
  text-align: center;
  margin-top: 48px;
  padding-top: 16px;
  border-top: 1px solid var(--border);
  color: var(--text-secondary);
  font-size: 0.8rem;
}
</style>