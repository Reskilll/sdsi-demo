<template>
  <div class="ticket-table-wrapper">
    <h2>Tickets &mdash; SLA Results</h2>
    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Ticket</th>
            <th>Priority</th>
            <th>Group</th>
            <th>Created</th>
            <th>Resolved</th>
            <th>Elapsed (min)</th>
            <th>Target (min)</th>
            <th>Due By</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="t in tickets" :key="t.id" :class="{ 'row-breach': t.breach, 'row-open': !t.resolvedAt }">
            <td class="ticket-id">{{ t.id }}</td>
            <td><span :class="`badge badge-${t.priority.toLowerCase()}`">{{ t.priority }}</span></td>
            <td>{{ t.assigneeGroup }}</td>
            <td>{{ fmt(t.createdAt) }}</td>
            <td>{{ t.resolvedAt ? fmt(t.resolvedAt) : '—' }}</td>
            <td class="num">{{ t.elapsedMin.toLocaleString() }}</td>
            <td class="num">{{ t.targetMin }}</td>
            <td>{{ fmt(t.dueBy) }}</td>
            <td>
              <span v-if="!t.resolvedAt" class="tag tag-open">Open</span>
              <span v-else-if="t.breach" class="tag tag-breach">Breach {{ t.breachMin }} min</span>
              <span v-else class="tag tag-ok">Met</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
export default {
  name: 'TicketTable',
  props: {
    tickets: { type: Array, required: true },
  },
  methods: {
    fmt(d) {
      if (!d) return '';
      const date = new Date(d);
      return date.toLocaleString('en-IN', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      });
    },
  },
};
</script>

<style scoped>
.ticket-table-wrapper {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px;
  margin-bottom: 24px;
  box-shadow: var(--shadow);
}
.ticket-table-wrapper h2 {
  font-size: 1.15rem;
  font-weight: 600;
  margin-bottom: 16px;
}
.table-scroll {
  overflow-x: auto;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}
th {
  text-align: left;
  padding: 10px 12px;
  font-weight: 600;
  color: var(--text-secondary);
  border-bottom: 2px solid var(--border);
  white-space: nowrap;
}
td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}
.ticket-id {
  font-weight: 600;
  font-family: 'SF Mono', 'Fira Code', monospace;
}
.num {
  font-variant-numeric: tabular-nums;
  text-align: right;
}

/* Row states */
.row-breach {
  background: var(--breach-bg);
}
.row-open {
  background: #fffbeb;
}

/* Badges */
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

/* Tags */
.tag {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
}
.tag-breach { background: var(--breach-bg); color: var(--breach); }
.tag-ok { background: var(--ok-bg); color: var(--ok); }
.tag-open { background: #fef3c7; color: #92400e; }
</style>