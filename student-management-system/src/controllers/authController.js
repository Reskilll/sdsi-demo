'use strict';

const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const db = require('../db');
const config = require('../config');

function signToken(user) {
  return jwt.sign(
    { sub: user.id, email: user.email, role: user.role },
    config.jwt.secret,
    { expiresIn: config.jwt.expiresIn }
  );
}

function setAuthCookie(res, token) {
  res.cookie('token', token, {
    httpOnly: true, // not readable by JS -> mitigates XSS token theft
    secure: config.isProd, // HTTPS-only in production
    sameSite: 'strict', // mitigates CSRF
    maxAge: 2 * 60 * 60 * 1000,
  });
}

const insertUser = db.prepare(
  'INSERT INTO users (email, password, role) VALUES (?, ?, ?)'
);
const findUserByEmail = db.prepare('SELECT * FROM users WHERE email = ?');

async function register(req, res, next) {
  try {
    const { email, password } = req.body;
    if (findUserByEmail.get(email)) {
      return res.status(409).json({ error: 'An account with this email already exists.' });
    }
    const hash = await bcrypt.hash(password, config.bcryptRounds);
    // Self-registration always creates a plain 'user'. Admins are seeded.
    const info = insertUser.run(email, hash, 'user');
    const user = { id: info.lastInsertRowid, email, role: 'user' };
    const token = signToken(user);
    setAuthCookie(res, token);
    return res.status(201).json({ user: { id: user.id, email: user.email, role: user.role }, token });
  } catch (err) {
    return next(err);
  }
}

async function login(req, res, next) {
  try {
    const { email, password } = req.body;
    const user = findUserByEmail.get(email);
    // Always run a compare to reduce user-enumeration timing differences.
    const hash = user ? user.password : '$2a$12$invalidinvalidinvalidinvalidinvalidinvalidinv';
    const ok = await bcrypt.compare(password, hash);
    if (!user || !ok) {
      return res.status(401).json({ error: 'Invalid email or password.' });
    }
    const token = signToken(user);
    setAuthCookie(res, token);
    return res.json({ user: { id: user.id, email: user.email, role: user.role }, token });
  } catch (err) {
    return next(err);
  }
}

function logout(req, res) {
  res.clearCookie('token');
  return res.json({ message: 'Logged out.' });
}

function me(req, res) {
  return res.json({ user: req.user });
}

module.exports = { register, login, logout, me };
