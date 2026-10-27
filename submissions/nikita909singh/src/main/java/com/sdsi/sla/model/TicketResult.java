package com.sdsi.sla.model;

import java.time.ZonedDateTime;

/**
 * SLA outcome for one ticket (M4).
 *
 * @param resolved       true when the current status is a stopped status (RESOLVED, CLOSED)
 * @param elapsedMinutes business minutes the clock ran, rounded down
 * @param dueBy          when the target is (or would be) reached; null while the ticket is on hold and
 *                       has not yet used up its target, because the deadline depends on when it resumes
 * @param breachMinutes  business minutes over target, rounded up, so any breach shows at least 1
 */
public record TicketResult(
        String id,
        String priority,
        String assigneeGroup,
        String currentStatus,
        boolean resolved,
        long targetMinutes,
        long elapsedMinutes,
        ZonedDateTime dueBy,
        boolean breached,
        long breachMinutes,
        State state) {

    public enum State {
        /** Resolved within target. */
        MET,
        /** Over target (resolved late, or still open and already late). */
        BREACHED,
        /** Open, within target, more than the at-risk fraction remaining. */
        ON_TRACK,
        /** Open, within target, but less than the at-risk fraction remaining. */
        AT_RISK,
        /** On hold, within target: the clock is paused. */
        PAUSED
    }
}
