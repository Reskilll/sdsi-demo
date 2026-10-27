package com.sdsi.sla.core;

import com.sdsi.sla.model.SlaPolicy;
import com.sdsi.sla.model.Summary;
import com.sdsi.sla.model.Ticket;
import com.sdsi.sla.model.TicketResult;
import com.sdsi.sla.model.TicketResult.State;

import java.time.Instant;
import java.time.ZonedDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.function.Function;

/**
 * Computes the SLA outcome of each ticket (M3, M4) and the breach summary (M5).
 *
 * <p>The clock starts at {@code createdAt} and runs while the ticket is in a running status. It pauses
 * in a paused status (ON_HOLD) and stops in a stopped status (RESOLVED, CLOSED). A ticket that is
 * reopened starts the clock again from where it left off. Only business time counts. Status changes
 * after {@code asOf} are ignored, so a report can be rerun "as of" any moment.
 */
public final class SlaEngine {

    private final SlaPolicy policy;
    private final BusinessCalendar calendar;

    public SlaEngine(SlaPolicy policy, BusinessCalendar calendar) {
        this.policy = policy;
        this.calendar = calendar;
    }

    public TicketResult evaluate(Ticket t, Instant asOf) {
        if (t.createdAt().isAfter(asOf)) {
            throw new ValidationException("ticket " + t.id() + " was created after the as-of time "
                    + asOf.atZone(calendar.zone()).toOffsetDateTime());
        }
        long target = policy.targets().get(t.priority()).toSeconds();

        // A new ticket's clock runs from creation; a custom policy may not call that status OPEN.
        String status = isRunning("OPEN") ? "OPEN" : policy.runningStatuses().iterator().next();
        Instant since = t.createdAt();
        long elapsed = 0;
        Instant dueBy = null;
        Instant resolvedAt = null;

        for (Ticket.StatusChange change : t.history()) {
            if (change.at().isAfter(asOf)) {
                break; // history is sorted, so everything after this is in the future too
            }
            if (isRunning(status)) {
                long seg = calendar.businessSeconds(since, change.at());
                if (dueBy == null && elapsed + seg >= target) {
                    dueBy = calendar.addBusinessSeconds(since, target - elapsed);
                }
                elapsed += seg;
            }
            if (!isStopped(status) && isStopped(change.status())) {
                resolvedAt = change.at(); // RESOLVED -> CLOSED keeps the first resolution time
            }
            status = change.status();
            since = change.at();
        }
        if (isRunning(status)) {
            long seg = calendar.businessSeconds(since, asOf);
            if (dueBy == null && elapsed + seg >= target) {
                dueBy = calendar.addBusinessSeconds(since, target - elapsed);
            }
            elapsed += seg;
        }

        boolean paused = policy.pausedStatuses().contains(status);
        boolean stopped = isStopped(status);
        if (dueBy == null && !paused) {
            // Not reached yet: project forward from now (still running) or from resolution (stopped),
            // assuming no further holds. For an on-hold ticket the deadline is unknown until it resumes.
            dueBy = calendar.addBusinessSeconds(stopped ? resolvedAt : asOf, target - elapsed);
        }

        boolean breached = elapsed > target;
        long breachSeconds = Math.max(0, elapsed - target);
        State state;
        if (breached) {
            state = State.BREACHED;
        } else if (stopped) {
            state = State.MET;
        } else if (paused) {
            state = State.PAUSED;
        } else if (target - elapsed < policy.atRiskFraction() * target) {
            state = State.AT_RISK;
        } else {
            state = State.ON_TRACK;
        }
        ZonedDateTime due = dueBy == null ? null : dueBy.atZone(calendar.zone());
        return new TicketResult(t.id(), t.priority(), t.assigneeGroup(), status, stopped, target / 60, elapsed / 60,
                due, breached, (breachSeconds + 59) / 60, state);
    }

    public List<TicketResult> evaluateAll(List<Ticket> tickets, Instant asOf) {
        List<TicketResult> out = new ArrayList<>(tickets.size());
        for (Ticket t : tickets) {
            out.add(evaluate(t, asOf));
        }
        return out;
    }

    public Summary summarize(List<TicketResult> results) {
        return new Summary(
                bucket("ALL", results),
                group(results, TicketResult::priority),
                group(results, TicketResult::assigneeGroup));
    }

    private boolean isRunning(String status) {
        return policy.runningStatuses().contains(status);
    }

    private boolean isStopped(String status) {
        return policy.stoppedStatuses().contains(status);
    }

    private static List<Summary.Bucket> group(List<TicketResult> results, Function<TicketResult, String> key) {
        Map<String, List<TicketResult>> grouped = new TreeMap<>();
        for (TicketResult r : results) {
            grouped.computeIfAbsent(key.apply(r), k -> new ArrayList<>()).add(r);
        }
        List<Summary.Bucket> out = new ArrayList<>();
        grouped.forEach((k, list) -> out.add(bucket(k, list)));
        return out;
    }

    private static Summary.Bucket bucket(String key, List<TicketResult> list) {
        int breached = (int) list.stream().filter(TicketResult::breached).count();
        int open = (int) list.stream().filter(r -> !r.resolved()).count();
        double pct = list.isEmpty() ? 0 : Math.round(breached * 10000.0 / list.size()) / 100.0;
        return new Summary.Bucket(key, list.size(), breached, open, pct);
    }
}
