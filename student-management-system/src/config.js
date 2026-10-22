'use strict';

require('dotenv').config();

const required = (key, fallback) => {
  const value = process.env[key];
  if (value === undefined || value === '') {
    if (fallback !== undefined) return fallback;
    throw new Error(`Missing required environment variable: ${key}`);
  }
  return value;
};

const config = {
  env: process.env.NODE_ENV || 'development',
  port: parseInt(process.env.PORT || '4000', 10),

  jwt: {
    secret: required('JWT_SECRET', 'insecure-dev-secret-change-me'),
    expiresIn: process.env.JWT_EXPIRES_IN || '2h',
  },

  cors: {
    origin: (process.env.CORS_ORIGIN || 'http://localhost:4000')
      .split(',')
      .map((o) => o.trim()),
  },

  admin: {
    email: process.env.ADMIN_EMAIL || 'admin@school.edu',
    password: process.env.ADMIN_PASSWORD || 'Admin@12345',
  },

  bcryptRounds: 12,
};

config.isProd = config.env === 'production';

if (config.isProd && config.jwt.secret.includes('insecure')) {
  throw new Error('Refusing to start in production with an insecure JWT_SECRET.');
}

module.exports = config;
