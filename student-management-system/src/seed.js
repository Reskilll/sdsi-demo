'use strict';

// Idempotent seed: ensures the default admin exists and adds sample students.
const bcrypt = require('bcryptjs');
const db = require('./db');
const config = require('./config');

function seedAdmin() {
  const existing = db.prepare('SELECT id FROM users WHERE email = ?').get(config.admin.email);
  if (existing) {
    console.log(`Admin already exists: ${config.admin.email}`);
    return;
  }
  const hash = bcrypt.hashSync(config.admin.password, config.bcryptRounds);
  db.prepare('INSERT INTO users (email, password, role) VALUES (?, ?, ?)').run(
    config.admin.email,
    hash,
    'admin'
  );
  console.log(`Created admin: ${config.admin.email}`);
}

function seedStudents() {
  const count = db.prepare('SELECT COUNT(*) AS n FROM students').get().n;
  if (count > 0) {
    console.log(`Students already present (${count}). Skipping sample data.`);
    return;
  }
  const samples = [
    ['Ada', 'Lovelace', 'ada.lovelace@school.edu', 17, 'Grade 11', 1],
    ['Alan', 'Turing', 'alan.turing@school.edu', 16, 'Grade 10', 1],
    ['Grace', 'Hopper', 'grace.hopper@school.edu', 18, 'Grade 12', 1],
    ['Katherine', 'Johnson', 'katherine.johnson@school.edu', 15, 'Grade 9', 0],
  ];
  const insert = db.prepare(
    'INSERT INTO students (first_name,last_name,email,age,grade,enrolled) VALUES (?,?,?,?,?,?)'
  );
  const tx = db.transaction((rows) => rows.forEach((r) => insert.run(...r)));
  tx(samples);
  console.log(`Inserted ${samples.length} sample students.`);
}

seedAdmin();
seedStudents();
console.log('Seed complete.');
