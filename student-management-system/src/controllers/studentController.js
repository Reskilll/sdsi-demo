'use strict';

const db = require('../db');

// All statements are prepared/parameterized -> SQL injection safe.
const stmts = {
  insert: db.prepare(`
    INSERT INTO students (first_name, last_name, email, age, grade, enrolled)
    VALUES (@first_name, @last_name, @email, @age, @grade, @enrolled)
  `),
  findById: db.prepare('SELECT * FROM students WHERE id = ?'),
  findByEmail: db.prepare('SELECT * FROM students WHERE email = ?'),
  update: db.prepare(`
    UPDATE students
    SET first_name=@first_name, last_name=@last_name, email=@email,
        age=@age, grade=@grade, enrolled=@enrolled, updated_at=datetime('now')
    WHERE id=@id
  `),
  remove: db.prepare('DELETE FROM students WHERE id = ?'),
  count: db.prepare('SELECT COUNT(*) AS n FROM students WHERE (@q = \'\' OR first_name LIKE @like OR last_name LIKE @like OR email LIKE @like)'),
  list: db.prepare(`
    SELECT * FROM students
    WHERE (@q = '' OR first_name LIKE @like OR last_name LIKE @like OR email LIKE @like)
    ORDER BY id DESC
    LIMIT @limit OFFSET @offset
  `),
};

function listStudents(req, res, next) {
  try {
    const q = (req.query.q || '').toString().trim();
    const page = Math.max(1, parseInt(req.query.page || '1', 10) || 1);
    const limit = Math.min(100, Math.max(1, parseInt(req.query.limit || '20', 10) || 20));
    const offset = (page - 1) * limit;
    const params = { q, like: `%${q}%`, limit, offset };
    const data = stmts.list.all(params);
    const total = stmts.count.get({ q, like: `%${q}%` }).n;
    return res.json({ data, page, limit, total, pages: Math.ceil(total / limit) || 1 });
  } catch (err) {
    return next(err);
  }
}

function getStudent(req, res, next) {
  try {
    const student = stmts.findById.get(req.params.id);
    if (!student) return res.status(404).json({ error: 'Student not found.' });
    return res.json({ data: student });
  } catch (err) {
    return next(err);
  }
}

function createStudent(req, res, next) {
  try {
    const payload = normalize(req.body);
    if (stmts.findByEmail.get(payload.email)) {
      return res.status(409).json({ error: 'A student with this email already exists.' });
    }
    const info = stmts.insert.run(payload);
    return res.status(201).json({ data: stmts.findById.get(info.lastInsertRowid) });
  } catch (err) {
    return next(err);
  }
}

function updateStudent(req, res, next) {
  try {
    const existing = stmts.findById.get(req.params.id);
    if (!existing) return res.status(404).json({ error: 'Student not found.' });

    const payload = normalize(req.body);
    const clash = stmts.findByEmail.get(payload.email);
    if (clash && clash.id !== existing.id) {
      return res.status(409).json({ error: 'Another student already uses this email.' });
    }
    stmts.update.run({ ...payload, id: existing.id });
    return res.json({ data: stmts.findById.get(existing.id) });
  } catch (err) {
    return next(err);
  }
}

function deleteStudent(req, res, next) {
  try {
    const info = stmts.remove.run(req.params.id);
    if (info.changes === 0) return res.status(404).json({ error: 'Student not found.' });
    return res.json({ message: 'Student deleted.' });
  } catch (err) {
    return next(err);
  }
}

function normalize(body) {
  return {
    first_name: body.first_name,
    last_name: body.last_name,
    email: body.email,
    age: body.age,
    grade: body.grade,
    enrolled: body.enrolled === undefined ? 1 : body.enrolled ? 1 : 0,
  };
}

module.exports = { listStudents, getStudent, createStudent, updateStudent, deleteStudent };
