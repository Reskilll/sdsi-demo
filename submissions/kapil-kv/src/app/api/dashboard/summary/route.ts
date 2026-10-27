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
 * GET /api/dashboard/summary — Dashboard summary statistics
 */
export async function GET(request: NextRequest) {
  try {
    const auth = await requireAuth(request);
    if (!("adminId" in auth)) return auth;

    await connectDB();

    const now = new Date();

    // Fetch all tickets, policies, and active holidays
    const [tickets, policies, holidays] = await Promise.all([
      Ticket.find().lean(),
      SLAPolicy.find().lean(),
      Holiday.find({ isActive: true }).lean(),
    ]);

    const policyMap: Record<Priority, number> = { ...DEFAULT_SLA_TARGETS };
    for (const p of policies) {
      if (p.isActive) {
        policyMap[p.priority] = p.targetBusinessHours * 60; // convert hours to minutes
      }
    }

    const calendarConfig = buildCalendarConfig(
      holidays.map((h) => new Date(h.date)),
    );

    // Calculate SLA results for each ticket
    const slaResults = tickets.map((ticket) =>
      calculateSla(
        ticket.statusHistory,
        ticket.priority as Priority,
        ticket.status as TicketStatus,
        ticket.resolvedAt ? new Date(ticket.resolvedAt) : null,
        now,
        policyMap,
        calendarConfig,
      ),
    );

    // Aggregate counts
    const total = tickets.length;
    const resolved = tickets.filter((t) => t.status === "RESOLVED").length;
    const open = tickets.filter((t) => t.status === "OPEN").length;
    const inProgress = tickets.filter((t) => t.status === "IN_PROGRESS").length;
    const onHold = tickets.filter((t) => t.status === "ON_HOLD").length;
    const breached = slaResults.filter((r) => r.isBreached).length;

    // SLA compliance: resolved tickets NOT breached / resolved tickets
    const eligibleResolved = tickets.filter((t) => t.status === "RESOLVED");
    const compliantResolved = eligibleResolved.filter((t, i) => {
      const result = slaResults[i];
      return result.slaStatus === "RESOLVED" && !result.isBreached;
    }).length;
    const slaCompliance =
      eligibleResolved.length > 0
        ? Math.round((compliantResolved / eligibleResolved.length) * 100)
        : 100;

    // Average resolution time (business minutes) for resolved tickets
    const resolvedResults = slaResults.filter(
      (_, i) => tickets[i].status === "RESOLVED",
    );
    const avgResolutionTime =
      resolvedResults.length > 0
        ? Math.round(
            resolvedResults.reduce((sum, r) => sum + r.elapsedBusinessMinutes, 0) /
              resolvedResults.length,
          )
        : 0;

    // Average breach duration
    const breachedResults = slaResults.filter((r) => r.isBreached);
    const avgBreachDuration =
      breachedResults.length > 0
        ? Math.round(
            breachedResults.reduce((sum, r) => sum + r.breachMinutes, 0) /
              breachedResults.length,
          )
        : 0;

    // Breaches by priority
    const breachesByPriority: Record<string, { total: number; breached: number }> = {};
    for (const p of ["P1", "P2", "P3", "P4"]) {
      breachesByPriority[p] = { total: 0, breached: 0 };
    }
    tickets.forEach((t, i) => {
      breachesByPriority[t.priority].total++;
      if (slaResults[i].isBreached) {
        breachesByPriority[t.priority].breached++;
      }
    });

    // Breaches by assignee group
    const breachesByGroup: Record<
      string,
      { name: string; total: number; breached: number }
    > = {};
    tickets.forEach((t, i) => {
      const groupId = t.assigneeGroup?.toString() || "unassigned";
      if (!breachesByGroup[groupId]) {
        breachesByGroup[groupId] = {
          name: (t.assigneeGroup as any)?.name || "Unassigned",
          total: 0,
          breached: 0,
        };
      }
      breachesByGroup[groupId].total++;
      if (slaResults[i].isBreached) {
        breachesByGroup[groupId].breached++;
      }
    });

    // Status distribution
    const statusDistribution = {
      OPEN: open,
      IN_PROGRESS: inProgress,
      ON_HOLD: onHold,
      RESOLVED: resolved,
    };

    // On-track count
    const onTrack = slaResults.filter((r) => r.slaStatus === "ON_TRACK").length;
    const atRisk = slaResults.filter((r) => r.slaStatus === "AT_RISK").length;

    return successResponse({
      summary: {
        total,
        open,
        inProgress,
        onHold,
        resolved,
        breached,
        onTrack,
        atRisk,
        slaCompliance,
        avgResolutionTime,
        avgBreachDuration,
      },
      breachesByPriority: Object.entries(breachesByPriority).map(([priority, data]) => ({
        priority,
        total: data.total,
        breached: data.breached,
        percentage: data.total > 0 ? Math.round((data.breached / data.total) * 100) : 0,
      })),
      breachesByGroup: Object.entries(breachesByGroup).map(([, data]) => ({
        name: data.name,
        total: data.total,
        breached: data.breached,
        percentage: data.total > 0 ? Math.round((data.breached / data.total) * 100) : 0,
      })),
      statusDistribution,
    });
  } catch (e) {
    logger.error("Error fetching dashboard summary", { error: (e as Error).message });
    return serverErrorResponse();
  }
}