/**
 * Page definitions — each page is a function returning HTML and an optional
 * onMount callback for attaching event listeners.
 */

/* ═══════════════════════════════════════════════════════════════════════════
   Overview / Dashboard Page
   ═══════════════════════════════════════════════════════════════════════════ */

function PageOverview() {
  const el = document.getElementById('page-content');
  el.innerHTML = `
    <div class="page-header">
      <h1 class="page-title">Group Overview</h1>
      <p class="page-subtitle">Track shared expenses and settle up effortlessly.</p>
      <div style="display:flex;gap:12px;margin-top:16px">
        <button class="btn btn-primary" onclick="App.openAddExpense()">${Icons.plus} Add Expense</button>
        <button class="btn btn-secondary" onclick="App.navigate('/import')">${Icons.upload} Import JSON</button>
      </div>
    </div>
    <div id="overview-stats" class="stat-grid">
      <div class="card"><div class="skeleton skeleton-card"></div></div>
      <div class="card"><div class="skeleton skeleton-card"></div></div>
      <div class="card"><div class="skeleton skeleton-card"></div></div>
      <div class="card"><div class="skeleton skeleton-card"></div></div>
    </div>
    <div class="two-col">
      <div class="section-card">
        <div class="section-card-header">
          <h3 class="section-card-title">Recent Expenses</h3>
          <a href="/expenses" onclick="App.navigate(event,'/expenses')" style="font-size:13px;font-weight:600">View all</a>
        </div>
        <div class="section-card-body" id="recent-expenses"><p style="color:var(--color-text-muted);font-size:14px">Loading...</p></div>
      </div>
      <div class="section-card">
        <div class="section-card-header">
          <h3 class="section-card-title">Member Balances</h3>
          <a href="/members" onclick="App.navigate(event,'/members')" style="font-size:13px;font-weight:600">View all</a>
        </div>
        <div class="section-card-body" id="member-balances"><p style="color:var(--color-text-muted);font-size:14px">Loading...</p></div>
      </div>
    </div>
  `;

  loadOverviewData();
}

async function loadOverviewData() {
  try {
    const data = await API.fetchGroup();
    renderOverviewStats(data);
    renderRecentExpenses(data.expenses || []);
    renderMemberBalances(data.balances || []);
  } catch (e) {
    document.getElementById('overview-stats').innerHTML =
      `<div class="empty-state"><div class="empty-state-icon">!</div><div class="empty-state-title">Failed to load</div><div class="empty-state-desc">${e.message}</div></div>`;
    showToast(e.message, 'error');
  }
}

function renderOverviewStats(data) {
  const totalAmount = parseFloat(data.total_amount || '0');
  const balances = data.balances || [];
  const el = document.getElementById('overview-stats');
  el.innerHTML = `
    ${StatCard({ icon: Icons.receipt, iconColor: 'blue', label: 'Total Group Expenses', value: fmtINR(totalAmount) })}
    ${StatCard({ icon: Icons.wallet, iconColor: 'green', label: 'You Are Owed', value: fmtINR(balances.filter(b => parseFloat(b.net_balance) > 0).reduce((s,b) => s + parseFloat(b.net_balance),0)) })}
    ${StatCard({ icon: Icons.receipt, iconColor: 'red', label: 'Total Outstanding', value: fmtINR(balances.filter(b => parseFloat(b.net_balance) < 0).reduce((s,b) => s + Math.abs(parseFloat(b.net_balance)),0)) })}
    ${StatCard({ icon: Icons.users, iconColor: 'blue', label: 'Group Members', value: (data.members || []).length })}
  `;
}

function renderRecentExpenses(expenses) {
  const el = document.getElementById('recent-expenses');
  const items = expenses.slice(-5).reverse();
  if (items.length === 0) {
    el.innerHTML = `<div class="empty-state">
      <div class="empty-state-icon">${Icons.receipt}</div>
      <div class="empty-state-title">No expenses yet</div>
      <div class="empty-state-desc">Add your first expense to start tracking who owes whom.</div>
      <button class="btn btn-primary" onclick="App.openAddExpense()">${Icons.plus} Add Expense</button>
    </div>`;
    return;
  }
  let rows = items.map(e => {
    const memberMap = {};
    (App._groupData?.members || []).forEach(m => { memberMap[m.id] = m.name || m.id; });
    const payerName = memberMap[e.payer] || e.payer;
    const date = e.timestamp ? new Date(e.timestamp).toLocaleDateString('en-IN', { day:'numeric', month:'short' }) : '-';
    return `<tr>
      <td style="font-weight:600">${escHtml(e.description)}</td>
      <td>${Avatar({ name: payerName, size: 26 })} ${escHtml(payerName)}</td>
      <td>${date}</td>
      <td style="font-weight:600">${fmtINR(e.amount)}</td>
      <td><span class="badge badge-blue">${e.split_type}</span></td>
      <td>${e.participants ? e.participants.length : 0}</td>
    </tr>`;
  }).join('');
  el.innerHTML = `<div class="table-container"><table><thead><tr>
    <th>Description</th><th>Payer</th><th>Date</th><th>Amount</th><th>Type</th><th>#</th>
  </tr></thead><tbody>${rows}</tbody></table></div>`;
}

function renderMemberBalances(balances) {
  const el = document.getElementById('member-balances');
  if (balances.length === 0) {
    el.innerHTML = `<div class="empty-state">
      <div class="empty-state-icon">${Icons.users}</div>
      <div class="empty-state-title">No members</div>
      <div class="empty-state-desc">Add group members to start tracking shared expenses.</div>
    </div>`;
    return;
  }
  let rows = balances.map(b => {
    const net = parseFloat(b.net_balance);
    let status, badgeClass;
    if (net > 0) { status = 'Gets back ' + fmtINR(net); badgeClass = 'badge-green'; }
    else if (net < 0) { status = 'Owes ' + fmtINR(Math.abs(net)); badgeClass = 'badge-red'; }
    else { status = 'Settled up'; badgeClass = 'badge-neutral'; }
    return `<tr>
      <td>${Avatar({ name: b.name || b.member_id, size: 26 })} ${escHtml(b.name || b.member_id)}</td>
      <td>${fmtINR(b.total_paid)}</td>
      <td>${fmtINR(b.total_share)}</td>
      <td><span class="badge ${badgeClass}">${status}</span></td>
    </tr>`;
  }).join('');
  el.innerHTML = `<div class="table-container"><table><thead><tr>
    <th>Member</th><th>Paid</th><th>Share</th><th>Status</th>
  </tr></thead><tbody>${rows}</tbody></table></div>`;
}

/* ═══════════════════════════════════════════════════════════════════════════
   Expenses Page
   ═══════════════════════════════════════════════════════════════════════════ */

function PageExpenses() {
  const el = document.getElementById('page-content');
  el.innerHTML = `
    <div class="page-header">
      <h1 class="page-title">Expenses</h1>
      <p class="page-subtitle">View and manage all shared expenses.</p>
      <div style="display:flex;gap:12px;margin-top:16px">
        <button class="btn btn-primary" onclick="App.openAddExpense()">${Icons.plus} Add Expense</button>
        <button class="btn btn-secondary" onclick="App.navigate('/import')">${Icons.upload} Import JSON</button>
      </div>
    </div>
    <div class="filter-bar">
      <input type="text" class="form-input" placeholder="Search expenses..." id="exp-search" style="min-width:200px" oninput="filterExpenses()">
      <select class="form-select" id="exp-payer-filter" onchange="filterExpenses()">
        <option value="">All Payers</option>
      </select>
      <select class="form-select" id="exp-type-filter" onchange="filterExpenses()">
        <option value="">All Types</option>
        <option value="equal">Equal</option>
        <option value="exact">Exact</option>
        <option value="percentage">Percentage</option>
      </select>
      <button class="btn btn-ghost btn-sm" onclick="clearExpenseFilters()">Clear filters</button>
    </div>
    <div class="section-card" id="expenses-list"><p style="padding:24px;color:var(--color-text-muted)">Loading...</p></div>
  `;
  loadExpensesPage();
}

async function loadExpensesPage() {
  try {
    const data = await API.fetchGroup();
    window._expPageData = data;
    // Populate payer filter
    const payerSelect = document.getElementById('exp-payer-filter');
    const members = data.members || [];
    members.forEach(m => {
      const opt = document.createElement('option');
      opt.value = m.id; opt.textContent = m.name || m.id;
      payerSelect.appendChild(opt);
    });
    renderExpensesTable(data.expenses || []);
  } catch (e) {
    document.getElementById('expenses-list').innerHTML =
      `<div class="empty-state"><div class="empty-state-icon">!</div><div class="empty-state-title">Failed to load</div><div class="empty-state-desc">${e.message}</div></div>`;
    showToast(e.message, 'error');
  }
}

function filterExpenses() {
  if (!window._expPageData) return;
  const search = (document.getElementById('exp-search')?.value || '').toLowerCase();
  const payer = document.getElementById('exp-payer-filter')?.value || '';
  const type = document.getElementById('exp-type-filter')?.value || '';

  let filtered = window._expPageData.expenses || [];
  if (search) filtered = filtered.filter(e => e.description.toLowerCase().includes(search));
  if (payer) filtered = filtered.filter(e => e.payer === payer);
  if (type) filtered = filtered.filter(e => e.split_type === type);
  renderExpensesTable(filtered);
}

function clearExpenseFilters() {
  const s = document.getElementById('exp-search'); if (s) s.value = '';
  const p = document.getElementById('exp-payer-filter'); if (p) p.value = '';
  const t = document.getElementById('exp-type-filter'); if (t) t.value = '';
  filterExpenses();
}

function renderExpensesTable(expenses) {
  const el = document.getElementById('expenses-list');
  if (expenses.length === 0) {
    el.innerHTML = `<div class="section-card-body"><div class="empty-state">
      <div class="empty-state-icon">${Icons.receipt}</div>
      <div class="empty-state-title">No expenses found</div>
      <div class="empty-state-desc">${document.getElementById('exp-search')?.value ? 'Try adjusting your filters.' : 'Add your first expense to get started.'}</div>
    </div></div>`;
    return;
  }
  const memberMap = {};
  if (window._expPageData) {
    (window._expPageData.members || []).forEach(m => { memberMap[m.id] = m.name || m.id; });
  }
  const rows = expenses.map(e => {
    const payerName = memberMap[e.payer] || e.payer;
    const date = e.timestamp ? new Date(e.timestamp).toLocaleDateString('en-IN', { day:'numeric', month:'short', year:'numeric' }) : '-';
    return `<tr>
      <td style="font-weight:600">${escHtml(e.description)}</td>
      <td>${Avatar({ name: payerName, size: 24 })} ${escHtml(payerName)}</td>
      <td>${date}</td>
      <td style="font-weight:600">${fmtINR(e.amount)}</td>
      <td><span class="badge badge-blue">${e.split_type}</span></td>
      <td>${e.participants ? e.participants.map(p => escHtml(memberMap[p] || p)).join(', ') : '-'}</td>
      <td>
        <button class="btn btn-ghost btn-sm" title="Delete" onclick="deleteExpense('${e.expense_id}')">${Icons.trash}</button>
      </td>
    </tr>`;
  }).join('');
  el.innerHTML = `<div class="table-container"><table><thead><tr>
    <th>Description</th><th>Payer</th><th>Date</th><th>Amount</th><th>Type</th><th>Participants</th><th></th>
  </tr></thead><tbody>${rows}</tbody></table></div>`;
}

async function deleteExpense(id) {
  if (!confirm('Delete this expense?')) return;
  try {
    await API.deleteExpense(id);
    showToast('Expense deleted', 'success');
    App.navigate('/expenses');
  } catch (e) {
    showToast(e.message, 'error');
  }
}

/* ═══════════════════════════════════════════════════════════════════════════
   Members Page
   ═══════════════════════════════════════════════════════════════════════════ */

function PageMembers() {
  const el = document.getElementById('page-content');
  el.innerHTML = `
    <div class="page-header">
      <h1 class="page-title">Members</h1>
      <p class="page-subtitle">Manage your group members and view their balances.</p>
      <div style="margin-top:16px">
        <button class="btn btn-primary" onclick="openAddMember()">${Icons.plus} Add Member</button>
      </div>
    </div>
    <div class="section-card" id="members-list"><p style="padding:24px;color:var(--color-text-muted)">Loading...</p></div>
  `;
  loadMembersPage();
}

async function loadMembersPage() {
  try {
    const data = await API.fetchGroup();
    const balances = data.balances || [];
    const balMap = {};
    balances.forEach(b => { balMap[b.member_id] = b; });

    const members = data.members || [];
    const el = document.getElementById('members-list');
    if (members.length === 0) {
      el.innerHTML = `<div class="section-card-body"><div class="empty-state">
        <div class="empty-state-icon">${Icons.users}</div>
        <div class="empty-state-title">No members</div>
        <div class="empty-state-desc">Add group members to get started.</div>
        <button class="btn btn-primary" onclick="openAddMember()">${Icons.plus} Add Member</button>
      </div></div>`;
      return;
    }

    const rows = members.map(m => {
      const bal = balMap[m.id];
      const net = bal ? parseFloat(bal.net_balance) : 0;
      let statusHtml, badgeClass;
      if (net > 0) { statusHtml = `Gets back ${fmtINR(net)}`; badgeClass = 'badge-green'; }
      else if (net < 0) { statusHtml = `Owes ${fmtINR(Math.abs(net))}`; badgeClass = 'badge-red'; }
      else { statusHtml = 'Settled up'; badgeClass = 'badge-neutral'; }
      return `<tr>
        <td>${Avatar({ name: m.name || m.id, size: 36 })} <span style="font-weight:600;margin-left:8px">${escHtml(m.name || m.id)}</span></td>
        <td>${bal ? fmtINR(bal.total_paid) : '₹0.00'}</td>
        <td>${bal ? fmtINR(bal.total_share) : '₹0.00'}</td>
        <td><span class="badge ${badgeClass}">${statusHtml}</span></td>
        <td><button class="btn btn-ghost btn-sm" title="Remove" onclick="deleteMember('${m.id}')">${Icons.trash}</button></td>
      </tr>`;
    }).join('');

    el.innerHTML = `<div class="table-container"><table><thead><tr>
      <th>Member</th><th>Total Paid</th><th>Total Share</th><th>Status</th><th></th>
    </tr></thead><tbody>${rows}</tbody></table></div>`;
  } catch (e) {
    document.getElementById('members-list').innerHTML =
      `<div class="empty-state"><p>Failed to load: ${e.message}</p></div>`;
    showToast(e.message, 'error');
  }
}

function openAddMember() {
  const { overlay, close } = Modal({
    title: 'Add Member',
    body: `
      <div class="form-group">
        <label class="form-label">Member ID</label>
        <input type="text" class="form-input" id="new-member-id" placeholder="e.g. frank">
        <p class="form-hint">Unique identifier for the member.</p>
      </div>
      <div class="form-group">
        <label class="form-label">Name (optional)</label>
        <input type="text" class="form-input" id="new-member-name" placeholder="e.g. Frank">
      </div>
    `,
    footer: `
      <button class="btn btn-secondary" onclick="this.closest('.modal-overlay').querySelector('.modal-close').click()">Cancel</button>
      <button class="btn btn-primary" onclick="App.addMemberFromModal(this)">${Icons.plus} Add Member</button>
    `,
  });
}

async function deleteMember(id) {
  if (!confirm('Remove this member? This may affect existing expenses.')) return;
  try {
    await API.deleteMember(id);
    showToast('Member removed', 'success');
    App.navigate('/members');
  } catch (e) {
    showToast(e.message, 'error');
  }
}

/* ═══════════════════════════════════════════════════════════════════════════
   Settle Up Page
   ═══════════════════════════════════════════════════════════════════════════ */

function PageSettleUp() {
  const el = document.getElementById('page-content');
  el.innerHTML = `
    <div class="page-header">
      <h1 class="page-title">Settle Up</h1>
      <p class="page-subtitle">Reduce unnecessary transfers and clear your group's outstanding balances.</p>
    </div>
    <div id="settlements-content"><p style="color:var(--color-text-muted)">Loading...</p></div>
  `;
  loadSettleUp();
}

async function loadSettleUp() {
  try {
    const data = await API.fetchGroup();
    const settlements = data.settlements || [];
    const totalOwed = settlements.reduce((s, st) => s + parseFloat(st.amount), 0);
    const membersInvolved = new Set();
    settlements.forEach(s => { membersInvolved.add(s.from); membersInvolved.add(s.to); });

    const el = document.getElementById('settlements-content');

    // Check if all settled
    const allSettled = data.balances && data.balances.every(b => parseFloat(b.net_balance) === 0);

    if (allSettled || settlements.length === 0) {
      el.innerHTML = `
        <div class="stat-grid" style="margin-bottom:24px">
          ${StatCard({ icon: Icons.check, iconColor: 'green', label: 'Status', value: 'All Settled!' })}
          ${StatCard({ icon: Icons.users, iconColor: 'blue', label: 'Group Members', value: (data.members || []).length })}
        </div>
        <div class="section-card">
          <div class="section-card-body" style="text-align:center;padding:48px">
            <div style="font-size:48px;margin-bottom:16px">🎉</div>
            <h3 style="font-size:20px;margin-bottom:8px">Everyone is settled!</h3>
            <p style="color:var(--color-text-secondary)">No outstanding balances. All expenses have been resolved.</p>
          </div>
        </div>
      `;
      return;
    }

    el.innerHTML = `
      <div class="stat-grid" style="margin-bottom:24px">
        ${StatCard({ icon: Icons.receipt, iconColor: 'red', label: 'Total Outstanding', value: fmtINR(totalOwed) })}
        ${StatCard({ icon: Icons.arrowRight, iconColor: 'blue', label: 'Transactions', value: settlements.length })}
        ${StatCard({ icon: Icons.users, iconColor: 'blue', label: 'Members Involved', value: membersInvolved.size })}
      </div>
      <div class="section-card">
        <div class="section-card-header">
          <h3 class="section-card-title">Suggested Settlements</h3>
          <div style="display:flex;gap:8px">
            <button class="btn btn-secondary btn-sm" onclick="copyAllSettlements()">${Icons.copy} Copy All</button>
            <button class="btn btn-secondary btn-sm" onclick="exportSettlementsJSON()">${Icons.download} Export JSON</button>
          </div>
        </div>
        <div class="section-card-body" id="settlement-items">
          ${settlements.map(s => `
            <div class="settlement-item">
              <div class="settlement-avatar from">${getInitials(s.from_name || s.from)}</div>
              <div class="settlement-info">
                <div class="settlement-people">${escHtml(s.from_name || s.from)} pays ${escHtml(s.to_name || s.to)}</div>
                <div class="settlement-desc">Settle outstanding balance</div>
              </div>
              ${Icons.arrowRight.replace('width="18"','width="22"').replace('height="18"','height="22"')}
              <div class="settlement-avatar to">${getInitials(s.to_name || s.to)}</div>
              <div class="settlement-amount">${fmtINR(s.amount)}</div>
              <button class="copy-settlement" title="Copy" onclick="copySettlement('${escHtml(s.from_name || s.from)}','${escHtml(s.to_name || s.to)}','${s.amount}')">${Icons.copy}</button>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  } catch (e) {
    document.getElementById('settlements-content').innerHTML =
      `<div class="empty-state"><div class="empty-state-icon">!</div><h3>Failed to load</h3><p>${e.message}</p></div>`;
    showToast(e.message, 'error');
  }
}

function copyAllSettlements() {
  const items = document.querySelectorAll('.settlement-item');
  let text = '';
  items.forEach(item => {
    const people = item.querySelector('.settlement-people')?.textContent || '';
    const amount = item.querySelector('.settlement-amount')?.textContent || '';
    text += `${people} ${amount}\n`;
  });
  navigator.clipboard.writeText(text.trim()).then(() => {
    showToast('All settlements copied!', 'success');
  });
}

function copySettlement(from, to, amount) {
  const text = `${from} pays ${to} ${fmtINR(amount)}`;
  navigator.clipboard.writeText(text).then(() => {
    showToast('Settlement copied!', 'success');
  });
}

function exportSettlementsJSON() {
  API.fetchSettlements().then(data => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'settlements.json';
    a.click(); URL.revokeObjectURL(url);
    showToast('Exported as JSON', 'success');
  }).catch(e => showToast(e.message, 'error'));
}

/* ═══════════════════════════════════════════════════════════════════════════
   Import JSON Page
   ═══════════════════════════════════════════════════════════════════════════ */

function PageImport() {
  const el = document.getElementById('page-content');
  el.innerHTML = `
    <div class="page-header">
      <h1 class="page-title">Import Expenses</h1>
      <p class="page-subtitle">Upload a JSON file with group members and expenses.</p>
    </div>
    <div class="section-card">
      <div class="section-card-body">
        <div class="drop-zone" id="import-drop-zone">
          <div class="drop-zone-icon">${Icons.upload}</div>
          <div class="drop-zone-text">Drag and drop a JSON file here, or click to select</div>
          <div class="drop-zone-hint">Supports .json files up to 50 MB</div>
          <input type="file" id="import-file-input" accept=".json" style="display:none">
        </div>
        <div id="import-preview" style="margin-top:20px"></div>
      </div>
    </div>
  `;

  // Set up drag-and-drop
  setTimeout(() => {
    const zone = document.getElementById('import-drop-zone');
    const input = document.getElementById('import-file-input');
    if (!zone || !input) return;

    zone.onclick = () => input.click();
    input.onchange = (e) => handleImportFile(e.target.files[0]);

    zone.ondragover = (e) => { e.preventDefault(); zone.classList.add('dragover'); };
    zone.ondragleave = () => { zone.classList.remove('dragover'); };
    zone.ondrop = (e) => {
      e.preventDefault();
      zone.classList.remove('dragover');
      const file = e.dataTransfer.files[0];
      if (file) handleImportFile(file);
    };
  }, 0);
}

function handleImportFile(file) {
  if (!file) return;
  if (!file.name.endsWith('.json')) {
    showToast('Please select a .json file', 'error');
    return;
  }
  const reader = new FileReader();
  reader.onload = (e) => {
    try {
      const data = JSON.parse(e.target.result);
      previewImportData(data);
    } catch (err) {
      showToast('Invalid JSON: ' + err.message, 'error');
      document.getElementById('import-preview').innerHTML =
        `<div class="empty-state"><div class="empty-state-icon">!</div><h3>Invalid JSON</h3><p>${escHtml(err.message)}</p></div>`;
    }
  };
  reader.readAsText(file);
}

function previewImportData(data) {
  if (!data || typeof data !== 'object') {
    showToast('Top-level JSON must be an object', 'error');
    return;
  }
  const members = data.members || [];
  const expenses = data.expenses || [];
  const el = document.getElementById('import-preview');
  el.innerHTML = `
    <div style="margin-bottom:20px">
      <h3 style="margin-bottom:8px">Preview</h3>
      <p style="color:var(--color-text-secondary);font-size:14px">
        ${members.length} member(s), ${expenses.length} expense(s)
      </p>
    </div>
    ${members.length > 0 ? `
      <div class="form-group">
        <label class="form-label">Members</label>
        <div style="display:flex;flex-wrap:wrap;gap:6px">
          ${members.map(m => `<span class="badge badge-blue">${escHtml(m.name || m.id)}</span>`).join('')}
        </div>
      </div>
    ` : ''}
    ${expenses.length > 0 ? `
      <div class="form-group">
        <label class="form-label">Expenses</label>
        <div class="table-container">
          <table><thead><tr><th>ID</th><th>Description</th><th>Amount</th><th>Type</th></tr></thead><tbody>
            ${expenses.map(e => `<tr>
              <td>${escHtml(e.expense_id || '?')}</td>
              <td>${escHtml(e.description || '')}</td>
              <td>${fmtINR(e.amount)}</td>
              <td><span class="badge badge-blue">${e.split_type || '?'}</span></td>
            </tr>`).join('')}
          </tbody></table>
        </div>
      </div>
    ` : ''}
    <button class="btn btn-primary" onclick="importBatch(this)" data-json='${JSON.stringify(data).replace(/'/g, "&#39;")}'>
      ${Icons.upload} Import Data
    </button>
  `;
}

async function importBatch(btn) {
  const raw = btn.getAttribute('data-json');
  if (!raw) return;
  try {
    const data = JSON.parse(raw);
    btn.disabled = true;
    btn.textContent = 'Importing...';
    await API.importBatch(data);
    showToast('Import successful!', 'success');
    App.navigate('/');
  } catch (e) {
    showToast(e.message, 'error');
    btn.disabled = false;
    btn.innerHTML = `${Icons.upload} Import Data`;
  }
}

/* ═══════════════════════════════════════════════════════════════════════════
   Add Expense Modal
   ═══════════════════════════════════════════════════════════════════════════ */

function openAddExpenseModal() {
  // Fetch member list first
  API.fetchMembers().then(memberData => {
    const members = memberData.members || [];
    let modalHtml = `
      <div class="form-row">
        <div class="form-group">
          <label class="form-label">Description</label>
          <input type="text" class="form-input" id="ae-desc" placeholder="e.g. Dinner at Taj">
        </div>
        <div class="form-group">
          <label class="form-label">Amount (INR)</label>
          <input type="number" class="form-input" id="ae-amount" placeholder="0.00" step="0.01" min="0.01" oninput="updateSplitPreview()">
          <p class="form-error" id="ae-amount-err" style="display:none"></p>
        </div>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label class="form-label">Paid by</label>
          <select class="form-select" id="ae-payer">
            ${members.map(m => `<option value="${m.id}">${m.name || m.id}</option>`).join('')}
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Date</label>
          <input type="date" class="form-input" id="ae-date" value="${new Date().toISOString().split('T')[0]}">
        </div>
      </div>
      <div class="form-group">
        <label class="form-label">Participants</label>
        <div class="checkbox-group" id="ae-participants">
          ${members.map(m => `
            <label class="checkbox-item" data-id="${m.id}">
              <input type="checkbox" value="${m.id}" onchange="this.parentElement.classList.toggle('checked',this.checked);updateSplitPreview()">
              ${m.name || m.id}
            </label>
          `).join('')}
        </div>
        <p class="form-error" id="ae-parts-err" style="display:none"></p>
      </div>
      <div class="form-group">
        <label class="form-label">Split Type</label>
        <div class="split-tabs" id="ae-split-type">
          <button class="split-tab active" data-type="equal" onclick="switchSplitTab(this,'equal')">Equal</button>
          <button class="split-tab" data-type="exact" onclick="switchSplitTab(this,'exact')">Exact</button>
          <button class="split-tab" data-type="percentage" onclick="switchSplitTab(this,'percentage')">Percentage</button>
        </div>
      </div>
      <div id="ae-split-details" style="margin-top:16px">
        <p style="color:var(--color-text-muted);font-size:14px" id="ae-split-info">Select participants to see the split.</p>
      </div>
    `;

    const { overlay, close } = Modal({
      title: 'Add Expense',
      body: modalHtml,
      footer: `
        <button class="btn btn-secondary" onclick="this.closest('.modal-overlay').querySelector('.modal-close').click()">Cancel</button>
        <button class="btn btn-primary" id="ae-submit-btn" onclick="submitAddExpense()">${Icons.plus} Add Expense</button>
      `,
      wide: true,
      onClose: () => { window._aeModal = null; },
    });
    window._aeModal = { overlay, close, members };
  }).catch(e => showToast('Failed to load members: ' + e.message, 'error'));
}

function switchSplitTab(btn, type) {
  document.querySelectorAll('#ae-split-type .split-tab').forEach(t => t.classList.remove('active'));
  btn.classList.add('active');
  window._aeSplitType = type;
  updateSplitPreview();
}

function getSelectedParticipants() {
  const checks = document.querySelectorAll('#ae-participants input:checked');
  return Array.from(checks).map(c => c.value);
}

function getAmount() {
  const val = document.getElementById('ae-amount')?.value;
  const err = document.getElementById('ae-amount-err');
  if (!val || isNaN(parseFloat(val)) || parseFloat(val) <= 0) {
    if (err) { err.style.display = 'block'; err.textContent = 'Amount must be a positive number'; }
    return null;
  }
  if (err) err.style.display = 'none';
  return parseFloat(val);
}

function updateSplitPreview() {
  const container = document.getElementById('ae-split-details');
  const info = document.getElementById('ae-split-info');
  if (!container) return;

  const participants = getSelectedParticipants();
  const amount = getAmount();
  const splitType = window._aeSplitType || 'equal';

  if (participants.length === 0) {
    container.innerHTML = '<p style="color:var(--color-text-muted);font-size:14px">Select participants to see the split.</p>';
    return;
  }
  if (amount === null) {
    container.innerHTML = '<p style="color:var(--color-text-muted);font-size:14px">Enter a valid amount to see the split.</p>';
    return;
  }

  const memberMap = {};
  if (window._aeModal?.members) {
    window._aeModal.members.forEach(m => { memberMap[m.id] = m.name || m.id; });
  }

  if (splitType === 'equal') {
    const share = amount / participants.length;
    container.innerHTML = `
      <div style="background:var(--color-primary-light);border-radius:var(--radius-sm);padding:12px 16px;margin-bottom:12px">
        <span style="font-size:13px;font-weight:600;color:var(--color-primary)">Equal Split</span>
        <span style="float:right;font-size:13px;color:var(--color-text-secondary)">
          ${participants.length} people &middot; ${fmtINR(share)} each
        </span>
      </div>
      ${participants.map(p => `
        <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--color-border-light)">
          <span>${escHtml(memberMap[p] || p)}</span>
          <span style="font-weight:600">${fmtINR(share)}</span>
        </div>
      `).join('')}
      <p style="font-size:12px;color:var(--color-text-muted);margin-top:8px">
        Rounding: remainders are distributed one paise at a time to the first participants in list order.
      </p>
    `;
  } else if (splitType === 'exact') {
    const perShare = (amount / participants.length);
    container.innerHTML = `
      ${participants.map((p, i) => `
        <div class="form-group" style="margin-bottom:10px">
          <label class="form-label">${escHtml(memberMap[p] || p)}</label>
          <input type="number" class="form-input ae-exact-input" data-participant="${p}"
            value="${(i === participants.length - 1 ? amount - (perShare * (participants.length - 1)) : perShare).toFixed(2)}"
            step="0.01" min="0" oninput="updateExactTotal()">
        </div>
      `).join('')}
      <div style="padding:10px 14px;border-radius:var(--radius-sm);font-size:13px;font-weight:600" id="ae-exact-summary">
        <span id="ae-exact-total"></span> / ${fmtINR(amount)}
      </div>
    `;
    setTimeout(updateExactTotal, 10);
  } else if (splitType === 'percentage') {
    const perPct = (100 / participants.length).toFixed(2);
    container.innerHTML = `
      ${participants.map((p, i) => `
        <div class="form-group" style="margin-bottom:10px">
          <label class="form-label">${escHtml(memberMap[p] || p)}</label>
          <div style="display:flex;align-items:center;gap:8px">
            <input type="number" class="form-input ae-pct-input" data-participant="${p}"
              value="${(i === participants.length - 1 ? (100 - parseFloat(perPct) * (participants.length - 1)) : parseFloat(perPct)).toFixed(2)}"
              step="0.01" min="0" max="100" oninput="updatePctTotal()" style="width:100px">
            <span style="font-size:13px;color:var(--color-text-muted)">%</span>
            <span style="font-size:14px;font-weight:600;margin-left:8px" class="ae-pct-amount">→ ${fmtINR(amount * parseFloat(perPct) / 100)}</span>
          </div>
        </div>
      `).join('')}
      <div style="padding:10px 14px;border-radius:var(--radius-sm);font-size:13px;font-weight:600" id="ae-pct-summary">
        <span id="ae-pct-total"></span> / 100%
      </div>
    `;
    setTimeout(updatePctTotal, 10);
  }
}

function updateExactTotal() {
  const inputs = document.querySelectorAll('.ae-exact-input');
  let total = 0;
  inputs.forEach(inp => { total += parseFloat(inp.value) || 0; });
  const amount = getAmount() || 0;
  const summary = document.getElementById('ae-exact-total');
  const box = document.getElementById('ae-exact-summary');
  if (summary && box) {
    summary.textContent = fmtINR(total);
    if (Math.abs(total - amount) < 0.01) {
      box.style.background = 'var(--color-green-bg)'; box.style.color = 'var(--color-green)';
    } else {
      box.style.background = 'var(--color-red-bg)'; box.style.color = 'var(--color-red)';
    }
  }
}

function updatePctTotal() {
  const inputs = document.querySelectorAll('.ae-pct-input');
  let total = 0;
  inputs.forEach(inp => { total += parseFloat(inp.value) || 0; });
  const summary = document.getElementById('ae-pct-total');
  const box = document.getElementById('ae-pct-summary');
  if (summary && box) {
    summary.textContent = total.toFixed(2) + '%';
    if (Math.abs(total - 100) < 0.01) {
      box.style.background = 'var(--color-green-bg)'; box.style.color = 'var(--color-green)';
    } else {
      box.style.background = 'var(--color-red-bg)'; box.style.color = 'var(--color-red)';
    }
  }
  // Update amount displays
  const amount = getAmount() || 0;
  document.querySelectorAll('.ae-pct-amount').forEach(el => {
    const input = el.previousElementSibling?.previousElementSibling;
    if (input) {
      const pct = parseFloat(input.value) || 0;
      el.textContent = '→ ' + fmtINR(amount * pct / 100);
    }
  });
}

async function submitAddExpense() {
  const desc = document.getElementById('ae-desc')?.value?.trim();
  const amountVal = document.getElementById('ae-amount')?.value;
  const payer = document.getElementById('ae-payer')?.value;
  const date = document.getElementById('ae-date')?.value;
  const participants = getSelectedParticipants();
  const splitType = window._aeSplitType || 'equal';

  // Validation
  if (!desc) return showToast('Please enter a description', 'error');
  if (!amountVal || isNaN(parseFloat(amountVal)) || parseFloat(amountVal) <= 0) return showToast('Enter a valid positive amount', 'error');
  if (!payer) return showToast('Please select a payer', 'error');
  if (participants.length === 0) return showToast('Please select at least one participant', 'error');

  const amount = parseFloat(parseFloat(amountVal).toFixed(2));

  const expense = {
    description: desc,
    amount: amount,
    payer: payer,
    participants: participants,
    split_type: splitType,
  };

  if (date) expense.timestamp = new Date(date).toISOString();

  // Handle split details
  if (splitType === 'exact') {
    const inputs = document.querySelectorAll('.ae-exact-input');
    if (inputs.length === 0) return showToast('Enter exact amounts', 'error');
    let total = 0;
    const details = [];
    inputs.forEach(inp => {
      const val = parseFloat(parseFloat(inp.value || '0').toFixed(2));
      if (val < 0) return showToast('Exact amounts must be non-negative', 'error');
      details.push({ member_id: inp.dataset.participant, value: val });
      total += val;
    });
    if (Math.abs(total - amount) > 0.005) return showToast(`Exact amounts (${total.toFixed(2)}) must sum to expense total (${amount.toFixed(2)})`, 'error');
    expense.split_details = details;
  } else if (splitType === 'percentage') {
    const inputs = document.querySelectorAll('.ae-pct-input');
    if (inputs.length === 0) return showToast('Enter percentages', 'error');
    let total = 0;
    const details = [];
    inputs.forEach(inp => {
      const val = parseFloat(parseFloat(inp.value || '0').toFixed(2));
      if (val < 0 || val > 100) return showToast('Percentages must be between 0 and 100', 'error');
      details.push({ member_id: inp.dataset.participant, value: val });
      total += val;
    });
    if (Math.abs(total - 100) > 0.01) return showToast(`Percentages must sum to 100% (current: ${total.toFixed(2)}%)`, 'error');
    expense.split_details = details;
  }

  try {
    await API.addExpense(expense);
    if (window._aeModal) window._aeModal.close();
    showToast('Expense added!', 'success');
    App.navigate('/');
  } catch (e) {
    showToast(e.message, 'error');
  }
}

/* ═══════════════════════════════════════════════════════════════════════════
   Settings Page
   ═══════════════════════════════════════════════════════════════════════════ */

function PageSettings() {
  const el = document.getElementById('page-content');
  el.innerHTML = `
    <div class="page-header">
      <h1 class="page-title">Settings</h1>
      <p class="page-subtitle">Application preferences and group details.</p>
    </div>
    <div class="section-card">
      <div class="section-card-header"><h3 class="section-card-title">General</h3></div>
      <div class="section-card-body">
        <div class="form-group">
          <label class="form-label">Default Currency</label>
          <input type="text" class="form-input" value="INR (Indian Rupee)" disabled style="max-width:300px">
          <p class="form-hint">Currently only INR is supported.</p>
        </div>
        <div class="form-group">
          <label class="form-label">Rounding</label>
          <input type="text" class="form-input" value="Half-Up to 2 decimal places (paise)" disabled style="max-width:400px">
          <p class="form-hint">All settlements use paise-level precision.</p>
        </div>
      </div>
    </div>
    <div class="section-card" style="margin-top:24px">
      <div class="section-card-header"><h3 class="section-card-title">Danger Zone</h3></div>
      <div class="section-card-body">
        <p style="color:var(--color-text-secondary);font-size:14px;margin-bottom:16px">
          Reset all data to the demo state. This will remove all manually added expenses and members.
        </p>
        <button class="btn btn-danger" onclick="resetAllData()">Reset All Data</button>
      </div>
    </div>
  `;
}

async function resetAllData() {
  if (!confirm('Reset all data? This cannot be undone.')) return;
  try {
    await API.resetStore();
    showToast('Data reset', 'success');
    App.navigate('/');
  } catch (e) {
    showToast(e.message, 'error');
  }
}

/* ═══════════════════════════════════════════════════════════════════════════
   Helpers
   ═══════════════════════════════════════════════════════════════════════════ */

function escHtml(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}