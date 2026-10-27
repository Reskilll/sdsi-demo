/**
 * Application shell — sidebar, routing, and global state.
 */

const App = {
  _groupData: null,
  _currentPage: '',

  routes: {
    '/':              { name: 'Overview',   icon: Icons.dashboard, page: PageOverview,  label: 'Overview' },
    '/expenses':      { name: 'Expenses',   icon: Icons.expenses,  page: PageExpenses,  label: 'Expenses' },
    '/members':       { name: 'Members',    icon: Icons.members,   page: PageMembers,   label: 'Members' },
    '/settle-up':     { name: 'Settle Up',  icon: Icons.settleUp,  page: PageSettleUp,  label: 'Settle Up' },
    '/import':        { name: 'Import',     icon: Icons.import,    page: PageImport,    label: 'Import' },
    '/settings':      { name: 'Settings',   icon: Icons.settings,  page: PageSettings,  label: 'Settings' },
  },

  init() {
    this.renderShell();
    this.handleRoute();
    window.addEventListener('popstate', () => this.handleRoute());
  },

  renderShell() {
    const app = document.getElementById('app');
    const navLinks = Object.entries(this.routes).map(([path, r]) => `
      <a href="${path}" data-path="${path}" onclick="App.navigate(event,'${path}')">
        ${r.icon} ${r.label}
      </a>
    `).join('');

    app.innerHTML = `
      <div class="app-layout">
        <aside class="sidebar" id="sidebar">
          <div class="sidebar-brand">
            <div class="sidebar-brand-icon">SW</div>
            <div>
              <div class="sidebar-brand-text">SplitWise Lite</div>
              <div class="sidebar-brand-sub">Expense Splitter</div>
            </div>
          </div>
          <nav class="sidebar-nav">${navLinks}</nav>
          <div class="sidebar-footer">SplitWise Lite v1.0</div>
        </aside>
        <main class="main-content">
          <header class="topbar">
            <div class="topbar-left">
              <button class="menu-toggle" onclick="App.toggleSidebar()" aria-label="Menu">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
              </button>
              <span style="font-weight:600;font-size:15px" id="topbar-title">Group Overview</span>
            </div>
            <div class="topbar-right">
              <button class="btn btn-primary btn-sm" onclick="App.openAddExpense()">${Icons.plus} Add Expense</button>
            </div>
          </header>
          <div class="page" id="page-content"></div>
        </main>
      </div>
    `;

    // Close sidebar on outside click (mobile)
    document.addEventListener('click', (e) => {
      const sidebar = document.getElementById('sidebar');
      if (!sidebar) return;
      if (sidebar.classList.contains('open') && !sidebar.contains(e.target) && !e.target.closest('.menu-toggle')) {
        sidebar.classList.remove('open');
      }
    });
  },

  toggleSidebar() {
    document.getElementById('sidebar')?.classList.toggle('open');
  },

  navigate(eventOrPath, explicitPath) {
    if (typeof eventOrPath === 'string') {
      // Direct path navigation
      window.history.pushState({}, '', eventOrPath);
      this.handleRoute();
      return;
    }
    // Event-based navigation
    if (eventOrPath && eventOrPath.preventDefault) {
      eventOrPath.preventDefault();
      const path = eventOrPath.target?.closest('a')?.getAttribute('data-path') ||
                   eventOrPath.target?.getAttribute('data-path') || explicitPath;
      if (path) {
        window.history.pushState({}, '', path);
        this.handleRoute();
      }
    }
  },

  handleRoute() {
    const path = window.location.pathname || '/';
    const route = this.routes[path] || this.routes['/'];
    this._currentPage = path;

    // Update active nav link
    document.querySelectorAll('.sidebar-nav a').forEach(a => {
      a.classList.toggle('active', a.getAttribute('data-path') === path);
    });

    // Close mobile sidebar after navigation
    document.getElementById('sidebar')?.classList.remove('open');

    // Update topbar title
    const titleEl = document.getElementById('topbar-title');
    if (titleEl) titleEl.textContent = route.name;

    // Render page
    if (route.page) route.page();
  },

  openAddExpense() {
    openAddExpenseModal();
  },

  async addMemberFromModal(btn) {
    const id = document.getElementById('new-member-id')?.value?.trim();
    const name = document.getElementById('new-member-name')?.value?.trim();
    if (!id) return showToast('Member ID is required', 'error');
    try {
      await API.addMember({ id, name: name || id });
      showToast('Member added!', 'success');
      // Close the modal
      const overlay = btn.closest('.modal-overlay');
      if (overlay) overlay.querySelector('.modal-close')?.click();
      this.navigate('/members');
    } catch (e) {
      showToast(e.message, 'error');
    }
  },
};

// Boot
document.addEventListener('DOMContentLoaded', () => App.init());