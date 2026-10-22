'use strict';

// ---- Tiny helpers ----
const $ = (sel) => document.querySelector(sel);
const api = async (url, opts = {}) => {
  const res = await fetch(url, {
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  });
  let body = null;
  try { body = await res.json(); } catch (_) { /* no body */ }
  if (!res.ok) {
    const msg = body && (body.error || (body.details && body.details.map((d) => d.message).join(' '))) || 'Request failed.';
    throw new Error(msg);
  }
  return body;
};

function toast(msg, type = 'ok') {
  const t = $('#toast');
  t.textContent = msg;
  t.className = `toast ${type}`;
  t.hidden = false;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => { t.hidden = true; }, 2600);
}

// Prevent XSS: text inserted via textContent, never innerHTML of user data.
const state = { user: null, page: 1, limit: 10, q: '', pages: 1 };

// ---- Auth ----
async function refreshSession() {
  try {
    const { user } = await api('/api/auth/me');
    state.user = user;
    showApp();
  } catch (_) {
    state.user = null;
    showAuth();
  }
}

function showAuth() {
  $('#authView').hidden = false;
  $('#appView').hidden = true;
  $('#session').hidden = true;
}

function showApp() {
  $('#authView').hidden = true;
  $('#appView').hidden = false;
  $('#session').hidden = false;
  $('#whoami').textContent = `${state.user.email} (${state.user.role})`;
  const isAdmin = state.user.role === 'admin';
  $('#addBtn').hidden = !isAdmin;
  loadStudents();
}

// Tab switching
document.querySelectorAll('.tab').forEach((tab) => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach((t) => t.classList.remove('active'));
    tab.classList.add('active');
    const isLogin = tab.dataset.tab === 'login';
    $('#loginForm').hidden = !isLogin;
    $('#registerForm').hidden = isLogin;
  });
});

$('#loginForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const f = e.target;
  try {
    await api('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email: f.email.value, password: f.password.value }),
    });
    toast('Welcome back!');
    await refreshSession();
  } catch (err) { toast(err.message, 'err'); }
});

$('#registerForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const f = e.target;
  try {
    await api('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email: f.email.value, password: f.password.value }),
    });
    toast('Account created!');
    await refreshSession();
  } catch (err) { toast(err.message, 'err'); }
});

$('#logoutBtn').addEventListener('click', async () => {
  await api('/api/auth/logout', { method: 'POST' });
  state.user = null;
  showAuth();
  toast('Logged out.');
});

// ---- Students CRUD ----
async function loadStudents() {
  try {
    const params = new URLSearchParams({ q: state.q, page: state.page, limit: state.limit });
    const { data, page, pages, total } = await api(`/api/students?${params}`);
    state.pages = pages;
    renderRows(data);
    $('#pageInfo').textContent = `Page ${page} of ${pages} • ${total} student(s)`;
    $('#prevBtn').disabled = page <= 1;
    $('#nextBtn').disabled = page >= pages;
    $('#empty').hidden = data.length > 0;
  } catch (err) { toast(err.message, 'err'); }
}

function renderRows(students) {
  const tbody = $('#rows');
  tbody.textContent = '';
  const isAdmin = state.user && state.user.role === 'admin';

  students.forEach((s) => {
    const tr = document.createElement('tr');
    const cells = [
      s.id,
      `${s.first_name} ${s.last_name}`,
      s.email,
      s.age,
      s.grade,
    ];
    cells.forEach((val) => {
      const td = document.createElement('td');
      td.textContent = val;
      tr.appendChild(td);
    });

    const statusTd = document.createElement('td');
    const badge = document.createElement('span');
    badge.className = `badge ${s.enrolled ? 'on' : 'off'}`;
    badge.textContent = s.enrolled ? 'Enrolled' : 'Inactive';
    statusTd.appendChild(badge);
    tr.appendChild(statusTd);

    const actionsTd = document.createElement('td');
    actionsTd.className = 'actions-col';
    if (isAdmin) {
      const wrap = document.createElement('div');
      wrap.className = 'row-actions';
      const edit = document.createElement('button');
      edit.className = 'btn btn-ghost btn-sm';
      edit.textContent = 'Edit';
      edit.addEventListener('click', () => openModal(s));
      const del = document.createElement('button');
      del.className = 'btn btn-danger btn-sm';
      del.textContent = 'Delete';
      del.addEventListener('click', () => removeStudent(s));
      wrap.append(edit, del);
      actionsTd.appendChild(wrap);
    } else {
      actionsTd.textContent = '—';
    }
    tr.appendChild(actionsTd);
    tbody.appendChild(tr);
  });
}

async function removeStudent(s) {
  if (!confirm(`Delete ${s.first_name} ${s.last_name}?`)) return;
  try {
    await api(`/api/students/${s.id}`, { method: 'DELETE' });
    toast('Student deleted.');
    loadStudents();
  } catch (err) { toast(err.message, 'err'); }
}

// ---- Modal ----
function openModal(student) {
  const f = $('#studentForm');
  f.reset();
  if (student) {
    $('#modalTitle').textContent = 'Edit student';
    f.id.value = student.id;
    f.first_name.value = student.first_name;
    f.last_name.value = student.last_name;
    f.email.value = student.email;
    f.age.value = student.age;
    f.grade.value = student.grade;
    f.enrolled.checked = !!student.enrolled;
  } else {
    $('#modalTitle').textContent = 'Add student';
    f.id.value = '';
    f.enrolled.checked = true;
  }
  $('#modal').hidden = false;
}

function closeModal() { $('#modal').hidden = true; }

$('#addBtn').addEventListener('click', () => openModal(null));
$('#cancelBtn').addEventListener('click', closeModal);

$('#studentForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const f = e.target;
  const payload = {
    first_name: f.first_name.value.trim(),
    last_name: f.last_name.value.trim(),
    email: f.email.value.trim(),
    age: Number(f.age.value),
    grade: f.grade.value.trim(),
    enrolled: f.enrolled.checked,
  };
  const id = f.id.value;
  try {
    if (id) {
      await api(`/api/students/${id}`, { method: 'PUT', body: JSON.stringify(payload) });
      toast('Student updated.');
    } else {
      await api('/api/students', { method: 'POST', body: JSON.stringify(payload) });
      toast('Student added.');
    }
    closeModal();
    loadStudents();
  } catch (err) { toast(err.message, 'err'); }
});

// ---- Search + pagination ----
let searchTimer;
$('#search').addEventListener('input', (e) => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    state.q = e.target.value.trim();
    state.page = 1;
    loadStudents();
  }, 300);
});
$('#prevBtn').addEventListener('click', () => { if (state.page > 1) { state.page--; loadStudents(); } });
$('#nextBtn').addEventListener('click', () => { if (state.page < state.pages) { state.page++; loadStudents(); } });

// Boot
refreshSession();
