import { NextRequest } from "next/server";
import { connectDB } from "@/lib/db";
import { createSession } from "@/lib/auth";
import { successResponse, errorResponse, validationErrorResponse } from "@/lib/api-response";
import { loginSchema } from "@/validators/auth";
import Admin from "@/models/Admin";
import { logger } from "@/lib/logger";
import { getEnv } from "@/lib/env";

// Simple in-memory rate limiter (resets on server restart)
const loginAttempts = new Map<string, { count: number; firstAttempt: number }>();

function isRateLimited(ip: string): boolean {
  const env = getEnv();
  const now = Date.now();
  const record = loginAttempts.get(ip);

  if (!record) return false;
  if (now - record.firstAttempt > env.LOGIN_RATE_LIMIT_WINDOW_MS) {
    loginAttempts.delete(ip);
    return false;
  }
  return record.count >= env.LOGIN_RATE_LIMIT_MAX;
}

function recordLoginAttempt(ip: string): void {
  const now = Date.now();
  const env = getEnv();
  const record = loginAttempts.get(ip);

  if (!record || now - record.firstAttempt > env.LOGIN_RATE_LIMIT_WINDOW_MS) {
    loginAttempts.set(ip, { count: 1, firstAttempt: now });
  } else {
    record.count++;
  }
}

export async function POST(request: NextRequest) {
  try {
    await connectDB();

    // Rate limiting
    const ip = request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || "unknown";
    if (isRateLimited(ip)) {
      return errorResponse(
        "RATE_LIMITED",
        "Too many login attempts. Please try again later.",
        429,
      );
    }

    const body = await request.json();
    const { error, value } = loginSchema.validate(body);

    if (error) {
      return validationErrorResponse(error.details.map((d) => d.message).join("; "));
    }

    const { email, password } = value;

    // Find admin by email (case-insensitive)
    const admin = await Admin.findOne({ email: email.toLowerCase() }).select("+passwordHash");

    // Generic error: don't reveal whether email exists
    if (!admin) {
      recordLoginAttempt(ip);
      logger.warn("Login attempt with unknown email", { email: email.toLowerCase() });
      return errorResponse("AUTH_FAILED", "Invalid email or password.", 401);
    }

    // Compare password
    const isValid = await (admin as any).comparePassword(password);
    if (!isValid) {
      recordLoginAttempt(ip);
      logger.warn("Login attempt with wrong password", { email: email.toLowerCase() });
      return errorResponse("AUTH_FAILED", "Invalid email or password.", 401);
    }

    // Clear rate limit on success
    loginAttempts.delete(ip);

    // Create session
    await createSession({
      adminId: admin._id as string,
      email: admin.email,
      role: admin.role,
    });

    logger.info("Admin login successful", { email: admin.email });

    return successResponse({
      admin: {
        id: admin._id,
        email: admin.email,
        role: admin.role,
      },
    });
  } catch (e) {
    logger.error("Login error", { error: (e as Error).message });
    return errorResponse("SERVER_ERROR", "An unexpected error occurred.", 500);
  }
}