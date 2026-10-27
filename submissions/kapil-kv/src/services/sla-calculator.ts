import type {
  Priority,
  TicketStatus,
  StatusEvent,
  SlaResult,
  SlaStatus,
  BusinessCalendarConfig,
  Policy,
} from "@/types";
import {
  calculateBusinessMinutes,
  addBusinessMinutes,
  nextBusinessStart,
  buildCalendarConfig,
} from "./business-calendar";

/**
 * SLA Calculation Engine
 *
 * M1: SLA targets by priority
 *   P1 - 4 business hours (240 minutes)
 *   P2 - 8 business hours (480 minutes)
 *   P3 - 24 business hours (1440 minutes)
 *   P4 - 72 business hours (4320 minutes)
 *
 * M2: Business calendar rules
 *   - Monday through Friday
 *   - 09:00 to 18:00 in APP_TIMEZONE
 *   - Exclude weekends and active holidays
 *   - Tickets created outside business hours start at next business start
 *
 * M3: ON_HOLD pauses SLA
 *   - SLA clock stops when ticket enters ON_HOLD
 *   - SLA clock resumes when ticket leaves ON_HOLD
 *   - Multiple hold/resume cycles supported
 *
 * M4: Per-ticket SLA results
 *   - elapsedBusinessMinutes, slaTargetMinutes, dueBy, isBreached,
 *     breachMinutes, remainingBusinessMinutes, slaStatus
 */

export const DEFAULT_SLA_TARGETS: Record<Priority, number> = {
  P1: 240, // 4 hours
  P2: 480, // 8 hours
  P3: 1440, // 24 hours
  P4: 4320, // 72 hours
};

/**
 * Calculate SLA results for a ticket.
 *
 * @param statusHistory - Complete status history (must be at least [created] event)
 * @param priority - Ticket priority (P1-P4)
 * @param currentStatus - Current status of the ticket
 * @param resolvedAt - Resolution timestamp (null if currently unresolved)
 * @param now - Reference time for calculation (defaults to now, injectable for testing)
 * @param policies - Optional policy overrides
 * @param calendarConfig - Business calendar configuration
 */
export function calculateSla(
  statusHistory: StatusEvent[],
  priority: Priority,
  currentStatus: TicketStatus,
  resolvedAt: Date | null,
  now: Date = new Date(),
  policies?: Record<Priority, number>,
  calendarConfig?: BusinessCalendarConfig,
): SlaResult {
  // Validate inputs
  if (!statusHistory || statusHistory.length === 0) {
    return {
      elapsedBusinessMinutes: 0,
      slaTargetMinutes: 0,
      dueBy: null,
      isBreached: false,
      breachMinutes: 0,
      remainingBusinessMinutes: 0,
      slaStatus: "ON_TRACK",
      isProvisional: false,
    };
  }

  if (!priority || !DEFAULT_SLA_TARGETS[priority]) {
    return {
      elapsedBusinessMinutes: 0,
      slaTargetMinutes: 0,
      dueBy: null,
      isBreached: false,
      breachMinutes: 0,
      remainingBusinessMinutes: 0,
      slaStatus: "ON_TRACK",
      isProvisional: false,
    };
  }

  const slaTargets = policies || DEFAULT_SLA_TARGETS;
  const slaTargetMinutes = slaTargets[priority];
  const config = calendarConfig || buildCalendarConfig([]);

  // Sort status history by timestamp (oldest first)
  const sortedHistory = [...statusHistory].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
  );

  // The SLA clock starts at the first status event (should be OPEN creation)
  const creationEvent = sortedHistory[0];
  const creationTime = new Date(creationEvent.timestamp);

  // Calculate elapsed business minutes excluding ON_HOLD intervals
  let elapsedBusinessMinutes = 0;
  const referenceTime = currentStatus === "RESOLVED" && resolvedAt ? new Date(resolvedAt) : now;

  // Track ON_HOLD intervals
  const onHoldIntervals: { start: Date; end: Date }[] = [];
  for (let i = 0; i < sortedHistory.length; i++) {
    const event = sortedHistory[i];
    if (event.status === "ON_HOLD") {
      // Start of hold interval
      const holdStart = new Date(event.timestamp);
      // Find corresponding resume event (not ON_HOLD)
      let holdEnd: Date | null = null;
      for (let j = i + 1; j < sortedHistory.length; j++) {
        if (sortedHistory[j].status !== "ON_HOLD") {
          holdEnd = new Date(sortedHistory[j].timestamp);
          break;
        }
      }
      if (holdEnd === null) {
        // Still on hold — end is the reference time
        holdEnd = referenceTime;
      }
      onHoldIntervals.push({ start: holdStart, end: holdEnd });
    }
  }

  // Calculate elapsed business time from creation to reference time
  // excluding all ON_HOLD intervals
  let clockStart = new Date(creationTime);
  for (const interval of onHoldIntervals) {
    const intervalStart = interval.start;
    // Calculate business minutes from clockStart to intervalStart
    elapsedBusinessMinutes += calculateBusinessMinutes(clockStart, intervalStart, config);
    // Move clockStart past this hold interval
    clockStart = new Date(interval.end);
  }

  // Add remaining time from last clockStart to reference time
  const remainingElapsed = calculateBusinessMinutes(clockStart, referenceTime, config);
  elapsedBusinessMinutes += remainingElapsed;

  // Calculate dueBy: creation + SLA target (business minutes)
  // We need to add the SLA target in business minutes to the creation time,
  // then extend by the total hold duration (in real minutes)
  let totalHoldRealMinutes = 0;
  for (const interval of onHoldIntervals) {
    const holdStart = interval.start;
    const holdEnd = interval.end;
    if (holdEnd > holdStart) {
      totalHoldRealMinutes += (holdEnd.getTime() - holdStart.getTime()) / 60000;
    }
  }

  // Calculate the raw due by date (business-time forward from creation)
  let dueBy = addBusinessMinutes(creationTime, slaTargetMinutes, config);

  // Extend dueBy by hold real-time minutes
  if (totalHoldRealMinutes > 0) {
    const dueByMs = dueBy.getTime() + totalHoldRealMinutes * 60000;
    dueBy = new Date(dueByMs);
  }

  // Calculate breach status
  let isBreached: boolean;
  let breachMinutes: number;

  if (currentStatus === "RESOLVED" && resolvedAt) {
    // For resolved tickets: compare resolution time against dueBy
    isBreached = resolvedAt.getTime() > dueBy.getTime();
    breachMinutes = isBreached ? elapsedBusinessMinutes - slaTargetMinutes : 0;
  } else if (currentStatus === "ON_HOLD") {
    // For on-hold tickets: evaluate using elapsed time so far
    isBreached = elapsedBusinessMinutes > slaTargetMinutes;
    breachMinutes = isBreached ? elapsedBusinessMinutes - slaTargetMinutes : 0;
  } else {
    // For open/in-progress tickets: evaluate at current time
    isBreached = elapsedBusinessMinutes > slaTargetMinutes;
    breachMinutes = isBreached ? elapsedBusinessMinutes - slaTargetMinutes : 0;
  }

  // Ensure breachMinutes is never negative
  if (breachMinutes < 0) breachMinutes = 0;

  // Calculate remaining business minutes
  const remainingBusinessMinutes = Math.max(0, slaTargetMinutes - elapsedBusinessMinutes);

  // Determine SLA status
  let slaStatus: SlaStatus;
  if (currentStatus === "RESOLVED") {
    slaStatus = "RESOLVED";
  } else if (currentStatus === "ON_HOLD") {
    slaStatus = "PAUSED";
  } else if (isBreached) {
    slaStatus = "BREACHED";
  } else if (remainingBusinessMinutes <= slaTargetMinutes * 0.25) {
    // 25% or less of target remaining -> AT_RISK
    slaStatus = "AT_RISK";
  } else {
    slaStatus = "ON_TRACK";
  }

  const isProvisional = currentStatus === "ON_HOLD";

  return {
    elapsedBusinessMinutes,
    slaTargetMinutes,
    dueBy,
    isBreached,
    breachMinutes,
    remainingBusinessMinutes,
    slaStatus,
    isProvisional,
  };
}

/**
 * Calculate SLA for a list of tickets (used in batch reporting).
 */
export function calculateBatchSla(
  tickets: Array<{
    statusHistory: StatusEvent[];
    priority: Priority;
    status: TicketStatus;
    resolvedAt: Date | null;
  }>,
  now?: Date,
  policies?: Record<Priority, number>,
  calendarConfig?: BusinessCalendarConfig,
): Map<number, SlaResult> {
  const results = new Map<number, SlaResult>();
  tickets.forEach((ticket, index) => {
    results.set(index, calculateSla(
      ticket.statusHistory,
      ticket.priority,
      ticket.status,
      ticket.resolvedAt,
      now,
      policies,
      calendarConfig,
    ));
  });
  return results;
}

/**
 * Validate that a status transition is allowed.
 */
export const VALID_TRANSITIONS: Record<TicketStatus, TicketStatus[]> = {
  OPEN: ["IN_PROGRESS", "ON_HOLD", "RESOLVED"],
  IN_PROGRESS: ["ON_HOLD", "RESOLVED", "OPEN"],
  ON_HOLD: ["IN_PROGRESS", "RESOLVED", "OPEN"],
  RESOLVED: [], // Cannot transition from RESOLVED
};

export function isValidTransition(
  from: TicketStatus,
  to: TicketStatus,
): boolean {
  return VALID_TRANSITIONS[from]?.includes(to) ?? false;
}