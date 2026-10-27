/**
 * Seed Script: Admin Account
 *
 * Creates the initial admin account from environment variables.
 * Idempotent: will not overwrite an existing admin password, but will
 * create the admin if not present.
 *
 * Usage: npm run seed:admin
 */

import mongoose from "mongoose";
import bcrypt from "bcryptjs";

// Load env vars manually for script usage
import * as dotenv from "dotenv";
import * as path from "path";

// Try to load .env.local first, then .env
const envPaths = [
  path.resolve(process.cwd(), ".env.local"),
  path.resolve(process.cwd(), ".env"),
];

for (const envPath of envPaths) {
  try {
    dotenv.config({ path: envPath });
  } catch {
    // File doesn't exist, skip
  }
}

const MONGODB_URI = process.env.MONGODB_URI || "mongodb://127.0.0.1:27017/sla_tracker";
const ADMIN_EMAIL = process.env.ADMIN_EMAIL || "admin@example.com";
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || "ChangeMe123!";

async function seedAdmin() {
  console.log("🌱 Seeding admin account...");
  console.log(`   MongoDB URI: ${MONGODB_URI.replace(/\/\/.*@/, "//<credentials>@")}`);
  console.log(`   Admin Email: ${ADMIN_EMAIL}`);

  await mongoose.connect(MONGODB_URI);

  // Use the model directly (import after connection to avoid issues)
  const Admin = mongoose.models.Admin || mongoose.model(
    "Admin",
    new mongoose.Schema(
      {
        email: { type: String, required: true, unique: true, lowercase: true, trim: true },
        passwordHash: { type: String, required: true, select: false },
        role: { type: String, required: true, default: "ADMIN", enum: ["ADMIN"] },
      },
      { timestamps: true },
    ),
  );

  const existing = await Admin.findOne({ email: ADMIN_EMAIL.toLowerCase() });

  if (existing) {
    console.log("   ✓ Admin account already exists. No changes made.");
    console.log(`   Admin ID: ${existing._id}`);
  } else {
    const salt = await bcrypt.genSalt(12);
    const passwordHash = await bcrypt.hash(ADMIN_PASSWORD, salt);

    const admin = await Admin.create({
      email: ADMIN_EMAIL.toLowerCase(),
      passwordHash,
      role: "ADMIN",
    });

    console.log("   ✓ Admin account created successfully.");
    console.log(`   Admin ID: ${admin._id}`);
  }

  console.log("\n   ⚠ Remember to change the default password after first login!");
  console.log("   Use the Settings page or update .env and re-seed.\n");

  await mongoose.disconnect();
  process.exit(0);
}

seedAdmin().catch((err) => {
  console.error("❌ Seed failed:", err.message);
  process.exit(1);
});