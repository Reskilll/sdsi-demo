package com.sdsi.sla;

import com.sdsi.sla.core.ValidationException;
import com.sdsi.sla.io.InputLoader;
import com.sdsi.sla.model.SlaPolicy;
import com.sdsi.sla.model.Ticket;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

import java.nio.file.Path;
import java.time.DayOfWeek;
import java.time.Duration;
import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalTime;
import java.time.ZoneId;
import java.util.List;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class InputLoaderTest {

    private final SlaPolicy policy = SlaPolicy.defaults(ZoneId.of("Asia/Kolkata"));

    private static void assertInvalid(String fragment, Runnable r) {
        ValidationException e = assertThrows(ValidationException.class, r::run);
        assertTrue(e.getMessage().contains(fragment), "expected '" + fragment + "' in: " + e.getMessage());
    }

    private InputLoader.TicketBatch tickets(String json) {
        return InputLoader.parseTickets(json, policy);
    }

    private List<String> errorsOf(String ticketJson) {
        InputLoader.TicketBatch b = tickets("[" + ticketJson + "]");
        assertEquals(1, b.rejected().size(), "expected the ticket to be rejected");
        return b.rejected().get(0).errors();
    }

    // ------------------------------------------------------------------ policy

    @Test
    void samplePolicyMatchesProblemStatement() {
        SlaPolicy p = InputLoader.loadPolicy(Path.of("data/sla_policy.json"));
        assertEquals(Duration.ofHours(4), p.targets().get("P1"));
        assertEquals(Duration.ofHours(72), p.targets().get("P4"));
        assertEquals(LocalTime.of(9, 0), p.dayStart());
        assertEquals(Set.of(DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, DayOfWeek.THURSDAY,
                DayOfWeek.FRIDAY), p.workDays());
        assertEquals(InputLoader.loadPolicy(null), p); // the sample file spells out the built-in defaults
    }

    @Test
    void partialPolicyFallsBackToDefaults() {
        SlaPolicy p = InputLoader.parsePolicy("{\"timezone\":\"Europe/London\",\"targetsHours\":{\"p1\":0.5,\"P5\":120}}");
        assertEquals(ZoneId.of("Europe/London"), p.zone());
        assertEquals(Duration.ofMinutes(30), p.targets().get("P1"));
        assertEquals(Duration.ofHours(120), p.targets().get("P5"));
        assertEquals(LocalTime.of(18, 0), p.dayEnd());
    }

    @ParameterizedTest
    @CsvSource(delimiter = '|', value = {
            "{\"timezone\":\"Mars/Base\"}                                  | unknown time zone",
            "{\"businessHours\":{\"start\":\"18:00\",\"end\":\"09:00\"}}   | start must be before end",
            "{\"businessHours\":{\"start\":\"9am\"}}                       | not a time",
            "{\"businessHours\":{\"days\":[\"FUNDAY\"]}}                   | not a day",
            "{\"businessHours\":{\"days\":[]}}                             | at least one working day",
            "{\"targetsHours\":{\"P1\":-4}}                                | between 0 and 10000",
            "{\"targetsHours\":{\"P1\":\"4\"}}                             | between 0 and 10000",
            "{\"targetsHours\":{\"P1\":0.001}}                             | whole number of minutes",
            "{\"targetsHours\":{}}                                         | must be an object",
            "{\"statuses\":{\"paused\":[\"OPEN\"]}}                        | more than one list",
            "{\"atRiskFraction\":2}                                        | between 0 and 1",
            "{\"tz\":\"UTC\"}                                              | unknown field 'tz'",
            "[]                                                            | must be a JSON object",
            "not json                                                      | not valid JSON",
    })
    void rejectsBadPolicies(String json, String fragment) {
        assertInvalid(fragment, () -> InputLoader.parsePolicy(json));
    }

    // ------------------------------------------------------------------ holidays

    @Test
    void holidaysInEveryShape() {
        assertEquals(3, InputLoader.loadHolidays(Path.of("data/holidays.json")).size());
        assertEquals(Set.of(LocalDate.of(2026, 1, 26), LocalDate.of(2026, 8, 15)),
                InputLoader.parseHolidays("[\"2026-01-26\", {\"date\":\"2026-08-15\",\"name\":\"I-Day\"}, \"2026-01-26\"]"));
        assertEquals(Set.of(), InputLoader.loadHolidays(null));
    }

    @Test
    void rejectsBadHolidays() {
        assertInvalid("not a valid date", () -> InputLoader.parseHolidays("[\"2026-02-30\"]"));
        assertInvalid("needs a date", () -> InputLoader.parseHolidays("[{\"name\":\"x\"}]"));
        assertInvalid("expected an array", () -> InputLoader.parseHolidays("{\"days\":[]}"));
    }

    // ------------------------------------------------------------------ tickets

    @Test
    void sampleTicketsAllValid() {
        InputLoader.TicketBatch b = InputLoader.loadTickets(Path.of("data/tickets.json"), policy);
        assertTrue(b.rejected().isEmpty(), b.rejected().toString());
        assertEquals(10, b.tickets().size());
    }

    @Test
    void acceptsBareArraySingleObjectAndLocalTimes() {
        String one = "{\"id\":\"A\",\"priority\":\"p2\",\"assigneeGroup\":\"Desk\",\"createdAt\":\"2026-10-05T10:00\","
                + "\"statusHistory\":[{\"status\":\"on hold\",\"at\":\"2026-10-05T04:30:00Z\"}]}";
        Ticket t = tickets(one).tickets().get(0);
        assertEquals("P2", t.priority());
        assertEquals("ON_HOLD", t.history().get(0).status());
        // "2026-10-05T10:00" with no offset is read in the policy zone (IST), i.e. 04:30Z.
        assertEquals(Instant.parse("2026-10-05T04:30:00Z"), t.createdAt());
        assertEquals(1, tickets("[" + one + "]").tickets().size());
    }

    @Test
    void historyIsSortedByTime() {
        Ticket t = tickets("[{\"id\":\"A\",\"priority\":\"P1\",\"createdAt\":\"2026-10-05T09:00\",\"statusHistory\":["
                + "{\"status\":\"RESOLVED\",\"at\":\"2026-10-05T12:00\"},"
                + "{\"status\":\"IN_PROGRESS\",\"at\":\"2026-10-05T10:00\"}]}]").tickets().get(0);
        assertEquals(List.of("IN_PROGRESS", "RESOLVED"), t.history().stream().map(Ticket.StatusChange::status).toList());
        assertEquals("Unassigned", t.assigneeGroup());
    }

    @Test
    void reportsEveryProblemWithPosition() {
        InputLoader.TicketBatch b = tickets("""
                [{"id":"OK","priority":"P1","createdAt":"2026-10-05T09:00"},
                 {"id":"BAD","priority":"P9","createdAt":"yesterday","oops":1,
                  "statusHistory":[{"status":"PARKED","at":"2026-10-05T10:00"}]}]""");
        assertEquals(1, b.tickets().size());
        InputLoader.Rejected r = b.rejected().get(0);
        assertEquals(1, r.index());
        assertEquals("BAD", r.id());
        assertEquals(4, r.errors().size(), r.errors().toString());
    }

    @Test
    void individualTicketRules() {
        assertTrue(errorsOf("{\"priority\":\"P1\",\"createdAt\":\"2026-10-05T09:00\"}").get(0).contains("id is required"));
        assertTrue(errorsOf("{\"id\":\"a b\",\"priority\":\"P1\",\"createdAt\":\"2026-10-05T09:00\"}").get(0).contains("id is required"));
        assertTrue(errorsOf("{\"id\":\"A\",\"createdAt\":\"2026-10-05T09:00\"}").get(0).contains("priority is required"));
        assertTrue(errorsOf("{\"id\":\"A\",\"priority\":\"P1\"}").get(0).contains("createdAt is required"));
        assertTrue(errorsOf("{\"id\":\"A\",\"priority\":\"P1\",\"createdAt\":\"2026-10-05T09:00\",\"assigneeGroup\":\"<b>\"}")
                .get(0).contains("assigneeGroup"));
        assertTrue(errorsOf("{\"id\":\"A\",\"priority\":\"P1\",\"createdAt\":\"2026-10-05T09:00\",\"statusHistory\":"
                + "[{\"status\":\"RESOLVED\",\"at\":\"2026-10-04T09:00\"}]}").get(0).contains("before createdAt"));
        assertTrue(errorsOf("{\"id\":\"A\",\"priority\":\"P1\",\"createdAt\":\"2026-10-05T09:00\",\"statusHistory\":{}}")
                .get(0).contains("must be an array"));
    }

    @Test
    void duplicateIdsRejected() {
        InputLoader.TicketBatch b = tickets("[{\"id\":\"A\",\"priority\":\"P1\",\"createdAt\":\"2026-10-05T09:00\"},"
                + "{\"id\":\"A\",\"priority\":\"P2\",\"createdAt\":\"2026-10-05T09:00\"}]");
        assertEquals(1, b.tickets().size());
        assertTrue(b.rejected().get(0).errors().get(0).contains("used by another ticket"));
    }

    @ParameterizedTest
    @CsvSource(delimiter = '|', value = {
            "''                                     | file is empty",
            "{\"tickets\":{}}                       | must be an array",
            "{\"tickets\":[],\"extra\":1}           | only the \"tickets\" field",
            "42                                     | expected an array",
            "[{\"id\":\"A\",\"id\":\"B\"}]          | not valid JSON",
    })
    void rejectsBrokenTicketFiles(String json, String fragment) {
        assertInvalid(fragment, () -> tickets(json));
    }

    @Test
    void missingFile() {
        assertInvalid("file not found", () -> InputLoader.loadTickets(Path.of("nope.json"), policy));
    }
}
