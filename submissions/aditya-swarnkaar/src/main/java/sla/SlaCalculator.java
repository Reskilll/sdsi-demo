package sla;

import java.time.ZonedDateTime;
import java.util.*;

/**
 * Core SLA calculator: computes elapsed business minutes, due-by, breach.
 * Uses integer arithmetic throughout — no floating-point.
 */
public class SlaCalculator {

    private final BusinessCalendar cal;
    private final SlaPolicy policy;

    public SlaCalculator(BusinessCalendar cal, SlaPolicy policy) {
        this.cal = cal;
        this.policy = policy;
    }

    /** Compute SLA result for a single ticket at the given cutoff. */
    public TicketResult compute(Ticket t, ZonedDateTime asOf) {
        long target = policy.target(t.priority());
        if (target < 0)
            throw new IllegalArgumentException("Unknown priority: " + t.priority());

        var holds = t.holdIntervals(asOf);
        long elapsed = cal.activeMinutes(t.created(), asOf, holds);
        ZonedDateTime dueBy = cal.dueBy(t.created(), target, holds);
        boolean breached = !asOf.isBefore(dueBy); // >= dueBy means breach
        long breachMinutes = breached ? cal.activeMinutes(dueBy, asOf, holds) : 0;

        return new TicketResult(
            t.id(), t.priority(), t.group(), t.currentStatus(),
            elapsed, target, dueBy, breached, breachMinutes
        );
    }

    public record TicketResult(
        String ticketId, String priority, String group, String status,
        long elapsedMinutes, long slaTargetMinutes, ZonedDateTime dueBy,
        boolean breached, long breachMinutes
    ) {}
}