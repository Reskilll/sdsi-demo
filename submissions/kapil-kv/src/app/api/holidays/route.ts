import { NextRequest } from "next/server";
import { connectDB } from "@/lib/db";
import { requireAuth } from "@/lib/api-auth";
import {
  successResponse,
  validationErrorResponse,
  conflictResponse,
  serverErrorResponse,
} from "@/lib/api-response";
import { createHolidaySchema } from "@/validators/holiday";
import Holiday from "@/models/Holiday";
import { logger } from "@/lib/logger";

/**
 * GET /api/holidays — List holidays
 */
export async function GET(request: NextRequest) {
  try {
    const auth = await requireAuth(request);
    if (!("adminId" in auth)) return auth;

    await connectDB();

    const { searchParams } = new URL(request.url);
    const includeInactive = searchParams.get("includeInactive") === "true";

    const filter = includeInactive ? {} : { isActive: true };
    const holidays = await Holiday.find(filter).sort({ date: 1 }).lean();

    return successResponse({ holidays });
  } catch (e) {
    logger.error("Error fetching holidays", { error: (e as Error).message });
    return serverErrorResponse();
  }
}

/**
 * POST /api/holidays — Create a new holiday
 */
export async function POST(request: NextRequest) {
  try {
    const auth = await requireAuth(request);
    if (!("adminId" in auth)) return auth;

    await connectDB();

    const body = await request.json();
    const { error, value } = createHolidaySchema.validate(body);
    if (error) return validationErrorResponse(error.details.map((d) => d.message).join("; "));

    // Check for duplicate date (store date-only, normalize to midnight UTC for consistency)
    const dateOnly = new Date(value.date);
    dateOnly.setUTCHours(0, 0, 0, 0);

    const existing = await Holiday.findOne({
      date: {
        $gte: dateOnly,
        $lt: new Date(dateOnly.getTime() + 86400000),
      },
    });

    if (existing) {
      return conflictResponse("A holiday already exists for this date.");
    }

    const holiday = await Holiday.create({
      date: dateOnly,
      name: value.name,
      isActive: value.isActive !== false,
    });

    logger.info("Holiday created", { name: holiday.name, date: dateOnly });

    return successResponse({ holiday }, 201);
  } catch (e) {
    logger.error("Error creating holiday", { error: (e as Error).message });
    return serverErrorResponse();
  }
}