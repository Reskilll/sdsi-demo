/**
 * KnoxFlow Frontend Application Logic
 */

// ======================================================
// THEME SYSTEM — runs before DOM paint to prevent flash
// ======================================================
(function initThemeEarly() {
  const saved = localStorage.getItem('knoxflow-theme') || 'dark';
  document.documentElement.setAttribute('data-theme', saved);
})();

function toggleTheme() {
  const html = document.documentElement;
  const current = html.getAttribute('data-theme') || 'dark';
  const next = current === 'dark' ? 'light' : 'dark';

  html.setAttribute('data-theme', next);
  localStorage.setItem('knoxflow-theme', next);
  state.currentTheme = next;

  updateThemeIcons(next);
  showToast(`Switched to ${next === 'dark' ? '🌙 Dark' : '☀️ Light'} theme`, 'info');
}

function updateThemeIcons(theme) {
  const moonIcon = document.getElementById('theme-icon-moon');
  const sunIcon = document.getElementById('theme-icon-sun');
  if (!moonIcon || !sunIcon) return;

  if (theme === 'dark') {
    moonIcon.style.display = '';
    sunIcon.style.display = 'none';
  } else {
    moonIcon.style.display = 'none';
    sunIcon.style.display = '';
  }
}

let state = {
  currentRole: 'manager',
  currentTheme: localStorage.getItem('knoxflow-theme') || 'dark',
  activeEmployeeId: 'emp_01',
  selectedFilter: 'all',
  selectedEmployeeFilter: null,
  searchQuery: '',
  team: [],
  emails: [],
  historicalKb: [],
  analytics: null
};

// External enterprise contacts catalog
const EXTERNAL_CONTACTS = [
  { id: 'ext_01', name: 'Marcus Vance', email: 'marcus.v@fintechcorp.com', org: 'FinTech Corp (Partner)' },
  { id: 'ext_02', name: 'Elena Rostova', email: 'elena.r@partner.com', org: 'Enterprise Cloud Client' },
  { id: 'ext_03', name: 'Dr. Aris Thorne', email: 'aris.t@quantumresearch.ai', org: 'Quantum Research AI' },
  { id: 'ext_04', name: 'NetOps Notification Bot', email: 'noreply-netops@knoxflow.io', org: 'Global NOC Operations' }
];

// Preset simulation data
const SIMULATION_PRESETS = {
  vpn: {
    subject: "CRITICAL: GlobalProtect VPN gateway timeout when connecting to Prod",
    sender_id: "ext_01",
    sender_name: "Marcus Vance",
    sender_email: "marcus.v@fintechcorp.com",
    suggested_assignee: "emp_01", // Sarah Connor - Network Specialist
    body: "Hi team, our remote engineers in London cannot reach the primary VPN portal. GlobalProtect client is reporting tunnel connection timeout and gateway unreachable. We have an active release waiting."
  },
  postgres: {
    subject: "URGENT: Staging PostgreSQL read-only credentials needed for sprint demo",
    sender_id: "ext_02",
    sender_name: "Elena Rostova",
    sender_email: "elena.r@partner.com",
    suggested_assignee: "emp_04", // David Kim - Database Analyst
    body: "Hello, I need temporary read-only access to the staging PostgreSQL analytics database to verify user migration data ahead of today's customer demo."
  },
  unseen_bug: {
    subject: "Memory leak detected in custom Rust worker service in namespace prod-inference",
    sender_id: "ext_03",
    sender_name: "Dr. Aris Thorne",
    sender_email: "aris.t@quantumresearch.ai",
    suggested_assignee: "emp_02", // Alex Mercer - DevOps / SRE
    body: "We noticed anomalous RSS memory inflation in worker node #3. The pod is OOM-killing every 45 minutes. This is a brand new service deployed yesterday with zero prior incident history."
  },
  gen_info: {
    subject: "Notification: Scheduled Core Switch Firmware Upgrade this Sunday at 02:00 UTC",
    sender_id: "ext_04",
    sender_name: "NetOps Notification Bot",
    sender_email: "noreply-netops@knoxflow.io",
    suggested_assignee: "emp_03", // Priya Sharma - Support Lead
    body: "This is a broadcast maintenance notice. Core datacenter switches in region US-East will undergo redundant firmware upgrades this Sunday between 02:00 and 04:00 UTC. No action required."
  },
  custom: {
    subject: "",
    sender_id: "custom",
    sender_name: "",
    sender_email: "",
    suggested_assignee: "auto",
    body: ""
  }
};

// Initialize Application
document.addEventListener('DOMContentLoaded', () => {
  updateThemeIcons(state.currentTheme);
  fetchData();
  // Polling every 15 seconds to update aging live
  setInterval(fetchData, 15000);
});

async function fetchData() {
  try {
    const res = await fetch('/api/data');
    const data = await res.json();
    state.team = data.team || [];
    state.emails = data.emails || [];
    state.historicalKb = data.historical_kb || [];
    state.analytics = data.analytics || {};

    if (!state.activeEmployeeId && state.team.length > 0) {
      state.activeEmployeeId = state.team[0].id;
    }

    renderEmployeeSelectOptions();
    renderManagerDashboard();
    renderEmployeeDashboard();
    lucide.createIcons();
  } catch (err) {
    console.error('Failed to fetch data:', err);
  }
}

// Toast notification helper
function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  const bgColor = type === 'success' ? 'bg-emerald-600' : (type === 'error' ? 'bg-rose-600' : 'bg-blue-600');
  toast.className = `${bgColor} text-white px-4 py-2.5 rounded-xl shadow-xl text-xs font-medium flex items-center space-x-2 transition-all transform duration-300 pointer-events-auto`;
  toast.innerHTML = `<span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// Switch between Manager and Employee cockpit
function switchRole(role) {
  state.currentRole = role;
  const btnMgr = document.getElementById('btn-tab-manager');
  const btnEmp = document.getElementById('btn-tab-employee');
  const viewMgr = document.getElementById('manager-view');
  const viewEmp = document.getElementById('employee-view');

  if (role === 'manager') {
    btnMgr.className = 'px-4 py-1.5 rounded-lg text-sm font-medium transition-all flex items-center space-x-2 bg-blue-600 text-white shadow-sm';
    btnEmp.className = 'px-4 py-1.5 rounded-lg text-sm font-medium transition-all flex items-center space-x-2 text-slate-400 hover:text-white';
    viewMgr.classList.remove('hidden');
    viewEmp.classList.add('hidden');
  } else {
    btnEmp.className = 'px-4 py-1.5 rounded-lg text-sm font-medium transition-all flex items-center space-x-2 bg-blue-600 text-white shadow-sm';
    btnMgr.className = 'px-4 py-1.5 rounded-lg text-sm font-medium transition-all flex items-center space-x-2 text-slate-400 hover:text-white';
    viewEmp.classList.remove('hidden');
    viewMgr.classList.add('hidden');
    renderEmployeeDashboard();
  }
  lucide.createIcons();
}

// Render Manager Dashboard
function renderManagerDashboard() {
  const analytics = state.analytics;
  if (!analytics) return;

  // KPI Metrics
  document.getElementById('kpi-total-received').textContent = analytics.total_received || 0;
  document.getElementById('kpi-tasks-vs-info').textContent = `${analytics.total_tasks || 0} Tasks · ${analytics.total_general_info || 0} Info`;
  document.getElementById('kpi-total-responded').textContent = analytics.total_responded || 0;
  const respPct = analytics.total_tasks > 0 ? Math.round((analytics.total_responded / analytics.total_tasks) * 100) : 0;
  document.getElementById('kpi-responded-pct').textContent = `${respPct}% Rate`;
  document.getElementById('kpi-total-pending').textContent = analytics.total_pending || 0;
  document.getElementById('kpi-sla-breached').textContent = analytics.sla_breached_count || 0;
  document.getElementById('kpi-sla-compliance').textContent = `${analytics.sla_compliance_percent || 100}% SLA`;
  document.getElementById('kpi-avg-time').textContent = `${analytics.avg_response_time_hours || 0}h`;

  // Render Team Workload Cards
  const teamCardsGrid = document.getElementById('team-cards-grid');
  teamCardsGrid.innerHTML = '';

  const teamBreakdown = analytics.team_breakdown || [];
  teamBreakdown.forEach(item => {
    const emp = item.employee;
    const isSelected = state.selectedEmployeeFilter === emp.id;
    const card = document.createElement('div');
    card.onclick = () => toggleEmployeeFilter(emp.id);
    card.className = `p-4 rounded-xl border transition-all cursor-pointer ${
      isSelected 
        ? 'bg-blue-900/30 border-blue-500 ring-2 ring-blue-500/30' 
        : 'bg-slate-900/60 border-slate-800 hover:border-slate-700 hover:bg-slate-850'
    }`;

    card.innerHTML = `
      <div class="flex items-center justify-between">
        <div class="flex items-center space-x-2.5">
          <div class="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center font-bold text-xs text-blue-400">
            ${emp.avatar || emp.name.charAt(0)}
          </div>
          <div>
            <div class="font-semibold text-white text-xs">${emp.name}</div>
            <div class="text-[10px] text-slate-400 truncate max-w-[120px]">${emp.role}</div>
          </div>
        </div>
        <span class="text-[10px] px-1.5 py-0.5 rounded font-semibold ${item.breached_count > 0 ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30' : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'}">
          ${item.sla_compliance_percent}% SLA
        </span>
      </div>

      <div class="mt-3 grid grid-cols-3 gap-2 text-center text-[11px] pt-2 border-t border-slate-800/80">
        <div>
          <div class="text-slate-400 text-[10px]">Assigned</div>
          <div class="font-bold text-white text-xs">${item.total_assigned}</div>
        </div>
        <div>
          <div class="text-slate-400 text-[10px]">Responded</div>
          <div class="font-bold text-emerald-400 text-xs">${item.responded_count}</div>
        </div>
        <div>
          <div class="text-slate-400 text-[10px]">Pending</div>
          <div class="font-bold ${item.breached_count > 0 ? 'text-rose-400 font-extrabold' : 'text-amber-400'} text-xs">
            ${item.pending_count} ${item.breached_count > 0 ? `(${item.breached_count} Overdue)` : ''}
          </div>
        </div>
      </div>

      <div class="mt-2.5 pt-2 border-t border-slate-800/60 flex flex-wrap gap-1 items-center">
        ${(emp.skills || []).slice(0, 3).map(skill => `
          <span class="text-[9px] px-1.5 py-0.5 rounded bg-blue-950/60 text-blue-300 border border-blue-800/40 font-medium">
            ${skill}
          </span>
        `).join('')}
        ${(emp.skills || []).length > 3 ? `<span class="text-[9px] text-slate-400 font-bold">+${emp.skills.length - 3}</span>` : ''}
      </div>
    `;
    teamCardsGrid.appendChild(card);
  });

  renderManagerEmailsTable();
}

function toggleEmployeeFilter(empId) {
  state.selectedEmployeeFilter = state.selectedEmployeeFilter === empId ? null : empId;
  renderManagerDashboard();
}

function setTableFilter(filter) {
  state.selectedFilter = filter;
  document.querySelectorAll('.filter-pill').forEach(btn => {
    if (btn.getAttribute('data-filter') === filter) {
      btn.className = 'filter-pill px-3 py-1.5 rounded-lg bg-blue-600 text-white font-medium';
    } else {
      btn.className = 'filter-pill px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 hover:text-white font-medium';
    }
  });
  renderManagerEmailsTable();
}

function applyFilters() {
  state.searchQuery = document.getElementById('manager-search').value.toLowerCase();
  renderManagerEmailsTable();
}

// Render Manager Emails Table
function renderManagerEmailsTable() {
  const tbody = document.getElementById('manager-emails-tbody');
  tbody.innerHTML = '';

  let list = state.emails;

  // Filter pills
  if (state.selectedFilter === 'pending') {
    list = list.filter(e => e.category === 'Task' && !e.is_responded);
  } else if (state.selectedFilter === 'breached') {
    list = list.filter(e => e.category === 'Task' && e.sla_metrics && e.sla_metrics.is_breached);
  } else if (state.selectedFilter === 'responded') {
    list = list.filter(e => e.category === 'Task' && e.is_responded);
  } else if (state.selectedFilter === 'general_info') {
    list = list.filter(e => e.category === 'General Information');
  }

  // Employee filter
  if (state.selectedEmployeeFilter) {
    list = list.filter(e => e.assigned_to === state.selectedEmployeeFilter);
  }

  // Search filter
  if (state.searchQuery) {
    list = list.filter(e => 
      (e.subject || '').toLowerCase().includes(state.searchQuery) ||
      (e.sender?.name || '').toLowerCase().includes(state.searchQuery) ||
      (e.task_type || '').toLowerCase().includes(state.searchQuery) ||
      (e.response_info?.solution_category || '').toLowerCase().includes(state.searchQuery)
    );
  }

  if (list.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" class="py-8 text-center text-slate-500">
          <i data-lucide="inbox" class="w-8 h-8 mx-auto mb-2 text-slate-600"></i>
          No emails match the selected criteria.
        </td>
      </tr>
    `;
    lucide.createIcons();
    return;
  }

  list.forEach(email => {
    const tr = document.createElement('tr');
    tr.className = 'kf-table-row transition';
    tr.setAttribute('data-id', email.id);

    // Category / Task Type Badge
    let categoryBadgeHtml = '';
    if (email.category === 'General Information') {
      categoryBadgeHtml = `<span class="px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700 font-medium">General Info</span>`;
    } else {
      categoryBadgeHtml = `
        <div class="flex flex-col space-y-0.5">
          <span class="px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-300 border border-blue-500/20 font-medium w-fit">
            ${email.task_type || 'Task'}
          </span>
          <span class="text-[10px] text-slate-500">${email.sla_priority || 'Standard'}</span>
        </div>
      `;
    }

    // Assignee
    const assignee = state.team.find(m => m.id === email.assigned_to);
    const assigneeHtml = assignee ? `
      <div class="flex items-center space-x-1.5">
        <div class="w-5 h-5 rounded bg-blue-900/50 text-blue-300 text-[10px] font-bold flex items-center justify-center">
          ${assignee.avatar || assignee.name.charAt(0)}
        </div>
        <span class="text-white">${assignee.name}</span>
      </div>
    ` : `<span class="text-slate-500">Unassigned</span>`;

    // Status & SLA Runway
    let statusHtml = '';
    const sla = email.sla_metrics || {};

    if (email.category === 'General Information') {
      statusHtml = `<span class="text-slate-400 text-[11px]">Informational</span>`;
    } else if (email.is_responded) {
      statusHtml = `
        <div class="flex items-center space-x-1.5 text-emerald-400 font-medium">
          <i data-lucide="check-circle-2" class="w-3.5 h-3.5"></i>
          <span>Responded in ${sla.turnaround_formatted || (email.response_info?.response_time_hours + 'h')}</span>
        </div>
      `;
    } else {
      // Pending
      const isBreached = sla.is_breached;
      const isApproaching = sla.status === 'Approaching Breach';
      let badgeStyle = isBreached 
        ? 'bg-rose-500/10 text-rose-300 border-rose-500/30 font-bold' 
        : (isApproaching ? 'bg-amber-500/10 text-amber-300 border-amber-500/30' : 'bg-blue-500/10 text-blue-300 border-blue-500/30');

      statusHtml = `
        <div class="space-y-0.5">
          <div class="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full border text-[10px] ${badgeStyle}">
            <i data-lucide="${isBreached ? 'alert-triangle' : 'clock'}" class="w-3 h-3"></i>
            <span>Pending ${sla.aging_formatted || '0m'}</span>
          </div>
          <div class="text-[10px] ${isBreached ? 'text-rose-400 font-semibold' : 'text-slate-500'}">
            ${sla.time_remaining_formatted || ''}
          </div>
        </div>
      `;
    }

    // Historical Match
    let histMatchHtml = '';
    if (email.historical_match) {
      histMatchHtml = `
        <span class="inline-flex items-center space-x-1 px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 text-[10px] font-semibold" title="Historical Ticket Ref: ${email.historical_match.historical_ticket_id}">
          <i data-lucide="check" class="w-3 h-3"></i>
          <span>${email.historical_match.matched_kb_id} (${email.historical_match.historical_ticket_id})</span>
        </span>
      `;
    } else {
      histMatchHtml = `<span class="text-slate-500 text-[10px]">No Prior KB Match</span>`;
    }

    // Resolution Details
    let resDetailsHtml = '';
    if (email.is_responded && email.response_info) {
      resDetailsHtml = `
        <div class="max-w-xs">
          <div class="font-medium text-white text-[11px] truncate">${email.response_info.solution_category || 'Resolved'}</div>
          <div class="text-slate-400 text-[10px] truncate" title="${email.response_info.resolution_details || ''}">${email.response_info.resolution_details || ''}</div>
        </div>
      `;
    } else {
      resDetailsHtml = `<span class="text-slate-600">-</span>`;
    }

    // Actions
    let actionButtons = `
      <div class="flex items-center justify-end space-x-1.5">
        <button onclick="openResponseStudio('${email.id}')" class="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white transition text-[11px] font-medium flex items-center space-x-1">
          <i data-lucide="${email.is_responded ? 'eye' : 'message-square'}" class="w-3 h-3"></i>
          <span>${email.is_responded ? 'View' : 'Respond'}</span>
        </button>
    `;

    if (!email.is_responded && email.category === 'Task') {
      actionButtons += `
        <button onclick="openReassignModal('${email.id}')" class="px-2.5 py-1 rounded bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/30 transition text-[11px] font-medium flex items-center space-x-1">
          <i data-lucide="user-plus" class="w-3 h-3"></i>
          <span>Re-assign</span>
        </button>
      `;
    }
    actionButtons += `</div>`;

    tr.innerHTML = `
      <td class="py-3 px-4 max-w-xs">
        <div class="font-medium text-white truncate" title="${email.subject}">${email.subject}</div>
        <div class="text-slate-500 text-[10px] truncate">From: ${email.sender?.name || 'Unknown'} &bull; ${new Date(email.received_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>
      </td>
      <td class="py-3 px-4">${categoryBadgeHtml}</td>
      <td class="py-3 px-4">${assigneeHtml}</td>
      <td class="py-3 px-4">${statusHtml}</td>
      <td class="py-3 px-4">${histMatchHtml}</td>
      <td class="py-3 px-4">${resDetailsHtml}</td>
      <td class="py-3 px-4 text-right">${actionButtons}</td>
    `;
    tbody.appendChild(tr);
  });

  lucide.createIcons();
}

// Render Employee Select Dropdown
function renderEmployeeSelectOptions() {
  const select = document.getElementById('employee-select');
  select.innerHTML = '';
  state.team.forEach(emp => {
    const opt = document.createElement('option');
    opt.value = emp.id;
    opt.textContent = `${emp.name} (${emp.role})`;
    if (emp.id === state.activeEmployeeId) opt.selected = true;
    select.appendChild(opt);
  });
}

function onEmployeeSelectChange(empId) {
  state.activeEmployeeId = empId;
  renderEmployeeDashboard();
}

// Render Employee Dashboard
function renderEmployeeDashboard() {
  const emp = state.team.find(m => m.id === state.activeEmployeeId);
  if (!emp) return;

  // Header profile card
  document.getElementById('emp-avatar').textContent = emp.avatar || emp.name.charAt(0);
  document.getElementById('emp-name').textContent = emp.name;
  document.getElementById('emp-role').textContent = emp.role;
  document.getElementById('emp-dept').textContent = emp.department || 'Engineering';

  const skillsEl = document.getElementById('emp-skills-pills');
  if (skillsEl) {
    skillsEl.innerHTML = (emp.skills || []).map(skill => `
      <span class="text-[10px] px-2 py-0.5 rounded-full bg-blue-500/15 text-blue-300 border border-blue-500/30 font-medium">
        ${skill}
      </span>
    `).join('');
  }

  // Compute personal stats
  const myEmails = state.emails.filter(e => e.assigned_to === emp.id);
  const myTasks = myEmails.filter(e => e.category === 'Task');
  const myResponded = myTasks.filter(e => e.is_responded);
  const myPending = myTasks.filter(e => !e.is_responded);
  const myBreached = myTasks.filter(e => e.sla_metrics && e.sla_metrics.is_breached);
  const mySlaPercent = myTasks.length > 0 ? Math.round(((myTasks.length - myBreached.length) / myTasks.length) * 100) : 100;

  document.getElementById('emp-kpi-assigned').textContent = myTasks.length;
  document.getElementById('emp-kpi-responded').textContent = myResponded.length;
  document.getElementById('emp-kpi-pending').textContent = myPending.length;
  document.getElementById('emp-kpi-compliance').textContent = `${mySlaPercent}%`;

  // Render personal task queue (Urgent pending tasks first)
  const queueContainer = document.getElementById('employee-task-queue');
  queueContainer.innerHTML = '';

  const sortedTasks = [...myTasks].sort((a, b) => {
    // Pending first
    if (!a.is_responded && b.is_responded) return -1;
    if (a.is_responded && !b.is_responded) return 1;
    // Breached first
    const aBreached = a.sla_metrics?.is_breached ? 1 : 0;
    const bBreached = b.sla_metrics?.is_breached ? 1 : 0;
    if (aBreached !== bBreached) return bBreached - aBreached;
    return new Date(a.received_at) - new Date(b.received_at);
  });

  if (sortedTasks.length === 0) {
    queueContainer.innerHTML = `
      <div class="glass-panel p-8 rounded-2xl text-center text-slate-500">
        <i data-lucide="check-circle" class="w-10 h-10 text-emerald-400 mx-auto mb-2"></i>
        <h4 class="text-white font-medium">All caught up!</h4>
        <p class="text-xs mt-1">No active tasks currently assigned to ${emp.name}.</p>
      </div>
    `;
    lucide.createIcons();
    return;
  }

  sortedTasks.forEach(email => {
    const card = document.createElement('div');
    const isBreached = email.sla_metrics?.is_breached;
    const isResponded = email.is_responded;

    card.className = `p-4 rounded-2xl border transition-all ${
      isResponded 
        ? 'bg-slate-900/40 border-slate-800' 
        : (isBreached ? 'bg-rose-950/20 border-rose-800/80' : 'bg-slate-900/80 border-slate-700/80')
    }`;

    // Historical match banner inside task card
    let matchBanner = '';
    if (email.historical_match) {
      matchBanner = `
        <div class="mt-2.5 p-2 rounded-lg bg-emerald-950/30 border border-emerald-500/20 flex items-center justify-between text-xs text-emerald-300">
          <div class="flex items-center space-x-1.5">
            <i data-lucide="sparkles" class="w-3.5 h-3.5 text-emerald-400"></i>
            <span><strong>Verified Precedent Found:</strong> ${email.historical_match.kb_title || email.historical_match.solution_category} (Ticket #${email.historical_match.historical_ticket_id})</span>
          </div>
          <span class="text-[10px] text-emerald-400 font-semibold uppercase">Draft Ready</span>
        </div>
      `;
    } else if (!isResponded) {
      matchBanner = `
        <div class="mt-2.5 p-2 rounded-lg bg-slate-950/40 border border-slate-800 flex items-center space-x-1.5 text-xs text-slate-400">
          <i data-lucide="info" class="w-3.5 h-3.5 text-slate-500"></i>
          <span>No historical precedent found. Manual investigation required.</span>
        </div>
      `;
    }

    card.innerHTML = `
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div class="space-y-1">
          <div class="flex items-center space-x-2">
            <span class="px-2 py-0.5 rounded text-[10px] font-semibold ${email.sla_priority?.includes('P1') ? 'bg-rose-500/20 text-rose-300' : 'bg-blue-500/20 text-blue-300'}">
              ${email.task_type || 'Task'}
            </span>
            <span class="text-xs text-slate-500 font-mono">${email.id}</span>
            <span class="text-xs text-slate-400">&bull; From: ${email.sender?.name}</span>
          </div>
          <h4 class="font-semibold text-white text-sm">${email.subject}</h4>
        </div>

        <div class="flex items-center space-x-3">
          <div class="text-right text-xs">
            <div class="font-medium ${isResponded ? 'text-emerald-400' : (isBreached ? 'text-rose-400 font-bold' : 'text-amber-400')}">
              ${isResponded ? `Responded in ${email.sla_metrics?.turnaround_formatted}` : `Pending: ${email.sla_metrics?.aging_formatted}`}
            </div>
            <div class="text-[10px] text-slate-500">${isResponded ? 'Task Closed' : email.sla_metrics?.time_remaining_formatted}</div>
          </div>
          <button onclick="openResponseStudio('${email.id}')" class="px-3.5 py-1.5 rounded-xl ${isResponded ? 'bg-slate-800 text-slate-300' : 'bg-blue-600 hover:bg-blue-500 text-white font-medium'} text-xs transition flex items-center space-x-1.5 shadow-md">
            <i data-lucide="${isResponded ? 'eye' : 'send'}" class="w-3.5 h-3.5"></i>
            <span>${isResponded ? 'View Resolution' : 'Review & Respond'}</span>
          </button>
        </div>
      </div>

      ${matchBanner}
    `;
    queueContainer.appendChild(card);
  });

  lucide.createIcons();
}

// Open Response Studio Modal
function openResponseStudio(emailId) {
  const email = state.emails.find(e => e.id === emailId);
  if (!email) return;

  document.getElementById('resp-email-id').value = email.id;
  document.getElementById('modal-email-ref').textContent = `${email.id} · Priority: ${email.sla_priority || 'Standard'}`;
  document.getElementById('modal-sender-name').textContent = email.sender?.name || 'User';
  document.getElementById('modal-sender-email').textContent = `<${email.sender?.email || 'noreply'}>`;
  document.getElementById('modal-received-at').textContent = `Received at ${new Date(email.received_at).toLocaleString()}`;
  document.getElementById('modal-subject').textContent = email.subject;
  document.getElementById('modal-body').textContent = email.body || email.subject;

  // Classification info
  document.getElementById('modal-badge-category').textContent = email.category;
  document.getElementById('modal-badge-tasktype').textContent = email.task_type || 'Informational';
  document.getElementById('modal-badge-sla').textContent = email.sla_priority || 'No SLA';
  document.getElementById('modal-classification-reason').textContent = email.classification_reason || 'Autonomous agent classification applied.';

  // Historical Match recommendation
  const histContainer = document.getElementById('historical-match-container');
  histContainer.innerHTML = '';

  if (email.historical_match) {
    const match = email.historical_match;
    histContainer.innerHTML = `
      <div class="p-4 rounded-xl bg-emerald-950/20 border border-emerald-500/30 space-y-3">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-2 text-emerald-400 font-semibold">
            <i data-lucide="shield-check" class="w-4 h-4"></i>
            <span>VERIFIED HISTORICAL RESOLUTION FOUND (Ref: #${match.historical_ticket_id})</span>
          </div>
          <span class="text-[10px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-semibold uppercase">100% Verified Match</span>
        </div>

        <div class="text-xs text-slate-300 space-y-1">
          <div><strong class="text-white">Previous Solution:</strong> ${match.solution_category} (Resolved by ${match.resolved_by || 'Team'} on ${match.resolution_date || 'Past Record'})</div>
          <div class="text-slate-400"><strong class="text-slate-300">Resolution Steps Taken:</strong> ${match.resolution_details}</div>
        </div>

        <div class="pt-1 flex items-center justify-between">
          <span class="text-[11px] text-emerald-400/90 font-mono flex items-center space-x-1">
            <i data-lucide="check" class="w-3 h-3"></i>
            <span>Deterministic Anti-Hallucination: Sourced directly from historical database</span>
          </span>
          <button type="button" onclick="applyHistoricalDraft('${email.id}')" class="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold transition text-xs flex items-center space-x-1.5 shadow-md">
            <i data-lucide="copy-check" class="w-3.5 h-3.5"></i>
            <span>Apply Historical Response Draft</span>
          </button>
        </div>
      </div>
    `;
  } else {
    histContainer.innerHTML = `
      <div class="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 flex items-start space-x-3 text-xs text-slate-400">
        <i data-lucide="alert-circle" class="w-4 h-4 text-slate-500 shrink-0 mt-0.5"></i>
        <div>
          <span class="text-slate-300 font-semibold">No Verified Historical Precedent Found:</span>
          <span> As per system governance policy, generative AI invention for unverified solutions is disabled. Please investigate and enter the resolution details manually below.</span>
        </div>
      </div>
    `;
  }

  // Populate form fields
  if (email.is_responded && email.response_info) {
    document.getElementById('resp-solution-cat').value = email.response_info.solution_category || '';
    document.getElementById('resp-resolution-details').value = email.response_info.resolution_details || '';
    document.getElementById('resp-body').value = email.response_info.response_body || '';
    document.getElementById('resp-add-kb').checked = false;
  } else {
    // Pre-populate if historical draft exists
    if (email.historical_match) {
      document.getElementById('resp-solution-cat').value = email.historical_match.solution_category || '';
      document.getElementById('resp-resolution-details').value = email.historical_match.resolution_details || '';
      document.getElementById('resp-body').value = email.historical_match.verified_draft || '';
    } else {
      document.getElementById('resp-solution-cat').value = '';
      document.getElementById('resp-resolution-details').value = '';
      document.getElementById('resp-body').value = '';
    }
    document.getElementById('resp-add-kb').checked = true;
  }

  document.getElementById('modal-response-studio').classList.remove('hidden');
  lucide.createIcons();
}

function applyHistoricalDraft(emailId) {
  const email = state.emails.find(e => e.id === emailId);
  if (email && email.historical_match) {
    document.getElementById('resp-solution-cat').value = email.historical_match.solution_category || '';
    document.getElementById('resp-resolution-details').value = email.historical_match.resolution_details || '';
    document.getElementById('resp-body').value = email.historical_match.verified_draft || '';
    showToast('Verified historical draft and resolution details applied!', 'success');
  }
}

function closeResponseStudio() {
  document.getElementById('modal-response-studio').classList.add('hidden');
}

// Submit Response Form
async function submitEmailResponse(event) {
  event.preventDefault();
  const emailId = document.getElementById('resp-email-id').value;
  const solutionCategory = document.getElementById('resp-solution-cat').value;
  const resolutionDetails = document.getElementById('resp-resolution-details').value;
  const responseBody = document.getElementById('resp-body').value;
  const addToKb = document.getElementById('resp-add-kb').checked;

  try {
    const res = await fetch('/api/emails/respond', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email_id: emailId,
        responder_id: state.activeEmployeeId,
        solution_category: solutionCategory,
        resolution_details: resolutionDetails,
        response_body: responseBody,
        add_to_kb: addToKb
      })
    });

    const result = await res.json();
    if (result.success) {
      showToast(`Response dispatched & resolution category '${solutionCategory}' logged!`, 'success');
      closeResponseStudio();
      await fetchData();
    } else {
      showToast(result.error || 'Failed to submit response', 'error');
    }
  } catch (err) {
    showToast('Network error while submitting response', 'error');
  }
}

// Open Re-assign Modal with Complete Resource Intelligence
function openReassignModal(emailId) {
  const email = state.emails.find(e => e.id === emailId);
  if (!email) return;

  document.getElementById('reassign-email-id').value = email.id;
  const idBadge = document.getElementById('reassign-email-id-badge');
  if (idBadge) idBadge.textContent = email.id;

  const subjectEl = document.getElementById('reassign-subject-preview');
  if (subjectEl) subjectEl.textContent = email.subject;

  const catBadge = document.getElementById('reassign-category-badge');
  if (catBadge) catBadge.textContent = `Task: ${email.task_type || email.category}`;

  const currentEmp = state.team.find(m => m.id === email.assigned_to);
  const currEl = document.getElementById('reassign-current-assignee');
  if (currEl) {
    currEl.innerHTML = `Currently assigned to: <strong class="text-white">${currentEmp ? currentEmp.name : 'Unassigned'}</strong> (${currentEmp ? currentEmp.role : ''})`;
  }

  const slaBadge = document.getElementById('reassign-sla-badge');
  if (slaBadge) {
    const isBreached = email.sla_metrics && email.sla_metrics.is_breached;
    slaBadge.textContent = `${email.sla_priority || 'Standard'} • ${email.sla_metrics?.time_remaining_formatted || 'Pending'}`;
    slaBadge.className = `px-2 py-0.5 rounded text-[10px] font-semibold ${isBreached ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30' : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'}`;
  }

  // Populate target teammates with skill and domain match hints
  const targetSelect = document.getElementById('reassign-target-member');
  targetSelect.innerHTML = '';
  let firstValidId = null;

  const queryText = `${email.subject || ''} ${email.body || ''} ${email.task_type || ''}`.toLowerCase();

  state.team.forEach(emp => {
    const opt = document.createElement('option');
    opt.value = emp.id;
    const isCurrent = emp.id === email.assigned_to;

    // Check skill overlap
    const hasSkillMatch = (emp.skills || []).some(s => {
      const sl = s.toLowerCase();
      return queryText.includes(sl.split(' ')[0]) ||
             (sl.includes('vpn') && queryText.includes('vpn')) ||
             (sl.includes('sql') && (queryText.includes('sql') || queryText.includes('postgres'))) ||
             (sl.includes('kubernetes') && (queryText.includes('k8s') || queryText.includes('kubernetes') || queryText.includes('oom')));
    });

    const topSkills = (emp.skills || []).slice(0, 2).join(', ');
    opt.textContent = `${emp.name} — ${emp.role} [${topSkills}]${hasSkillMatch ? ' ⭐️ (Skill Match)' : ''}${isCurrent ? ' [Current Assignee]' : ''}`;

    if (isCurrent) {
      opt.disabled = true;
    } else if (!firstValidId) {
      firstValidId = emp.id;
      opt.selected = true;
    }
    targetSelect.appendChild(opt);
  });

  if (firstValidId) {
    targetSelect.value = firstValidId;
    onReassignTargetChange(firstValidId);
  }

  document.getElementById('modal-reassign').classList.remove('hidden');
  lucide.createIcons();
}

function onReassignTargetChange(candidateId) {
  const emp = state.team.find(m => m.id === candidateId);
  const container = document.getElementById('reassign-resource-intel');
  if (!emp || !container) return;

  const breakdown = (state.analytics?.team_breakdown || []).find(b => b.employee.id === candidateId) || {
    total_assigned: 0,
    pending_count: 0,
    breached_count: 0,
    sla_compliance_percent: 100
  };

  const emailId = document.getElementById('reassign-email-id').value;
  const email = state.emails.find(e => e.id === emailId) || {};
  const query = `${email.subject || ''} ${email.body || ''} ${email.task_type || ''}`.toLowerCase();

  const matchedSkills = (emp.skills || []).filter(s => {
    const sl = s.toLowerCase();
    return query.includes(sl.split(' ')[0]) || 
           (sl.includes('vpn') && query.includes('vpn')) ||
           (sl.includes('network') && (query.includes('network') || query.includes('vpn') || query.includes('gateway'))) ||
           (sl.includes('sql') && (query.includes('sql') || query.includes('postgres') || query.includes('database'))) ||
           (sl.includes('kubernetes') && (query.includes('k8s') || query.includes('kubernetes') || query.includes('pod') || query.includes('oom'))) ||
           (sl.includes('access') && query.includes('access'));
  });

  const isSkillFit = matchedSkills.length > 0;
  const isBreached = breakdown.breached_count > 0;

  container.innerHTML = `
    <div class="flex items-center justify-between pb-2 border-b border-slate-800/80">
      <div class="flex items-center space-x-2.5">
        <div class="w-8 h-8 rounded-lg bg-blue-600/20 text-blue-300 font-bold flex items-center justify-center text-xs border border-blue-500/30">
          ${emp.avatar || emp.name.charAt(0)}
        </div>
        <div>
          <div class="font-bold text-white text-xs">${emp.name} &bull; <span class="text-slate-400 font-normal">${emp.experience || 'Specialist'}</span></div>
          <div class="text-[10px] text-slate-400">${emp.department} &bull; ${emp.primary_expertise || emp.role}</div>
        </div>
      </div>
      <div class="text-right">
        <span class="text-[10px] px-2 py-0.5 rounded font-semibold ${isBreached ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30' : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'}">
          ${breakdown.sla_compliance_percent}% SLA
        </span>
      </div>
    </div>

    <!-- Live Workload Grid -->
    <div class="grid grid-cols-3 gap-2 py-1 text-center text-[10px]">
      <div class="bg-slate-900/60 p-1.5 rounded-lg border border-slate-800">
        <div class="text-slate-400">Total Assigned</div>
        <div class="font-bold text-white text-xs">${breakdown.total_assigned}</div>
      </div>
      <div class="bg-slate-900/60 p-1.5 rounded-lg border border-slate-800">
        <div class="text-slate-400">Queue Pending</div>
        <div class="font-bold text-amber-400 text-xs">${breakdown.pending_count}</div>
      </div>
      <div class="bg-slate-900/60 p-1.5 rounded-lg border border-slate-800">
        <div class="text-slate-400">Overdue SLA</div>
        <div class="font-bold ${isBreached ? 'text-rose-400 font-extrabold' : 'text-slate-400'} text-xs">${breakdown.breached_count}</div>
      </div>
    </div>

    <!-- Verified Skills Badges -->
    <div>
      <div class="text-[10px] text-slate-400 uppercase tracking-wider font-semibold mb-1">Resource Verified Skills & Domain Strengths:</div>
      <div class="flex flex-wrap gap-1">
        ${(emp.skills || []).map(skill => {
          const isMatch = matchedSkills.includes(skill);
          return `
            <span class="text-[10px] px-2 py-0.5 rounded-md font-medium border flex items-center space-x-1 ${
              isMatch 
                ? 'bg-emerald-950/60 text-emerald-300 border-emerald-500/50 shadow-sm shadow-emerald-900/40' 
                : 'bg-slate-900 text-blue-300 border-slate-700'
            }">
              ${isMatch ? '<i data-lucide="check" class="w-3 h-3 text-emerald-400 inline mr-0.5"></i>' : ''}
              <span>${skill}</span>
            </span>
          `;
        }).join('')}
      </div>
    </div>

    <!-- Agent Recommendation Fit Banner -->
    <div class="p-2 rounded-lg text-[11px] flex items-start space-x-2 ${
      isSkillFit 
        ? 'bg-emerald-950/30 border border-emerald-500/30 text-emerald-300' 
        : 'bg-blue-950/20 border border-blue-500/20 text-slate-300'
    }">
      <i data-lucide="${isSkillFit ? 'sparkles' : 'info'}" class="w-4 h-4 mt-0.5 shrink-0 ${isSkillFit ? 'text-emerald-400' : 'text-blue-400'}"></i>
      <div>
        ${isSkillFit 
          ? `<strong>Skill Fit Recommendation:</strong> ${emp.name} is specialized in <strong>${matchedSkills.join(', ')}</strong>, directly aligning with this incident.`
          : `<strong>Standard Routing:</strong> ${emp.name} is available in ${emp.department} with active capacity (${breakdown.pending_count} pending).`
        }
      </div>
    </div>
  `;
  lucide.createIcons();
}

function closeReassignModal() {
  document.getElementById('modal-reassign').classList.add('hidden');
}

async function submitReassignment(event) {
  event.preventDefault();
  const emailId = document.getElementById('reassign-email-id').value;
  const newAssigneeId = document.getElementById('reassign-target-member').value;
  const reason = document.getElementById('reassign-reason').value;

  try {
    const res = await fetch('/api/emails/reassign', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email_id: emailId,
        new_assigned_to: newAssigneeId,
        reassign_reason: reason
      })
    });

    const result = await res.json();
    if (result.success) {
      showToast(`Email ${emailId} successfully reassigned!`, 'success');
      closeReassignModal();
      await fetchData();
    } else {
      showToast(result.error || 'Failed to reassign email', 'error');
    }
  } catch (err) {
    showToast('Network error during reassignment', 'error');
  }
}

// Open & Run Simulation Modal
function openSimulateModal() {
  // Populate Sender dropdown with Employees & External Partners
  const senderSelect = document.getElementById('sim-sender-select');
  if (senderSelect) {
    senderSelect.innerHTML = '';

    const empGroup = document.createElement('optgroup');
    empGroup.label = 'Team Employees (Internal)';
    state.team.forEach(emp => {
      const opt = document.createElement('option');
      opt.value = emp.id;
      opt.textContent = `${emp.name} <${emp.email}> (${emp.role})`;
      empGroup.appendChild(opt);
    });
    senderSelect.appendChild(empGroup);

    const extGroup = document.createElement('optgroup');
    extGroup.label = 'External Enterprise Clients / Partners';
    EXTERNAL_CONTACTS.forEach(ext => {
      const opt = document.createElement('option');
      opt.value = ext.id;
      opt.textContent = `${ext.name} <${ext.email}> [${ext.org}]`;
      extGroup.appendChild(opt);
    });
    senderSelect.appendChild(extGroup);

    const customOpt = document.createElement('option');
    customOpt.value = 'custom';
    customOpt.textContent = '✍️ -- Custom Sender Input --';
    senderSelect.appendChild(customOpt);
  }

  // Populate Assign To dropdown
  const assignSelect = document.getElementById('sim-assign-to');
  if (assignSelect) {
    assignSelect.innerHTML = '';
    const autoOpt = document.createElement('option');
    autoOpt.value = 'auto';
    autoOpt.textContent = '🤖 AI Smart Agent Routing (Auto-Assign to best skill)';
    assignSelect.appendChild(autoOpt);

    state.team.forEach(emp => {
      const opt = document.createElement('option');
      opt.value = emp.id;
      const topSkills = (emp.skills || []).slice(0, 2).join(', ');
      opt.textContent = `${emp.name} — ${emp.role} [${topSkills}]`;
      assignSelect.appendChild(opt);
    });
  }

  onPresetChange('vpn');
  document.getElementById('modal-simulate').classList.remove('hidden');
  lucide.createIcons();
}

function closeSimulateModal() {
  document.getElementById('modal-simulate').classList.add('hidden');
}

function onSenderSelectChange(val) {
  const customRow = document.getElementById('sim-custom-sender-row');
  const nameInput = document.getElementById('sim-sender-name');
  const emailInput = document.getElementById('sim-sender-email');

  if (val === 'custom') {
    if (customRow) customRow.classList.remove('hidden');
    if (nameInput) nameInput.focus();
  } else {
    if (customRow) customRow.classList.add('hidden');
    const emp = state.team.find(m => m.id === val);
    const ext = EXTERNAL_CONTACTS.find(m => m.id === val);
    if (emp) {
      if (nameInput) nameInput.value = emp.name;
      if (emailInput) emailInput.value = emp.email;
    } else if (ext) {
      if (nameInput) nameInput.value = ext.name;
      if (emailInput) emailInput.value = ext.email;
    }
  }
}

function onPresetChange(presetKey) {
  const preset = SIMULATION_PRESETS[presetKey] || SIMULATION_PRESETS.vpn;
  document.getElementById('sim-subject').value = preset.subject;
  document.getElementById('sim-body').value = preset.body;

  const senderSelect = document.getElementById('sim-sender-select');
  if (senderSelect && preset.sender_id) {
    senderSelect.value = preset.sender_id;
    onSenderSelectChange(preset.sender_id);
  }

  const assignSelect = document.getElementById('sim-assign-to');
  if (assignSelect && preset.suggested_assignee) {
    assignSelect.value = preset.suggested_assignee;
  }
}

async function executeSimulation() {
  const subject = document.getElementById('sim-subject').value.trim();
  const body = document.getElementById('sim-body').value.trim();
  const senderSelect = document.getElementById('sim-sender-select').value;
  let sender_name = '';
  let sender_email = '';

  if (senderSelect === 'custom') {
    sender_name = document.getElementById('sim-sender-name').value.trim() || 'External Inquirer';
    sender_email = document.getElementById('sim-sender-email').value.trim() || 'inquiry@enterprise.io';
  } else {
    const emp = state.team.find(m => m.id === senderSelect);
    const ext = EXTERNAL_CONTACTS.find(m => m.id === senderSelect);
    if (emp) {
      sender_name = emp.name;
      sender_email = emp.email;
    } else if (ext) {
      sender_name = ext.name;
      sender_email = ext.email;
    } else {
      sender_name = document.getElementById('sim-sender-name').value.trim() || 'Enterprise Client';
      sender_email = document.getElementById('sim-sender-email').value.trim() || 'client@enterprise.io';
    }
  }

  const assignVal = document.getElementById('sim-assign-to').value;
  const assigned_to = (assignVal && assignVal !== 'auto') ? assignVal : undefined;

  if (!subject) {
    showToast('Please enter an email subject', 'error');
    return;
  }
  if (!body) {
    showToast('Please enter email body content', 'error');
    return;
  }

  const btn = document.getElementById('btn-ingest-simulate');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i><span>Ingesting...</span>`;
    lucide.createIcons();
  }

  try {
    const res = await fetch('/api/simulate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ subject, sender_name, sender_email, body, assigned_to })
    });

    const result = await res.json();
    if (result.success) {
      // Clear filters so new email is guaranteed visible at top of grid
      state.selectedFilter = 'all';
      state.selectedEmployeeFilter = null;
      state.searchQuery = '';
      const searchInput = document.getElementById('manager-search');
      if (searchInput) searchInput.value = '';

      document.querySelectorAll('.filter-pill').forEach(btnEl => {
        if (btnEl.getAttribute('data-filter') === 'all') {
          btnEl.className = 'filter-pill px-3 py-1.5 rounded-lg bg-blue-600 text-white font-medium';
        } else {
          btnEl.className = 'filter-pill px-3 py-1.5 rounded-lg bg-slate-800 text-slate-400 font-medium hover:text-white hover:bg-slate-700';
        }
      });

      closeSimulateModal();
      await fetchData();

      // Highlight the newly created row in the table
      setTimeout(() => {
        const row = document.querySelector(`tr[data-id="${result.email.id}"]`);
        if (row) {
          row.classList.add('ring-2', 'ring-indigo-500', 'bg-indigo-900/40');
          row.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
          setTimeout(() => {
            row.classList.remove('ring-2', 'ring-indigo-500', 'bg-indigo-900/40');
          }, 4500);
        }
      }, 200);

      const assigneeEmp = state.team.find(m => m.id === result.email.assigned_to);
      showToast(`Ingested ${result.email.id} into grid! Routed to ${assigneeEmp ? assigneeEmp.name : 'Team member'}.`, 'success');
    } else {
      showToast('Simulation ingestion failed', 'error');
    }
  } catch (err) {
    showToast('Network error during simulation', 'error');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i data-lucide="play" class="w-4 h-4"></i><span>Ingest & Process with Agent</span>`;
      lucide.createIcons();
    }
  }
}

// Reset benchmark data
async function resetBenchmarkData() {
  if (!confirm('Reset email data to initial hackathon benchmark state?')) return;
  try {
    const res = await fetch('/api/reset', { method: 'POST' });
    const result = await res.json();
    if (result.success) {
      showToast('Benchmark dataset restored successfully!', 'success');
      await fetchData();
    }
  } catch (err) {
    showToast('Failed to reset benchmark data', 'error');
  }
}
