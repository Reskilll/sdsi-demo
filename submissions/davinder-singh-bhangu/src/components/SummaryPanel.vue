<template>
  <div class="summary-grid">
    <!-- By Priority -->
    <div class="summary-card">
      <h2>Breach % by Priority</h2>
      <table class="summary-table">
        <thead>
          <tr>
            <th>Priority</th>
            <th>Total</th>
            <th>Breached</th>
            <th>Breach %</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in prioritySummary" :key="row.priority">
            <td><span :class="`badge badge-${row.priority.toLowerCase()}`">{{ row.priority }}</span></td>
            <td class="num">{{ row.total }}</td>
            <td class="num">{{ row.breached }}</td>
            <td class="num">
              <span :class="pctClass(row.breachPct)">{{ row.breachPct }}%</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- By Group -->
    <div class="summary-card">
      <h2>Breach % by Assignee Group</h2>
      <table class="summary-table">
        <thead>
          <tr>
            <th>Group</th>
            <th>Total</th>
            <th>Breached</th>
            <th>Breach %</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in groupSummary" :key="row.group">
            <td class="group-name">{{ row.group }}</td>
            <td class="num">{{ row.total }}</td>
            <td class="num">{{ row.breached }}</td>
            <td class="num">
              <span :class="pctClass(row.breachPct)">{{ row.breachPct }}%</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
export default {
  name: 'SummaryPanel',
  props: {
    prioritySummary: { type: Array, required: true },
    groupSummary: { type: Array, required: true },
  },
  methods: {
    pctClass(pct) {
      if (pct > 50) return 'pct-high';
      if (pct > 0) return 'pct-mid';
      return 'pct-ok';
    },
  },
};
</script>

<style scoped>
.summary-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}
@media (max-width: 768px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }
}

.summary-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px;
  box-shadow: var(--shadow);
}
.summary-card h2 {
  font-size: 1.05rem;
  font-weight: 600;
  margin-bottom: 12px;
}

.summary-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}
.summary-table th {
  text-align: left;
  padding: 8px 10px;
  border-bottom: 2px solid var(--border);
  color: var(--text-secondary);
  font-weight: 600;
}
.summary-table td {
  padding: 8px 10px;
  border-bottom: 1px solid var(--border);
}
.num {
  font-variant-numeric: tabular-nums;
  text-align: right;
}
.group-name {
  font-weight: 500;
}

/* Badge reuse */
.badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
}
.badge-p1 { background: #fee2e2; color: #991b1b; }
.badge-p2 { background: #fed7aa; color: #9a3412; }
.badge-p3 { background: #fef3c7; color: #92400e; }
.badge-p4 { background: #dbeafe; color: #1e40af; }

/* Percentage colour */
.pct-high { color: var(--breach); font-weight: 600; }
.pct-mid { color: var(--warn); font-weight: 600; }
.pct-ok { color: var(--ok); font-weight: 600; }
</style>