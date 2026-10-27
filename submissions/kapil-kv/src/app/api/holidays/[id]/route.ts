import { NextRequest } from "next/server";
import { connectDB } from "@/lib/db";
import { requireAuth } from "@/lib/api-auth";
import {
  successResponse,
  validationErrorResponse,
  notFoundResponse,
  serverErrorResponse,
} from "@/lib/api-response";
import { updateHolidaySchema, holidayIdParamsSchema } from "@/validators/holiday";
import Holiday from "@/models/Holiday";
import { logger } from "@/lib/logger";

/**
 * PATCH /api/holidays/[id] — Update a holiday
 */
export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const auth = await requireAuth(request);
    if (!("adminId" in auth)) return auth;

    await connectDB();

    const { id } = await params;
    const { error: idError } = holidayIdParamsSchema.validate({ id });
    if (idError) return validationErrorResponse("Invalid holiday ID.");

    const body = await request.json();
    const { error, value } = updateHolidaySchema.validate(body);
    if (error) return validationErrorResponse(error.details.map((d) => d.message).join("; "));

    const holiday = await Holiday.findByIdAndUpdate(
      id,
      { $set: value },
      { new: true, runValidators: true },
    );

    if (!holiday) return notFoundResponse("Holiday");

    logger.info("Holiday updated", { name: holiday.name });

    return successResponse({ holiday });
  } catch (e) {
    logger.error("Error updating holiday", { error: (e as Error).message });
    return serverErrorResponse();
  }
}

/**
 * DELETE /api/holidays/[id] — Delete a holiday
 */
export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const auth = await requireAuth(request);
    if (!("adminId" in auth)) return auth;

    await connectDB();

    const { id } = await params;
    const { error: idError } = holidayIdParamsSchema.validate({ id });
    if (idError) return validationErrorResponse("Invalid holiday ID.");

    const holiday = await Holiday.findByIdAndDelete(id);
    if (!holiday) return notFoundResponse("Holiday");

    logger.info("Holiday deleted", { name: holiday.name });

    return successResponse({ message: "Holiday deleted successfully." });
  } catch (e) {
    logger.error("Error deleting holiday", { error: (e as Error).message });
    return serverErrorResponse();
  }
}