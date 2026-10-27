package com.sdsi.sla.model;

import java.time.Instant;
import java.util.List;

/**
 * A validated support ticket.
 *
 * @param history status changes after creation, sorted by time (ties keep file order). The ticket starts
 *                in the clock-running state at {@code createdAt} unless an entry at that instant says
 *                otherwise.
 */
public record Ticket(String id, String priority, String assigneeGroup, Instant createdAt, List<StatusChange> history) {

    public record StatusChange(String status, Instant at) {
    }
}
