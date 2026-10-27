import { NextRequest } from "next/server";
import { connectDB } from "@/lib/db";
import { requireAuth } from "@/lib/api-auth";
import {
  successResponse,
  validationErrorResponse,
  serverErrorResponse,
  errorResponse,
} from "@/lib/api-response";
import { createTicketSchema, ticketQuerySchema } from "@/validators/ticket";
import Ticket from "@/models/Ticket";
import { logger } from "@/lib/logger";

/**
 * GET /api/tickets — List tickets with pagination, search, and filters
 */
export async function GET(request: NextRequest) {
  try {
    const auth = await requireAuth(request);
    if (!("adminId" in auth)) return auth;

    await connectDB();

    const { searchParams } = new URL(request.url);
    const params: Record<string, unknown> = {};

    searchParams.forEach((value, key) => {
      // Handle array params (multiple of same key)
      if (params[key] !== undefined) {
        if (Array.isArray(params[key])) {
          (params[key] as string[]).push(value);
        } else {
          params[key] = [params[key] as string, value];
        }
      } else {
        params[key] = value;
      }
    });

    const { error, value } = ticketQuerySchema.validate(params, { stripUnknown: true });
    if (error) return validationErrorResponse(error.details.map((d) => d.message).join("; "));

    const { page, limit, search, priority, status, assigneeGroup, dateFrom, dateTo, sortBy, sortOrder } = value;

    // Build query
    const filter: Record<string, unknown> = {};

    if (search) {
      filter.$or = [
        { ticketNumber: { $regex: search, $options: "i" } },
        { title: { $regex: search, $options: "i" } },
      ];
    }

    if (priority) {
      filter.priority = Array.isArray(priority) ? { $in: priority } : priority;
    }

    if (status) {
      filter.status = Array.isArray(status) ? { $in: status } : status;
    }

    if (assigneeGroup) {
      filter.assigneeGroup = assigneeGroup;
    }

    if (dateFrom || dateTo) {
      filter.createdAt = {};
      if (dateFrom) {
        (filter.createdAt as Record<string, unknown>).$gte = new Date(dateFrom as string);
      }
      if (dateTo) {
        (filter.createdAt as Record<string, unknown>).$lte = new Date(dateTo as string);
      }
    }

    const skip = (page - 1) * limit;
    const sortField = sortBy || "createdAt";
    const sortDir = sortOrder === "asc" ? 1 : -1;

    const [tickets, total] = await Promise.all([
      Ticket.find(filter)
        .sort({ [sortField]: sortDir })
        .skip(skip)
        .limit(limit)
        .populate("assigneeGroup", "name")
        .lean(),
      Ticket.countDocuments(filter),
    ]);

    return successResponse({
      tickets,
      pagination: {
        page,
        limit,
        total,
        totalPages: Math.ceil(total / limit),
      },
    });
  } catch (e) {
    logger.error("Error fetching tickets", { error: (e as Error).message });
    return serverErrorResponse();
  }
}

/**
 * POST /api/tickets — Create a new ticket
 */
export async function POST(request: NextRequest) {
  try {
    const auth = await requireAuth(request);
    if (!("adminId" in auth)) return auth;

    await connectDB();

    const body = await request.json();
    const { error, value } = createTicketSchema.validate(body);
    if (error) return validationErrorResponse(error.details.map((d) => d.message).join("; "));

    // Generate ticket number: TK-YYYYMMDD-XXXX
    const today = new Date();
    const dateStr = today.toISOString().slice(0, 10).replace(/-/g, "");
    const countToday = await Ticket.countDocuments({
      ticketNumber: { $regex: `^TK-${dateStr}-` },
    });
    const ticketNumber = `TK-${dateStr}-${String(countToday + 1).padStart(4, "0")}`;

    const ticket = await Ticket.create({
      ticketNumber,
      title: value.title,
      description: value.description || "",
      priority: value.priority,
      status: value.status || "OPEN",
      assigneeGroup: value.assigneeGroup || null,
      createdBy: auth.adminId,
      statusHistory: [
        {
          status: value.status || "OPEN",
          timestamp: new Date(),
          reason: "Ticket created",
        },
      ],
    });

    logger.info("Ticket created", { ticketNumber });

    return successResponse(await ticket.populate("assigneeGroup", "name"), 201);
  } catch (e) {
    logger.error("Error creating ticket", { error: (e as Error).message });
    return serverErrorResponse();
  }
}