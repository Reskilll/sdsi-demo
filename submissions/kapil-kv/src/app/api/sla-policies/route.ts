import { NextRequest } from "next/server";
import { connectDB } from "@/lib/db";
import { requireAuth } from "@/lib/api-auth";
import { successResponse, serverErrorResponse } from "@/lib/api-response";
import SLAPolicy from "@/models/SLAPolicy";
import { logger } from "@/lib/logger";

/**
 * GET /api/sla-policies — List SLA policies
 */
export async function GET(request: NextRequest) {
  try {
    const auth = await requireAuth(request);
    if (!("adminId" in auth)) return auth;

    await connectDB();

    const policies = await SLAPolicy.find().sort({ priority: 1 }).lean();
    return successResponse({ policies });
  } catch (e) {
    logger.error("Error fetching SLA policies", { error: (e as Error).message });
    return serverErrorResponse();
  }
}