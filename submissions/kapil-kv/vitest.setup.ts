// Test environment setup — sets required env vars before tests run
process.env.NODE_ENV = "test";
process.env.MONGODB_URI = "mongodb://127.0.0.1:27017/sla_tracker_test";
process.env.ADMIN_EMAIL = "admin@test.com";
process.env.ADMIN_PASSWORD = "TestPass123!";
process.env.SESSION_SECRET = "test_secret_32_chars_long_minimum";
process.env.APP_TIMEZONE = "Asia/Kolkata";
process.env.BUSINESS_START_HOUR = "9";
process.env.BUSINESS_END_HOUR = "18";