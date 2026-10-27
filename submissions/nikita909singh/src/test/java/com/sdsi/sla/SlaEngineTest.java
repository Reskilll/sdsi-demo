package com.sdsi.sla;

import com.sdsi.sla.core.BusinessCalendar;
import com.sdsi.sla.core.SlaEngine;
import com.sdsi.sla.core.ValidationException;
import com.sdsi.sla.io.InputLoader;
import com.sdsi.sla.model.SlaPolicy;
import com.sdsi.sla.model.Summary;
import com.sdsi.sla.model.Ticket;
import com.sdsi.sla.model.Ticket.StatusChange;
import com.sdsi.sla.model.TicketResult;
import com.sdsi.sla.model.TicketResult.State;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

import java.nio.file.Path;
import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class SlaEngineTest {

    private static final ZoneId IST = ZoneId.of("Asia/Kolkata");
    private SlaPolicy policy;
    private SlaEngine engine;

    @BeforeEach
    void setUp() {
        policy = SlaPolicy.defaults(IST);
        engine = new SlaEngine(policy, new BusinessCalendar(policy, Set.of(LocalDate.of(2026, 10, 2))));
    }

    private static Instant t(String local) {
        return LocalDateTime.parse(local).atZone(IST).toInstant();
    }

    private static Ticket ticket(String priority, String created, String... statusAt) {
        List<StatusChange> h = new ArrayList<>();
        for (int i = 0; i < statusAt.length; i += 2) {
            h.add(new StatusChange(statusAt[i], t(statusAt[i + 1])));
        }
        return new Ticket("T", priority, "G", t(created), h);
    }

    /** Hand-computed expectations for every ticket in data/tickets.json, as of Fri 2026-10-16 18:00. */
    @ParameterizedTest(name = "{0}: {1} min, due {2}, breach {3}, {4}")
    @CsvSource({
            "T-1001, 180,  2026-10-05T14:00, 0,    MET",       // simple same-day fix
            "T-1002, 300,  2026-10-05T11:00, 60,   BREACHED",  // over a holiday + weekend, still late
            "T-1003, 240,  2026-10-09T12:00, 0,    MET",       // ON_HOLD for ~1.5 days not counted
            "T-1004, 2940, 2026-10-14T11:00, 1500, BREACHED",  // still open and long overdue
            "T-1005, 720,  ,                 0,    PAUSED",    // on hold at as-of: due-by unknown
            "T-1006, 420,  2026-10-19T10:00, 0,    AT_RISK",   // 60 of 480 min left (< 25%)
            "T-1007, 900,  2026-10-16T16:00, 0,    MET",       // RESOLVED then CLOSED: projected from resolution
            "T-1008, 210,  2026-10-12T13:00, 0,    MET",       // raised on Saturday: clock starts Monday 09:00
            "T-1009, 330,  2026-10-19T11:30, 0,    ON_TRACK",  // resolved then reopened: time adds up
            "T-1010, 540,  2026-10-28T18:00, 0,    ON_TRACK",  // due-by skips the 2026-10-20 holiday
    })
    void sampleTicketsMatchHandCalculation(String id, long elapsed, String due, long breach, State state) {
        SlaPolicy p = InputLoader.loadPolicy(Path.of("data/sla_policy.json"));
        SlaEngine e = new SlaEngine(p, new BusinessCalendar(p, InputLoader.loadHolidays(Path.of("data/holidays.json"))));
        InputLoader.TicketBatch batch = InputLoader.loadTickets(Path.of("data/tickets.json"), p);
        Ticket ticket = batch.tickets().stream().filter(x -> x.id().equals(id)).findFirst().orElseThrow();

        TicketResult r = e.evaluate(ticket, t("2026-10-16T18:00"));
        assertEquals(elapsed, r.elapsedMinutes(), "elapsed");
        assertEquals(due == null ? null : t(due), r.dueBy() == null ? null : r.dueBy().toInstant(), "dueBy");
        assertEquals(breach, r.breachMinutes(), "breach minutes");
        assertEquals(breach > 0, r.breached());
        assertEquals(state, r.state());
    }

    @Test
    void resolvedExactlyAtTargetIsNotABreach() {
        TicketResult r = engine.evaluate(ticket("P1", "2026-10-05T09:00", "RESOLVED", "2026-10-05T13:00"),
                t("2026-10-30T00:00"));
        assertEquals(240, r.elapsedMinutes());
        assertFalse(r.breached());
        assertEquals(State.MET, r.state());
        assertEquals(t("2026-10-05T13:00"), r.dueBy().toInstant());
    }

    @Test
    void oneSecondLateIsABreachOfOneMinute() {
        Ticket tk = new Ticket("T", "P1", "G", t("2026-10-05T09:00"),
                List.of(new StatusChange("RESOLVED", t("2026-10-05T13:00").plusSeconds(1))));
        TicketResult r = engine.evaluate(tk, t("2026-10-30T00:00"));
        assertTrue(r.breached());
        assertEquals(1, r.breachMinutes());
    }

    @Test
    void holdOverWeekendDoesNotCount() {
        // Fri 16:00 on hold until Mon 11:00, resolved Mon 12:00 -> 2h Fri + 1h Mon = 180 min.
        TicketResult r = engine.evaluate(ticket("P1", "2026-10-09T16:00",
                "ON_HOLD", "2026-10-09T18:00", "IN_PROGRESS", "2026-10-12T11:00", "RESOLVED", "2026-10-12T12:00"),
                t("2026-10-30T00:00"));
        assertEquals(180, r.elapsedMinutes());
    }

    @Test
    void multipleHoldsAndReopens() {
        TicketResult r = engine.evaluate(ticket("P2", "2026-10-05T09:00",
                "ON_HOLD", "2026-10-05T10:00",       // +60
                "IN_PROGRESS", "2026-10-05T12:00",
                "ON_HOLD", "2026-10-05T13:00",       // +60
                "IN_PROGRESS", "2026-10-06T09:00",
                "RESOLVED", "2026-10-06T10:00",      // +60
                "REOPENED", "2026-10-07T09:00",
                "CLOSED", "2026-10-07T09:30"),       // +30
                t("2026-10-30T00:00"));
        assertEquals(210, r.elapsedMinutes());
        assertTrue(r.resolved());
    }

    @Test
    void breachDetectedWhileOnHold() {
        // Ran 5h (over the 4h P1 target), then went on hold: breached, and due-by is known.
        TicketResult r = engine.evaluate(ticket("P1", "2026-10-05T09:00", "ON_HOLD", "2026-10-05T14:00"),
                t("2026-10-06T18:00"));
        assertTrue(r.breached());
        assertEquals(60, r.breachMinutes());
        assertEquals(State.BREACHED, r.state());
        assertEquals(t("2026-10-05T13:00"), r.dueBy().toInstant());
    }

    @Test
    void eventsAfterAsOfAreIgnored() {
        Ticket tk = ticket("P1", "2026-10-05T09:00", "RESOLVED", "2026-10-05T12:00");
        TicketResult before = engine.evaluate(tk, t("2026-10-05T11:00"));
        assertEquals(120, before.elapsedMinutes());
        assertEquals("OPEN", before.currentStatus());
        assertFalse(before.resolved());
        assertEquals(180, engine.evaluate(tk, t("2026-10-06T11:00")).elapsedMinutes());
    }

    @Test
    void ticketCreatedAfterAsOfIsRejected() {
        assertThrows(ValidationException.class,
                () -> engine.evaluate(ticket("P1", "2026-10-06T09:00"), t("2026-10-05T09:00")));
    }

    @Test
    void ticketCreatedOnHoldStartsPaused() {
        TicketResult r = engine.evaluate(ticket("P3", "2026-10-05T09:00", "ON_HOLD", "2026-10-05T09:00"),
                t("2026-10-09T18:00"));
        assertEquals(0, r.elapsedMinutes());
        assertEquals(State.PAUSED, r.state());
        assertNull(r.dueBy());
    }

    @Test
    void customRunningStatusWithoutOpen() {
        SlaPolicy p = new SlaPolicy(IST, policy.workDays(), policy.dayStart(), policy.dayEnd(), policy.targets(),
                Set.of("WORKING"), Set.of("WAITING"), Set.of("DONE"), 0.25);
        SlaEngine e = new SlaEngine(p, new BusinessCalendar(p, Set.of()));
        assertEquals(60, e.evaluate(ticket("P1", "2026-10-05T09:00", "DONE", "2026-10-05T10:00"),
                t("2026-10-06T09:00")).elapsedMinutes());
    }

    @Test
    void summaryPercentagesPerPriorityAndGroup() {
        SlaPolicy p = InputLoader.loadPolicy(Path.of("data/sla_policy.json"));
        SlaEngine e = new SlaEngine(p, new BusinessCalendar(p, InputLoader.loadHolidays(Path.of("data/holidays.json"))));
        List<TicketResult> results = e.evaluateAll(
                InputLoader.loadTickets(Path.of("data/tickets.json"), p).tickets(), t("2026-10-16T18:00"));
        Summary s = e.summarize(results);

        assertEquals(new Summary.Bucket("ALL", 10, 2, 5, 20.0), s.overall());
        Map<String, Summary.Bucket> byP = s.byPriority().stream().collect(Collectors.toMap(Summary.Bucket::key, b -> b));
        assertEquals(33.33, byP.get("P1").breachPercent());
        assertEquals(0.0, byP.get("P2").breachPercent());
        assertEquals(50.0, byP.get("P3").breachPercent());
        Map<String, Summary.Bucket> byG = s.byAssigneeGroup().stream().collect(Collectors.toMap(Summary.Bucket::key, b -> b));
        assertEquals(25.0, byG.get("Network").breachPercent());
        assertEquals(1, byG.get("Unassigned").total());
    }

    @Test
    void emptySummary() {
        Summary s = engine.summarize(List.of());
        assertEquals(0, s.overall().total());
        assertEquals(0.0, s.overall().breachPercent());
        assertTrue(s.byPriority().isEmpty());
    }

    @Test
    void longOpenTicketIsFast() {
        // Open for ~3 years: the day-by-day walk is still trivial.
        long start = System.nanoTime();
        for (int i = 0; i < 1_000; i++) {
            engine.evaluate(ticket("P4", "2023-01-02T09:00"), t("2026-01-02T09:00"));
        }
        assertTrue((System.nanoTime() - start) / 1_000_000 < 5_000, "1000 three-year tickets took too long");
    }
}
