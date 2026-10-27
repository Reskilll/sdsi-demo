import { NextRequest } from "next/server";
import { connectDB } from "@/lib/db";
import { requireAuth } from "@/lib/api-auth";
import {
  successResponse,
  validationErrorResponse,
  notFoundResponse,
  serverErrorResponse,
} from "@/lib/api-response";
import { updatePolicySchema, policyIdParamsSchema } from "@/validators/policy";
import SLAPolicy from "@/models/SLAPolicy";
import { logger } from "@/lib/logger";

/**
 * GET /api/sla-policies/[id] — Get a single SLA policy
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const auth = await requireAuth(request);
    if (!("adminId" in auth)) return auth;

    await connectDB();

    const { id } = await params;
    const { error } = policyIdParamsSchema.validate({ id });
    if (error) return validationErrorResponse("Invalid policy ID.");

    const policy = await SLAPolicy.findById(id).lean();
    if (!policy) return notFoundResponse("SLA Policy");

    return successResponse({ policy });
  } catch (e) {
    logger.error("Error fetching SLA policy", { error: (e as Error).message });
    return serverErrorResponse();
  }
}

/**
 * PATCH /api/sla-policies/[id] — Update an SLA policy
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
    const { error: idError } = policyIdParamsSchema.validate({ id });
    if (idError) return validationErrorResponse("Invalid policy ID.");

    const body = await request.json();
    const { error, value } = updatePolicySchema.validate(body);
    if (error) return validationErrorResponse(error.details.map((d) => d.message).join("; "));

    const policy = await SLAPolicy.findByIdAndUpdate(
      id,
      { $set: value },
      { new: true, runValidators: true },
    );

    if (!policy) return notFoundResponse("SLA Policy");

    logger.info("SLA policy updated", { priority: policy.priority });

    return successResponse({ policy });
  } catch (e) {
    logger.error("Error updating SLA policy", { error: (e as Error).message });
    return serverErrorResponse();
  }
}