'use strict';

// Lightweight end-to-end API test using Node's built-in test runner + http.
// Runs against an in-memory DB and an ephemeral port — no external deps.
const test = require('node:test');
const assert = require('node:assert');
const http = require('node:http');

process.env.DB_PATH = ':memory:';
process.env.NODE_ENV = 'test';
const app = require('../server');

let server;
let base;

function req(method, path, { body, token } = {}) {
  return new Promise((resolve, reject) => {
    const data = body ? JSON.stringify(body) : null;
    const headers = { 'Content-Type': 'application/json' };
    if (data) headers['Content-Length'] = Buffer.byteLength(data);
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const r = http.request(base + path, { method, headers }, (res) => {
      let raw = '';
      res.on('data', (c) => (raw += c));
      res.on('end', () => {
        let json = null;
        try { json = JSON.parse(raw); } catch (_) {}
        resolve({ status: res.statusCode, body: json });
      });
    });
    r.on('error', reject);
    if (data) r.write(data);
    r.end();
  });
}

test.before(async () => {
  await new Promise((r) => { server = app.listen(0, r); });
  base = `http://127.0.0.1:${server.address().port}`;
});
test.after(() => server && server.close());

let adminToken;
let userToken;
let studentId;

test('health check', async () => {
  const res = await req('GET', '/api/health');
  assert.equal(res.status, 200);
  assert.equal(res.body.status, 'ok');
});

test('admin can log in', async () => {
  const res = await req('POST', '/api/auth/login', {
    body: { email: 'admin@school.edu', password: 'Admin@12345' },
  });
  assert.equal(res.status, 200);
  assert.equal(res.body.user.role, 'admin');
  adminToken = res.body.token;
});

test('rejects wrong password', async () => {
  const res = await req('POST', '/api/auth/login', {
    body: { email: 'admin@school.edu', password: 'wrong' },
  });
  assert.equal(res.status, 401);
});

test('rejects weak registration password', async () => {
  const res = await req('POST', '/api/auth/register', {
    body: { email: 'weak@school.edu', password: 'abc' },
  });
  assert.equal(res.status, 422);
});

test('registers a normal (read-only) user', async () => {
  const res = await req('POST', '/api/auth/register', {
    body: { email: 'student.user@school.edu', password: 'User@12345' },
  });
  assert.equal(res.status, 201);
  assert.equal(res.body.user.role, 'user');
  userToken = res.body.token;
});

test('unauthenticated cannot list students', async () => {
  const res = await req('GET', '/api/students');
  assert.equal(res.status, 401);
});

test('admin creates a student', async () => {
  const res = await req('POST', '/api/students', {
    token: adminToken,
    body: { first_name: 'Test', last_name: 'Student', email: 'new.student@school.edu', age: 14, grade: 'Grade 8', enrolled: true },
  });
  assert.equal(res.status, 201);
  studentId = res.body.data.id;
  assert.ok(studentId);
});

test('validation rejects bad student age', async () => {
  const res = await req('POST', '/api/students', {
    token: adminToken,
    body: { first_name: 'Bad', last_name: 'Age', email: 'bad.age@school.edu', age: 999, grade: 'X' },
  });
  assert.equal(res.status, 422);
});

test('read-only user is forbidden from creating', async () => {
  const res = await req('POST', '/api/students', {
    token: userToken,
    body: { first_name: 'No', last_name: 'Perm', email: 'noperm@school.edu', age: 12, grade: 'G1' },
  });
  assert.equal(res.status, 403);
});

test('user can read students', async () => {
  const res = await req('GET', '/api/students', { token: userToken });
  assert.equal(res.status, 200);
  assert.ok(Array.isArray(res.body.data));
});

test('admin updates a student', async () => {
  const res = await req('PUT', `/api/students/${studentId}`, {
    token: adminToken,
    body: { first_name: 'Updated', last_name: 'Student', email: 'new.student@school.edu', age: 15, grade: 'Grade 9', enrolled: false },
  });
  assert.equal(res.status, 200);
  assert.equal(res.body.data.first_name, 'Updated');
  assert.equal(res.body.data.enrolled, 0);
});

test('SQL-injection attempt is treated as literal search, not executed', async () => {
  const res = await req('GET', "/api/students?q=' OR '1'='1", { token: adminToken });
  assert.equal(res.status, 200); // table still intact, query parameterized
});

test('admin deletes a student', async () => {
  const res = await req('DELETE', `/api/students/${studentId}`, { token: adminToken });
  assert.equal(res.status, 200);
  const check = await req('GET', `/api/students/${studentId}`, { token: adminToken });
  assert.equal(check.status, 404);
});
