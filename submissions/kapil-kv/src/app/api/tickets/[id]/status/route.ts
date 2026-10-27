import { NextRequest } from "next/server";
import { connectDB } from "@/lib/db";
import { requireAuth } from "@/lib/api-auth";
import {
  successResponse,
  validationErrorResponse,
  notFoundResponse,
  errorResponse,
  serverErrorResponse,
} from "@/lib/api-response";
import { ticketIdParamsSchema, ticketStatusSchema } from "@/validators/ticket";
import { isValidTransition } from "@/services/sla-calculator";
import Ticket from "@/models/Ticket";
import { logger } from "@/lib/logger";
import type { TicketStatus } from "@/types";

/**
 * POST /api/tickets/[id]/status — Change ticket status
 */
export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const auth = await requireAuth(request);
    if (!("adminId" in auth)) return auth;

    await connectDB();

    const { id } = await params;
    const { error: idError } = ticketIdParamsSchema.validate({ id });
    if (idError) return validationErrorResponse("Invalid ticket ID.");

    const body = await request.json();
    const { error, value } = ticketStatusSchema.validate(body);
    if (error) return validationErrorResponse(error.details.map((d) => d.message).join("; "));

    const ticket = await Ticket.findById(id);
    if (!ticket) return notFoundResponse("Ticket");

    const currentStatus = ticket.status as TicketStatus;
    const newStatus = value.status as TicketStatus;

    // Validate status transition
    if (!isValidTransition(currentStatus, newStatus)) {
      return errorResponse(
        "INVALID_TRANSITION",
        `Cannot transition from ${currentStatus} to ${newStatus}.`,
        422,
      );
    }

    // Build status history entry
    const statusEntry = {
      status: newStatus,
      timestamp: new Date(),
      reason: value.reason || "",
    };

    // Build update operation
    const updateFields: Record<string, unknown> = {
      status: newStatus,
      $push: { statusHistory: statusEntry },
    };

    // If resolving, set resolvedAt
    if (newStatus === "RESOLVED") {
      updateFields.resolvedAt = new Date();
    }

    // Use findOneAndUpdate for atomic operation
    const updatedTicket = await Ticket.findByIdAndUpdate(
      id,
      updateFields,
      { new: true, runValidators: true },
    ).populate("assigneeGroup", "name");

    logger.info("Ticket status changed", {
      ticketNumber: ticket.ticketNumber,
      from: currentStatus,
      to: newStatus,
    });

    return successResponse({ ticket: updatedTicket });
  } catch (e) {
    logger.error("Error updating ticket status", { error: (e as Error).message });
    return serverErrorResponse();
  }
}