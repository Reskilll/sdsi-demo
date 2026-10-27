import { NextRequest } from "next/server";
import { connectDB } from "@/lib/db";
import { requireAuth } from "@/lib/api-auth";
import { successResponse, serverErrorResponse } from "@/lib/api-response";
import Ticket from "@/models/Ticket";
import SLAPolicy from "@/models/SLAPolicy";
import Holiday from "@/models/Holiday";
import { calculateSla, DEFAULT_SLA_TARGETS } from "@/services/sla-calculator";
import { buildCalendarConfig } from "@/services/business-calendar";
import { logger } from "@/lib/logger";
import type { Priority, TicketStatus } from "@/types";

/**
 * GET /api/reports/sla — SLA breach report
 * Supports filters: priority, status, assigneeGroup, dateFrom, dateTo
 */
export async function GET(request: NextRequest) {
  try {
    const auth = await requireAuth(request);
    if (!("adminId" in auth)) return auth;

    await connectDB();

    const { searchParams } = new URL(request.url);
    const priority = searchParams.get("priority");
    const status = searchParams.get("status");
    const assigneeGroup = searchParams.get("assigneeGroup");
    const dateFrom = searchParams.get("dateFrom");
    const dateTo = searchParams.get("dateTo");

    const now = new Date();

    // Build filter
    const filter: Record<string, unknown> = {};
    if (priority) filter.priority = priority;
    if (status) filter.status = status;
    if (assigneeGroup) filter.assigneeGroup = assigneeGroup;
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

    // Calculate SLA for each ticket
    const enrichedTickets = tickets.map((ticket) => {
      const slaResult = calculateSla(
        ticket.statusHistory,
        ticket.priority as Priority,
        ticket.status as TicketStatus,
        ticket.resolvedAt ? new Date(ticket.resolvedAt) : null,
        now,
        policyMap,
        calendarConfig,
      );

      return {
        ...ticket,
        slaResult,
      };
    });

    // Aggregate by priority
    const byPriority: Record<string, { total: number; breached: number }> = {};
    for (const p of ["P1", "P2", "P3", "P4"]) {
      byPriority[p] = { total: 0, breached: 0 };
    }
    enrichedTickets.forEach((t) => {
      byPriority[t.priority].total++;
      if (t.slaResult.isBreached) byPriority[t.priority].breached++;
    });

    // Aggregate by assignee group
    const byGroup: Record<string, { name: string; total: number; breached: number }> = {};
    enrichedTickets.forEach((t) => {
      const groupId = t.assigneeGroup?._id?.toString() || "unassigned";
      if (!byGroup[groupId]) {
        byGroup[groupId] = {
          name: (t.assigneeGroup as any)?.name || "Unassigned",
          total: 0,
          breached: 0,
        };
      }
      byGroup[groupId].total++;
      if (t.slaResult.isBreached) byGroup[groupId].breached++;
    });

    return successResponse({
      tickets: enrichedTickets,
      summary: {
        total: tickets.length,
        breached: enrichedTickets.filter((t) => t.slaResult.isBreached).length,
        byPriority: Object.entries(byPriority).map(([p, d]) => ({
          priority: p,
          total: d.total,
          breached: d.breached,
          percentage: d.total > 0 ? Math.round((d.breached / d.total) * 100) : 0,
        })),
        byGroup: Object.entries(byGroup).map(([, d]) => ({
          name: d.name,
          total: d.total,
          breached: d.breached,
          percentage: d.total > 0 ? Math.round((d.breached / d.total) * 100) : 0,
        })),
      },
    });
  } catch (e) {
    logger.error("Error generating SLA report", { error: (e as Error).message });
    return serverErrorResponse();
  }
}