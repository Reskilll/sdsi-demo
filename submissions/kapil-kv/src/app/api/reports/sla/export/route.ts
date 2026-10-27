import { NextRequest, NextResponse } from "next/server";
import { connectDB } from "@/lib/db";
import { requireAuth } from "@/lib/api-auth";
import { serverErrorResponse } from "@/lib/api-response";
import Ticket from "@/models/Ticket";
import SLAPolicy from "@/models/SLAPolicy";
import Holiday from "@/models/Holiday";
import { calculateSla, DEFAULT_SLA_TARGETS } from "@/services/sla-calculator";
import { buildCalendarConfig } from "@/services/business-calendar";
import { logger } from "@/lib/logger";
import type { Priority, TicketStatus } from "@/types";

/**
 * GET /api/reports/sla/export — Export SLA report as CSV
 */
export async function GET(request: NextRequest) {
  try {
    const auth = await requireAuth(request);
    if (!("adminId" in auth)) return auth;

    await connectDB();

    const { searchParams } = new URL(request.url);
    const priority = searchParams.get("priority");
    const status = searchParams.get("status");
    const dateFrom = searchParams.get("dateFrom");
    const dateTo = searchParams.get("dateTo");

    const filter: Record<string, unknown> = {};
    if (priority) filter.priority = priority;
    if (status) filter.status = status;
    if (dateFrom || dateTo) {
      filter.createdAt = {};
      if (dateFrom) (filter.createdAt as Record<string, unknown>).$gte = new Date(dateFrom);
      if (dateTo) (filter.createdAt as Record<string, unknown>).$lte = new Date(dateTo);
    }

    const [tickets, policies, holidays] = await Promise.all([
      Ticket.find(filter).populate("assigneeGroup", "name").lean(),
      SLAPolicy.find().lean(),
      Holiday.find({ isActive: true }).lean(),
    ]);

    const policyMap: Record<Priority, number> = { ...DEFAULT_SLA_TARGETS };
    for (const p of policies) {
      if (p.isActive) {
        policyMap[p.priority] = p.targetBusinessHours * 60;
      }
    }

    const calendarConfig = buildCalendarConfig(
      holidays.map((h) => new Date(h.date)),
    );

    const now = new Date();

    // CSV header
    const headers = [
      "Ticket Number",
      "Title",
      "Priority",
      "Status",
      "Assignee Group",
      "Created At",
      "Resolved At",
      "Elapsed Business Minutes",
      "SLA Target Minutes",
      "Due By",
      "Is Breached",
      "Breach Minutes",
      "SLA Status",
    ];

    // Build CSV rows
    const rows = tickets.map((ticket) => {
      const sla = calculateSla(
        ticket.statusHistory,
        ticket.priority as Priority,
        ticket.status as TicketStatus,
        ticket.resolvedAt ? new Date(ticket.resolvedAt) : null,
        now,
        policyMap,
        calendarConfig,
      );

      return [
        ticket.ticketNumber,
        `"${(ticket.title || "").replace(/"/g, '""')}"`,
        ticket.priority,
        ticket.status,
        (ticket.assigneeGroup as any)?.name || "Unassigned",
        ticket.createdAt ? new Date(ticket.createdAt).toISOString() : "",
        ticket.resolvedAt ? new Date(ticket.resolvedAt).toISOString() : "",
        sla.elapsedBusinessMinutes,
        sla.slaTargetMinutes,
        sla.dueBy ? sla.dueBy.toISOString() : "",
        sla.isBreached ? "Yes" : "No",
        sla.breachMinutes,
        sla.slaStatus,
      ].join(",");
    });

    const csv = [headers.join(","), ...rows].join("\n");

    return new NextResponse(csv, {
      status: 200,
      headers: {
        "Content-Type": "text/csv",
        "Content-Disposition": `attachment; filename="sla-report-${new Date().toISOString().slice(0, 10)}.csv"`,
      },
    });
  } catch (e) {
    logger.error("Error exporting SLA report", { error: (e as Error).message });
    return serverErrorResponse();
  }
}