// Test environment setup — sets required env vars before tests run

// Use bracket notation to avoid read-only TypeScript errors
Object.assign(process.env, {
  NODE_ENV: "test",
  MONGODB_URI: "mongodb://127.0.0.1:27017/sla_tracker_test",
  ADMIN_EMAIL: "admin@test.com",
  ADMIN_PASSWORD: "TestPass123!",
  SESSION_SECRET: "test_secret_32_chars_long_minimum",
  APP_TIMEZONE: "Asia/Kolkata",
  BUSINESS_START_HOUR: "9",
  BUSINESS_END_HOUR: "18",
});