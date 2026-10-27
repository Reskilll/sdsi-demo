import { getEnv } from "./env";

type LogLevel = "debug" | "info" | "warn" | "error";

function shouldLog(level: LogLevel): boolean {
  const env = getEnv();
  if (env.NODE_ENV === "test") return level === "error";
  if (env.NODE_ENV === "production") return level !== "debug";
  return true;
}

function formatMessage(level: LogLevel, message: string, meta?: Record<string, unknown>): void {
  if (!shouldLog(level)) return;

  const timestamp = new Date().toISOString();
  const prefix = `[${timestamp}] [${level.toUpperCase()}]`;
  const safeMeta = meta ? sanitizeForLogging(meta) : undefined;

  if (safeMeta) {
    console[level](`${prefix} ${message}`, safeMeta);
  } else {
    console[level](`${prefix} ${message}`);
  }
}

/** Remove sensitive keys before logging */
function sanitizeForLogging(obj: Record<string, unknown>): Record<string, unknown> {
  const sensitiveKeys = new Set([
    "password",
    "passwordHash",
    "sessionSecret",
    "token",
    "cookie",
    "secret",
    "authorization",
    "apiKey",
    "api_key",
    "accessToken",
    "access_token",
    "refreshToken",
    "refresh_token",
  ]);

  const sanitized: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(obj)) {
    if (sensitiveKeys.has(key)) {
      sanitized[key] = "[REDACTED]";
    } else if (typeof value === "object" && value !== null && !Array.isArray(value)) {
      sanitized[key] = sanitizeForLogging(value as Record<string, unknown>);
    } else {
      sanitized[key] = value;
    }
  }
  return sanitized;
}

export const logger = {
  debug: (msg: string, meta?: Record<string, unknown>) => formatMessage("debug", msg, meta),
  info: (msg: string, meta?: Record<string, unknown>) => formatMessage("info", msg, meta),
  warn: (msg: string, meta?: Record<string, unknown>) => formatMessage("warn", msg, meta),
  error: (msg: string, meta?: Record<string, unknown>) => formatMessage("error", msg, meta),
};