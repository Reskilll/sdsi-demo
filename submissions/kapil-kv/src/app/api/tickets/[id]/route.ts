import { NextRequest } from "next/server";
import { connectDB } from "@/lib/db";
import { requireAuth } from "@/lib/api-auth";
import {
  successResponse,
  validationErrorResponse,
  notFoundResponse,
  serverErrorResponse,
} from "@/lib/api-response";
import { updateTicketSchema, ticketIdParamsSchema } from "@/validators/ticket";
import Ticket from "@/models/Ticket";
import { logger } from "@/lib/logger";

/**
 * GET /api/tickets/[id] — Get ticket details with SLA
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
    const { error } = ticketIdParamsSchema.validate({ id });
    if (error) return validationErrorResponse("Invalid ticket ID.");

    const ticket = await Ticket.findById(id).populate("assigneeGroup", "name").lean();
    if (!ticket) return notFoundResponse("Ticket");

    return successResponse({ ticket });
  } catch (e) {
    logger.error("Error fetching ticket", { error: (e as Error).message });
    return serverErrorResponse();
  }
}

/**
 * PATCH /api/tickets/[id] — Update ticket fields
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
    const { error: idError } = ticketIdParamsSchema.validate({ id });
    if (idError) return validationErrorResponse("Invalid ticket ID.");

    const body = await request.json();
    const { error, value } = updateTicketSchema.validate(body);
    if (error) return validationErrorResponse(error.details.map((d) => d.message).join("; "));

    const ticket = await Ticket.findByIdAndUpdate(
      id,
      { $set: value },
      { new: true, runValidators: true },
    ).populate("assigneeGroup", "name");

    if (!ticket) return notFoundResponse("Ticket");

    logger.info("Ticket updated", { ticketNumber: ticket.ticketNumber });

    return successResponse({ ticket });
  } catch (e) {
    logger.error("Error updating ticket", { error: (e as Error).message });
    return serverErrorResponse();
  }
}