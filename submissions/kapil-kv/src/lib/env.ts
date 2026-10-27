import Joi from "joi";

/** Safe environment variable access — all values validated at startup */

/**
 * Email validation regex — avoids Joi's built-in TLD list which can fail
 * to load in some environments (e.g. newer Node.js versions on Windows).
 */
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

interface EnvConfig {
  NODE_ENV: "development" | "production" | "test";
  MONGODB_URI: string;
  ADMIN_EMAIL: string;
  ADMIN_PASSWORD: string;
  SESSION_SECRET: string;
  APP_TIMEZONE: string;
  BUSINESS_START_HOUR: number;
  BUSINESS_END_HOUR: number;
  SESSION_COOKIE_NAME: string;
  COOKIE_MAX_AGE_SECONDS: number;
  LOGIN_RATE_LIMIT_MAX: number;
  LOGIN_RATE_LIMIT_WINDOW_MS: number;
}

function envSchema(): Joi.ObjectSchema<EnvConfig> {
  return Joi.object({
    NODE_ENV: Joi.string().valid("development", "production", "test").default("development"),
    MONGODB_URI: Joi.string().uri().required(),
    ADMIN_EMAIL: Joi.string().pattern(EMAIL_PATTERN, "email").required(),
    ADMIN_PASSWORD: Joi.string().min(8).required(),
    SESSION_SECRET: Joi.string().min(32).required(),
    APP_TIMEZONE: Joi.string().default("Asia/Kolkata"),
    BUSINESS_START_HOUR: Joi.number().integer().min(0).max(23).default(9),
    BUSINESS_END_HOUR: Joi.number().integer().min(0).max(23).default(18),
    SESSION_COOKIE_NAME: Joi.string().default("sla_tracker_session"),
    COOKIE_MAX_AGE_SECONDS: Joi.number().integer().min(60).default(86400),
    LOGIN_RATE_LIMIT_MAX: Joi.number().integer().min(1).default(5),
    LOGIN_RATE_LIMIT_WINDOW_MS: Joi.number().integer().min(1000).default(900000),
  });
}

let _env: EnvConfig | null = null;

export function getEnv(): EnvConfig {
  if (_env) return _env;

  const raw = {
    NODE_ENV: process.env.NODE_ENV,
    MONGODB_URI: process.env.MONGODB_URI,
    ADMIN_EMAIL: process.env.ADMIN_EMAIL,
    ADMIN_PASSWORD: process.env.ADMIN_PASSWORD,
    SESSION_SECRET: process.env.SESSION_SECRET,
    APP_TIMEZONE: process.env.APP_TIMEZONE,
    BUSINESS_START_HOUR: process.env.BUSINESS_START_HOUR
      ? parseInt(process.env.BUSINESS_START_HOUR, 10)
      : undefined,
    BUSINESS_END_HOUR: process.env.BUSINESS_END_HOUR
      ? parseInt(process.env.BUSINESS_END_HOUR, 10)
      : undefined,
    SESSION_COOKIE_NAME: process.env.SESSION_COOKIE_NAME,
    COOKIE_MAX_AGE_SECONDS: process.env.COOKIE_MAX_AGE_SECONDS
      ? parseInt(process.env.COOKIE_MAX_AGE_SECONDS, 10)
      : undefined,
    LOGIN_RATE_LIMIT_MAX: process.env.LOGIN_RATE_LIMIT_MAX
      ? parseInt(process.env.LOGIN_RATE_LIMIT_MAX, 10)
      : undefined,
    LOGIN_RATE_LIMIT_WINDOW_MS: process.env.LOGIN_RATE_LIMIT_WINDOW_MS
      ? parseInt(process.env.LOGIN_RATE_LIMIT_WINDOW_MS, 10)
      : undefined,
  };

  const { error, value } = envSchema().validate(raw, {
    allowUnknown: false,
    stripUnknown: true,
  });

  if (error) {
    const details = error.details.map((d) => d.message).join("; ");
    throw new Error(`Invalid environment configuration: ${details}`);
  }

  _env = value as EnvConfig;
  return _env;
}