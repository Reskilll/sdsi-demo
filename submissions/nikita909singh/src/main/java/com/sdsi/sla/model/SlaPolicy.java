package com.sdsi.sla.model;

import java.time.DayOfWeek;
import java.time.Duration;
import java.time.LocalTime;
import java.time.ZoneId;
import java.util.EnumSet;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * Business calendar and SLA targets.
 *
 * @param targets         priority -> resolution target in business time
 * @param runningStatuses statuses in which the SLA clock runs
 * @param pausedStatuses  statuses in which the clock is paused (M3)
 * @param stoppedStatuses statuses in which the ticket counts as resolved; the clock stops
 * @param atRiskFraction  an open ticket is "at risk" once less than this fraction of its target remains
 */
public record SlaPolicy(
        ZoneId zone,
        Set<DayOfWeek> workDays,
        LocalTime dayStart,
        LocalTime dayEnd,
        Map<String, Duration> targets,
        Set<String> runningStatuses,
        Set<String> pausedStatuses,
        Set<String> stoppedStatuses,
        double atRiskFraction) {

    /** The targets from the problem statement: Mon–Fri 09:00–18:00, P1 4h, P2 8h, P3 24h, P4 72h. */
    public static SlaPolicy defaults(ZoneId zone) {
        Map<String, Duration> targets = new LinkedHashMap<>();
        targets.put("P1", Duration.ofHours(4));
        targets.put("P2", Duration.ofHours(8));
        targets.put("P3", Duration.ofHours(24));
        targets.put("P4", Duration.ofHours(72));
        return new SlaPolicy(zone,
                EnumSet.range(DayOfWeek.MONDAY, DayOfWeek.FRIDAY),
                LocalTime.of(9, 0), LocalTime.of(18, 0),
                Map.copyOf(targets),
                Set.of("NEW", "OPEN", "ASSIGNED", "IN_PROGRESS", "REOPENED"),
                Set.of("ON_HOLD"),
                Set.of("RESOLVED", "CLOSED"),
                0.25);
    }

    public boolean isKnownStatus(String s) {
        return runningStatuses.contains(s) || pausedStatuses.contains(s) || stoppedStatuses.contains(s);
    }
}
