package sla;

import java.time.ZonedDateTime;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Objects;

/**
 * A service-desk ticket with timestamped status history.
 * Immutable after validation/construction.
 */
public class Ticket {
    private final String id;
    private final String priority;    // P1–P4
    private final String group;       // assignee group
    private final ZonedDateTime created;
    private final List<StatusEntry> history;  // sorted by timestamp after validation

    public Ticket(String id, String priority, String group,
                  ZonedDateTime created, List<StatusEntry> history) {
        this.id = Objects.requireNonNull(id);
        this.priority = Objects.requireNonNull(priority);
        this.group = Objects.requireNonNull(group);
        this.created = Objects.requireNonNull(created);
        // Sort history by timestamp
        var sorted = new ArrayList<>(history);
        sorted.sort(Comparator.comparing(StatusEntry::timestamp));
        this.history = List.copyOf(sorted);
    }

    public String id() { return id; }
    public String priority() { return priority; }
    public String group() { return group; }
    public ZonedDateTime created() { return created; }
    public List<StatusEntry> history() { return history; }

    /**
     * Extract ON_HOLD intervals from status history.
     * A hold starts at the first ON_HOLD entry and ends at the
     * next non-ON_HOLD entry (or remains open if still on hold).
     * Handles multiple pause/resume cycles. For unresolved tickets
     * still on hold, the hold ends at {@code asOf}.
     */
    public List<BusinessCalendar.HoldInterval> holdIntervals(ZonedDateTime asOf) {
        List<BusinessCalendar.HoldInterval> intervals = new ArrayList<>();
        ZonedDateTime holdStart = null;
        for (var e : history) {
            if ("ON_HOLD".equals(e.status())) {
                if (holdStart == null) holdStart = e.timestamp();
            } else {
                if (holdStart != null) {
                    if (!e.timestamp().isBefore(holdStart)) {
                        intervals.add(new BusinessCalendar.HoldInterval(holdStart, e.timestamp()));
                    }
                    holdStart = null;
                }
            }
        }
        // Ticket currently on hold
        if (holdStart != null) {
            intervals.add(new BusinessCalendar.HoldInterval(holdStart, asOf));
        }
        return intervals;
    }

    /** Current status — the last entry in history, or "NEW" if empty. */
    public String currentStatus() {
        return history.isEmpty() ? "NEW" : history.getLast().status();
    }

    /** Resolved? Excluding ON_HOLD. */
    public boolean isResolved(ZonedDateTime asOf) {
        String st = currentStatus();
        return "RESOLVED".equals(st) || "CLOSED".equals(st);
    }

    /** Single status-history entry. */
    public record StatusEntry(String status, ZonedDateTime timestamp) {
        public StatusEntry {
            Objects.requireNonNull(status);
            Objects.requireNonNull(timestamp);
        }
    }
}