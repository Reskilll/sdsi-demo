import { NextRequest } from "next/server";
import { connectDB } from "@/lib/db";
import { requireAuth } from "@/lib/api-auth";
import {
  successResponse,
  validationErrorResponse,
  notFoundResponse,
  conflictResponse,
  serverErrorResponse,
} from "@/lib/api-response";
import { updateGroupSchema, groupIdParamsSchema } from "@/validators/assignee-group";
import AssigneeGroup from "@/models/AssigneeGroup";
import Ticket from "@/models/Ticket";
import { logger } from "@/lib/logger";

/**
 * PATCH /api/assignee-groups/[id] — Update an assignee group
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
    const { error: idError } = groupIdParamsSchema.validate({ id });
    if (idError) return validationErrorResponse("Invalid group ID.");

    const body = await request.json();
    const { error, value } = updateGroupSchema.validate(body);
    if (error) return validationErrorResponse(error.details.map((d) => d.message).join("; "));

    // If renaming, check uniqueness
    if (value.name) {
      const existing = await AssigneeGroup.findOne({
        name: value.name,
        _id: { $ne: id },
      });
      if (existing) {
        return conflictResponse("An assignee group with this name already exists.");
      }
    }

    const group = await AssigneeGroup.findByIdAndUpdate(
      id,
      { $set: value },
      { new: true, runValidators: true },
    );

    if (!group) return notFoundResponse("Assignee Group");

    logger.info("Assignee group updated", { name: group.name });

    return successResponse({ group });
  } catch (e) {
    logger.error("Error updating assignee group", { error: (e as Error).message });
    return serverErrorResponse();
  }
}

/**
 * DELETE /api/assignee-groups/[id] — Delete an assignee group
 * Only allowed if no tickets reference the group.
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
    const { error: idError } = groupIdParamsSchema.validate({ id });
    if (idError) return validationErrorResponse("Invalid group ID.");

    // Check for referenced tickets
    const ticketCount = await Ticket.countDocuments({ assigneeGroup: id });
    if (ticketCount > 0) {
      return conflictResponse(
        `Cannot delete this group because it is referenced by ${ticketCount} ticket(s). Reassign those tickets first.`,
      );
    }

    const group = await AssigneeGroup.findByIdAndDelete(id);
    if (!group) return notFoundResponse("Assignee Group");

    logger.info("Assignee group deleted", { name: group.name });

    return successResponse({ message: "Assignee group deleted successfully." });
  } catch (e) {
    logger.error("Error deleting assignee group", { error: (e as Error).message });
    return serverErrorResponse();
  }
}