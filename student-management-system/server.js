'use strict';

const path = require('path');
const express = require('express');
const helmet = require('helmet');
const cors = require('cors');
const cookieParser = require('cookie-parser');
const rateLimit = require('express-rate-limit');

const config = require('./src/config');
const { notFound, errorHandler } = require('./src/middleware/errorHandler');
const authRoutes = require('./src/routes/auth');
const studentRoutes = require('./src/routes/students');

// Ensure the default admin + sample data exist on boot.
require('./src/seed');

const app = express();

// Behind a proxy (e.g. in production) trust X-Forwarded-* for secure cookies & rate limiting.
if (config.isProd) app.set('trust proxy', 1);

// ---- Security middleware ----
app.use(
  helmet({
    contentSecurityPolicy: {
      directives: {
        defaultSrc: ["'self'"],
        scriptSrc: ["'self'"],
        styleSrc: ["'self'", "'unsafe-inline'"],
        imgSrc: ["'self'", 'data:'],
        connectSrc: ["'self'"],
        objectSrc: ["'none'"],
        frameAncestors: ["'none'"],
      },
    },
  })
);
app.use(
  cors({
    origin: config.cors.origin,
    credentials: true,
  })
);
app.use(express.json({ limit: '100kb' })); // cap body size -> basic DoS protection
app.use(cookieParser());

// Global, lenient rate limit across the whole API.
app.use(
  '/api',
  rateLimit({
    windowMs: 60 * 1000,
    max: 120,
    standardHeaders: true,
    legacyHeaders: false,
    message: { error: 'Too many requests. Slow down.' },
  })
);

// ---- API routes ----
app.get('/api/health', (req, res) => res.json({ status: 'ok', time: new Date().toISOString() }));
app.use('/api/auth', authRoutes);
app.use('/api/students', studentRoutes);

// ---- Static frontend ----
app.use(express.static(path.join(__dirname, 'public')));

// ---- 404 + error handling ----
app.use('/api', notFound);
app.use(errorHandler);

if (require.main === module) {
  app.listen(config.port, () => {
    console.log(`\nStudent Management System running at http://localhost:${config.port}`);
    console.log(`Environment: ${config.env}`);
    console.log(`Default admin: ${config.admin.email} / ${config.admin.password}\n`);
  });
}

module.exports = app;
