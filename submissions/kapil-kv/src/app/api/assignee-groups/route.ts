import { NextRequest } from "next/server";
import { connectDB } from "@/lib/db";
import { requireAuth } from "@/lib/api-auth";
import {
  successResponse,
  validationErrorResponse,
  conflictResponse,
  serverErrorResponse,
} from "@/lib/api-response";
import { createGroupSchema } from "@/validators/assignee-group";
import AssigneeGroup from "@/models/AssigneeGroup";
import { logger } from "@/lib/logger";

/**
 * GET /api/assignee-groups — List assignee groups
 */
export async function GET(request: NextRequest) {
  try {
    const auth = await requireAuth(request);
    if (!("adminId" in auth)) return auth;

    await connectDB();

    const { searchParams } = new URL(request.url);
    const includeInactive = searchParams.get("includeInactive") === "true";

    const filter = includeInactive ? {} : { isActive: true };
    const groups = await AssigneeGroup.find(filter).sort({ name: 1 }).lean();

    return successResponse({ groups });
  } catch (e) {
    logger.error("Error fetching assignee groups", { error: (e as Error).message });
    return serverErrorResponse();
  }
}

/**
 * POST /api/assignee-groups — Create a new assignee group
 */
export async function POST(request: NextRequest) {
  try {
    const auth = await requireAuth(request);
    if (!("adminId" in auth)) return auth;

    await connectDB();

    const body = await request.json();
    const { error, value } = createGroupSchema.validate(body);
    if (error) return validationErrorResponse(error.details.map((d) => d.message).join("; "));

    // Check for duplicate name
    const existing = await AssigneeGroup.findOne({ name: value.name });
    if (existing) {
      return conflictResponse("An assignee group with this name already exists.");
    }

    const group = await AssigneeGroup.create({
      name: value.name,
      description: value.description || "",
      isActive: value.isActive !== false,
    });

    logger.info("Assignee group created", { name: group.name });

    return successResponse({ group }, 201);
  } catch (e) {
    logger.error("Error creating assignee group", { error: (e as Error).message });
    return serverErrorResponse();
  }
}