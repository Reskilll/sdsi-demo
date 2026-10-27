/**
 * Seed Script: Sample Data
 *
 * Imports sample tickets, SLA policies, and holidays from sample-data/ JSON files.
 * Validates data with Joi before writing to MongoDB.
 * Idempotent: skips records that already exist.
 *
 * Usage: npm run seed:sample
 */

import mongoose from "mongoose";
import * as fs from "fs";
import * as path from "path";
import Joi from "joi";

// Load env vars manually
import * as dotenv from "dotenv";
const envPaths = [
  path.resolve(process.cwd(), ".env.local"),
  path.resolve(process.cwd(), ".env"),
];
for (const envPath of envPaths) {
  try {
    dotenv.config({ path: envPath });
  } catch {
    // File doesn't exist
  }
}

const MONGODB_URI = process.env.MONGODB_URI || "mongodb://127.0.0.1:27017/sla_tracker";

const slaPolicySchema = Joi.object({
  priority: Joi.string().valid("P1", "P2", "P3", "P4").required(),
  targetBusinessHours: Joi.number().min(0.25).required(),
  isActive: Joi.boolean().default(true),
});

const holidaySchema = Joi.object({
  date: Joi.date().iso().required(),
  name: Joi.string().required().min(1).max(200),
  isActive: Joi.boolean().default(true),
});

const statusEventSchema = Joi.object({
  status: Joi.string().valid("OPEN", "IN_PROGRESS", "ON_HOLD", "RESOLVED").required(),
  timestamp: Joi.date().iso().required(),
  reason: Joi.string().allow("").default(""),
});

const ticketSchema = Joi.object({
  ticketNumber: Joi.string().required(),
  title: Joi.string().required().min(1),
  description: Joi.string().allow("").default(""),
  priority: Joi.string().valid("P1", "P2", "P3", "P4").required(),
  status: Joi.string().valid("OPEN", "IN_PROGRESS", "ON_HOLD", "RESOLVED").required(),
  assigneeGroup: Joi.string().allow(null).default(null),
  createdAt: Joi.date().iso().required(),
  resolvedAt: Joi.date().iso().allow(null).default(null),
  statusHistory: Joi.array().items(statusEventSchema).min(1).required(),
});

function readJsonFile(filename: string): unknown {
  const filePath = path.resolve(process.cwd(), "sample-data", filename);
  if (!fs.existsSync(filePath)) {
    console.log(`   ⚠ File not found: ${filePath}. Skipping.`);
    return null;
  }
  const raw = fs.readFileSync(filePath, "utf-8");
  return JSON.parse(raw);
}

async function seedSampleData() {
  console.log("🌱 Seeding sample data...\n");

  await mongoose.connect(MONGODB_URI);

  const SLAPolicy = mongoose.models.SLAPolicy || mongoose.model(
    "SLAPolicy",
    new mongoose.Schema({
      priority: { type: String, required: true, unique: true, enum: ["P1", "P2", "P3", "P4"] },
      targetBusinessHours: { type: Number, required: true, min: 0.25 },
      isActive: { type: Boolean, default: true },
    }, { timestamps: true }),
  );

  const Holiday = mongoose.models.Holiday || mongoose.model(
    "Holiday",
    new mongoose.Schema({
      date: { type: Date, required: true, unique: true },
      name: { type: String, required: true },
      isActive: { type: Boolean, default: true },
    }, { timestamps: true }),
  );

  const AssigneeGroup = mongoose.models.AssigneeGroup || mongoose.model(
    "AssigneeGroup",
    new mongoose.Schema({
      name: { type: String, required: true, unique: true },
      description: { type: String, default: "" },
      isActive: { type: Boolean, default: true },
    }, { timestamps: true }),
  );

  const Ticket = mongoose.models.Ticket || mongoose.model(
    "Ticket",
    new mongoose.Schema({
      ticketNumber: { type: String, required: true, unique: true },
      title: { type: String, required: true },
      description: { type: String, default: "" },
      priority: { type: String, required: true, enum: ["P1", "P2", "P3", "P4"] },
      status: { type: String, required: true, enum: ["OPEN", "IN_PROGRESS", "ON_HOLD", "RESOLVED"] },
      assigneeGroup: { type: mongoose.Schema.Types.ObjectId, ref: "AssigneeGroup", default: null },
      resolvedAt: { type: Date, default: null },
      statusHistory: { type: [new mongoose.Schema({
        status: { type: String, required: true, enum: ["OPEN", "IN_PROGRESS", "ON_HOLD", "RESOLVED"] },
        timestamp: { type: Date, required: true },
        reason: { type: String, default: "" },
      }, { _id: false })], default: [] },
      createdBy: { type: mongoose.Schema.Types.ObjectId, ref: "Admin", default: null },
    }, { timestamps: true }),
  );

  // --- Seed SLA Policies ---
  console.log("📋 SLA Policies...");
  const policiesData = readJsonFile("sla_policy.json");

  if (policiesData && Array.isArray(policiesData)) {
    for (const rawPolicy of policiesData) {
      const { error, value } = slaPolicySchema.validate(rawPolicy);
      if (error) {
        console.log(`   ✗ Validation error for ${rawPolicy.priority}: ${error.message}`);
        continue;
      }
      const existing = await SLAPolicy.findOne({ priority: value.priority });
      if (existing) {
        console.log(`   → P${value.priority.indexOf("P") + 1} already exists. Skipping.`);
      } else {
        await SLAPolicy.create(value);
        console.log(`   ✓ Created SLA policy for ${value.priority}`);
      }
    }
  }

  // --- Seed Holidays ---
  console.log("\n📅 Holidays...");
  const holidaysData = readJsonFile("holidays.json");

  if (holidaysData && Array.isArray(holidaysData)) {
    for (const rawHoliday of holidaysData) {
      const { error, value } = holidaySchema.validate(rawHoliday);
      if (error) {
        console.log(`   ✗ Validation error: ${error.message}`);
        continue;
      }
      // Normalize date to midnight UTC
      const dateOnly = new Date(value.date);
      dateOnly.setUTCHours(0, 0, 0, 0);
      const existing = await Holiday.findOne({
        date: { $gte: dateOnly, $lt: new Date(dateOnly.getTime() + 86400000) },
      });
      if (existing) {
        console.log(`   → ${value.name} already exists. Skipping.`);
      } else {
        await Holiday.create({ ...value, date: dateOnly });
        console.log(`   ✓ Created holiday: ${value.name}`);
      }
    }
  }

  // --- Seed Assignee Groups ---
  console.log("\n👥 Assignee Groups...");
  const groupNames = ["Network Team", "Server Team", "Help Desk", "Security Team"];
  const groupMap: Record<string, mongoose.Types.ObjectId> = {};
  for (const name of groupNames) {
    const existing = await AssigneeGroup.findOne({ name });
    if (existing) {
      groupMap[name] = existing._id as mongoose.Types.ObjectId;
      console.log(`   → ${name} already exists. Skipping.`);
    } else {
      const group = await AssigneeGroup.create({ name, isActive: true });
      groupMap[name] = group._id as mongoose.Types.ObjectId;
      console.log(`   ✓ Created group: ${name}`);
    }
  }

  // --- Seed Tickets ---
  console.log("\n🎫 Tickets...");
  const ticketsData = readJsonFile("tickets.json");

  if (ticketsData && Array.isArray(ticketsData)) {
    for (const rawTicket of ticketsData) {
      const { error, value } = ticketSchema.validate(rawTicket);
      if (error) {
        console.log(`   ✗ Validation error for "${rawTicket.title}": ${error.message}`);
        continue;
      }

      const existing = await Ticket.findOne({ ticketNumber: value.ticketNumber });
      if (existing) {
        console.log(`   → ${value.ticketNumber} already exists. Skipping.`);
        continue;
      }

      // Resolve assigneeGroup name to ObjectId
      let groupId: mongoose.Types.ObjectId | null = null;
      if (typeof value.assigneeGroup === "string" && groupMap[value.assigneeGroup]) {
        groupId = groupMap[value.assigneeGroup];
      }

      await Ticket.create({
        ...value,
        assigneeGroup: groupId,
        createdAt: new Date(value.createdAt),
        resolvedAt: value.resolvedAt ? new Date(value.resolvedAt) : null,
        statusHistory: value.statusHistory.map((e: any) => ({
          ...e,
          timestamp: new Date(e.timestamp),
        })),
      });
      console.log(`   ✓ Created ticket: ${value.ticketNumber}`);
    }
  }

  console.log("\n✅ Sample data seeding complete!\n");
  await mongoose.disconnect();
  process.exit(0);
}

seedSampleData().catch((err) => {
  console.error("❌ Seed failed:", err.message);
  process.exit(1);
});