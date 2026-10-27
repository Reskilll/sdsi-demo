package sla;

import static org.junit.jupiter.api.Assertions.*;
import org.junit.jupiter.api.Test;
import java.time.*;
import java.util.*;

public class SlaTrackerTest {

    static final ZoneId UTC = ZoneId.of("UTC");
    static BusinessCalendar cal(Set<LocalDate> h) { return new BusinessCalendar(UTC, h); }

    static BusinessCalendar.HoldInterval hold(String a, String b) {
        return new BusinessCalendar.HoldInterval(ZonedDateTime.parse(a), ZonedDateTime.parse(b));
    }

    // ── M1: basic P1=4h target, business minutes ──
    @Test void p1TargetIs240() {
        assertEquals(240, SlaPolicy.DEFAULTS.get("P1"));
        assertEquals(480, SlaPolicy.DEFAULTS.get("P2"));
        assertEquals(1440, SlaPolicy.DEFAULTS.get("P3"));
        assertEquals(4320, SlaPolicy.DEFAULTS.get("P4"));
    }

    @Test void elapsedWithinSingleDay() {
        var c = cal(Set.of());
        long m = c.activeMinutes(t("2026-01-12T09:00:00Z"), t("2026-01-12T13:00:00Z"), List.of());
        assertEquals(240, m);
    }

    @Test void elapsedSpansWeekend() {
        var c = cal(Set.of());
        long m = c.activeMinutes(t("2026-01-09T16:00:00Z"), t("2026-01-12T12:00:00Z"), List.of());
        // Fri 16:00-18:00 = 120; Mon 09:00-12:00 = 180; total 300
        assertEquals(300, m);
    }

    @Test void outOfHoursCreation() {
        var c = cal(Set.of());
        long m = c.activeMinutes(t("2026-01-12T06:00:00Z"), t("2026-01-12T10:00:00Z"), List.of());
        assertEquals(60, m); // only 09:00-10:00
    }

    // ── M2: holidays ──
    @Test void holidayExcluded() {
        var c = cal(Set.of(LocalDate.parse("2026-01-19")));
        // Mon Jan 19 is holiday; Jan 20 is Tue
        long m = c.activeMinutes(t("2026-01-19T09:00:00Z"), t("2026-01-20T10:00:00Z"), List.of());
        assertEquals(60, m); // only Tue 09:00-10:00
    }

    // ── M3: ON_HOLD ──
    @Test void holdPausesClock() {
        var c = cal(Set.of());
        var holds = List.of(hold("2026-01-12T11:00:00Z", "2026-01-12T12:00:00Z"));
        long m = c.activeMinutes(t("2026-01-12T09:00:00Z"), t("2026-01-12T14:00:00Z"), holds);
        assertEquals(240, m); // 5h - 1h hold = 4h
    }

    @Test void multipleHolds() {
        var c = cal(Set.of());
        var holds = List.of(
            hold("2026-01-12T10:00:00Z", "2026-01-12T11:00:00Z"),
            hold("2026-01-12T13:00:00Z", "2026-01-12T14:00:00Z"));
        long m = c.activeMinutes(t("2026-01-12T09:00:00Z"), t("2026-01-12T15:00:00Z"), holds);
        assertEquals(240, m); // 6h - 2h = 4h
    }

    @Test void overlappingHoldsMerged() {
        var c = cal(Set.of());
        var holds = List.of(
            hold("2026-01-12T10:00:00Z", "2026-01-12T13:00:00Z"),
            hold("2026-01-12T12:00:00Z", "2026-01-12T14:00:00Z"));
        long m = c.activeMinutes(t("2026-01-12T09:00:00Z"), t("2026-01-12T15:00:00Z"), holds);
        assertEquals(120, m); // 6h - 4h merged = 2h
    }

    @Test void ticketCurrentlyOnHold() {
        var c = cal(Set.of());
        var t = new Ticket("T1", "P1", "G", t("2026-01-12T09:00:00Z"), List.of(
            new Ticket.StatusEntry("ON_HOLD", t("2026-01-12T10:00:00Z"))));
        var holds = t.holdIntervals(t("2026-01-12T15:00:00Z"));
        assertEquals(1, holds.size());
        // hold 10:00 -> asOf (15:00)
        assertEquals(t("2026-01-12T10:00:00Z"), holds.get(0).start());
        assertEquals(t("2026-01-12T15:00:00Z"), holds.get(0).end());
    }

    // ── M4: per-ticket output fields ──
    @Test void computeBreachAndDueBy() {
        var c = cal(Set.of());
        var calc = new SlaCalculator(c, SlaPolicy.defaults());
        var t = new Ticket("T1", "P1", "G", t("2026-01-12T09:00:00Z"), List.of());
        var asOf = t("2026-01-12T14:00:00Z");
        var r = calc.compute(t, asOf);
        assertEquals(300, r.elapsedMinutes());
        assertEquals(240, r.slaTargetMinutes());
        assertEquals(t("2026-01-12T13:00:00Z"), r.dueBy()); // 09:00 + 4h = 13:00
        assertTrue(r.breached());
        assertEquals(60, r.breachMinutes()); // 13:00 -> 14:00
    }

    @Test void notBreached() {
        var c = cal(Set.of());
        var calc = new SlaCalculator(c, SlaPolicy.defaults());
        var t = new Ticket("T1", "P1", "G", t("2026-01-12T09:00:00Z"), List.of());
        var r = calc.compute(t, t("2026-01-12T12:00:00Z"));
        assertFalse(r.breached());
        assertEquals(0, r.breachMinutes());
    }

    // ── M5: due-by across days / holds ──
    @Test void dueByAcrossWeekend() {
        var c = cal(Set.of());
        // Fri 16:00 => needs 4h: 16-18 (2h), next Mon 09-11
        var due = c.dueBy(t("2026-01-09T16:00:00Z"), 240, List.of());
        assertEquals(t("2026-01-12T11:00:00Z"), due);
    }

    @Test void dueByAcrossHold() {
        var c = cal(Set.of());
        var holds = List.of(hold("2026-01-12T11:00:00Z", "2026-01-12T13:00:00Z"));
        var due = c.dueBy(t("2026-01-12T09:00:00Z"), 240, holds);
        // 09-11 = 2h, hold 11-13, 13-15 = 2h => due 15:00
        assertEquals(t("2026-01-12T15:00:00Z"), due);
    }

    @Test void dueByAfterCloseRollsToNextDay() {
        var c = cal(Set.of());
        var due = c.dueBy(t("2026-01-12T17:00:00Z"), 240, List.of());
        // 17-18 = 1h, next day 09-12 = 3h => due 12:00 Tue
        assertEquals(t("2026-01-13T12:00:00Z"), due);
    }

    @Test void exactDeadlineNotBreached() {
        var c = cal(Set.of());
        var calc = new SlaCalculator(c, SlaPolicy.defaults());
        var t = new Ticket("T1", "P1", "G", t("2026-01-12T09:00:00Z"), List.of());
        var r = calc.compute(t, t("2026-01-12T13:00:00Z"));
        assertFalse(r.breached()); // asOf == dueBy
        assertEquals(0, r.breachMinutes());
    }

    // ── Validation / edge cases ──
    @Test void duplicateTicketIdsRejected() {
        List<Map<String,Object>> raw = new ArrayList<>();
        raw.add(mapOf("ticket_id","T1","priority","P1","assignee_group","G",
            "created_at","2026-01-12T09:00:00Z","status_history",List.of()));
        raw.add(mapOf("ticket_id","T1","priority","P2","assignee_group","G",
            "created_at","2026-01-12T09:00:00Z","status_history",List.of()));
        assertThrows(Validator.ValidationException.class, () -> Validator.validateTickets(raw, UTC));
    }

    @Test void unknownPriorityRejected() {
        List<Map<String,Object>> raw = new ArrayList<>();
        raw.add(mapOf("ticket_id","T1","priority","P9","assignee_group","G",
            "created_at","2026-01-12T09:00:00Z","status_history",List.of()));
        assertThrows(Validator.ValidationException.class, () -> Validator.validateTickets(raw, UTC));
    }

    @Test void invalidTimestampRejected() {
        List<Map<String,Object>> raw = new ArrayList<>();
        raw.add(mapOf("ticket_id","T1","priority","P1","assignee_group","G",
            "created_at","not-a-date","status_history",List.of()));
        assertThrows(Validator.ValidationException.class, () -> Validator.validateTickets(raw, UTC));
    }

    @Test void missingFieldRejected() {
        List<Map<String,Object>> raw = new ArrayList<>();
        raw.add(mapOf("ticket_id","T1","priority","P1","assignee_group","G",
            "created_at","2026-01-12T09:00:00Z"));
        assertThrows(Validator.ValidationException.class, () -> Validator.validateTickets(raw, UTC));
    }

    @Test void unsortedHistoryHandled() {
        var c = cal(Set.of());
        var t = new Ticket("T1","P1","G", t("2026-01-12T09:00:00Z"), List.of(
            new Ticket.StatusEntry("RESOLVED", t("2026-01-12T13:00:00Z")),
            new Ticket.StatusEntry("IN_PROGRESS", t("2026-01-12T10:00:00Z"))));
        assertEquals("RESOLVED", t.currentStatus()); // sorted → last is RESOLVED
    }

    @Test void unresolvedTicketEvaluatedAtAsOf() {
        var c = cal(Set.of());
        var calc = new SlaCalculator(c, SlaPolicy.defaults());
        var t = new Ticket("T1","P1","G", t("2026-01-12T09:00:00Z"), List.of());
        var r = calc.compute(t, t("2026-01-15T10:00:00Z")); // still open days later
        assertTrue(r.breached());
        assertTrue(r.breachMinutes() > 0);
    }

    // helpers
    static ZonedDateTime t(String s) { return ZonedDateTime.parse(s).withZoneSameInstant(UTC); }

    static Map<String,Object> mapOf(Object... kv) {
        Map<String,Object> m = new LinkedHashMap<>();
        for (int i = 0; i < kv.length; i += 2) m.put((String) kv[i], kv[i+1]);
        return m;
    }
}