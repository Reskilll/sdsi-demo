package com.sdsi.sla;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sdsi.sla.cli.Main;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** Runs the CLI in-process with a fixed clock and checks exit codes and output. */
class MainTest {

    private static final String[] INPUTS = {"--tickets", "data/tickets.json", "--policy", "data/sla_policy.json",
            "--holidays", "data/holidays.json"};
    private static final Clock FRIDAY_6PM = Clock.fixed(Instant.parse("2026-10-16T12:30:00Z"), ZoneOffset.UTC);

    private ByteArrayOutputStream out;
    private ByteArrayOutputStream err;

    @BeforeEach
    void streams() {
        out = new ByteArrayOutputStream();
        err = new ByteArrayOutputStream();
    }

    private int run(String... args) {
        return Main.run(args, new PrintStream(out, true, StandardCharsets.UTF_8),
                new PrintStream(err, true, StandardCharsets.UTF_8), FRIDAY_6PM);
    }

    private static String[] with(String command, String... extra) {
        String[] a = new String[1 + INPUTS.length + extra.length];
        a[0] = command;
        System.arraycopy(INPUTS, 0, a, 1, INPUTS.length);
        System.arraycopy(extra, 0, a, 1 + INPUTS.length, extra.length);
        return a;
    }

    private String out() {
        return out.toString(StandardCharsets.UTF_8);
    }

    private String err() {
        return err.toString(StandardCharsets.UTF_8);
    }

    @Test
    void textReport() {
        assertEquals(0, run(with("report", "--as-of", "2026-10-16T18:00")));
        String o = out();
        assertTrue(o.contains("SLA report as of 2026-10-16 18:00 Asia/Kolkata: 10 ticket(s)"), o);
        assertTrue(o.matches("(?s).*T-1002 +P1 +Network +RESOLVED +240 +300 +2026-10-05 11:00 YES +60 +BREACHED.*"), o);
        assertTrue(o.contains("(paused)"));
        assertTrue(o.matches("(?s).*ALL +10 ticket\\(s\\), +2 breached, +5 open +20\\.00% breached.*"), o);
    }

    @Test
    void asOfDefaultsToNow() {
        // The fixed clock is Fri 2026-10-16 18:00 IST, so the default matches the explicit --as-of.
        assertEquals(0, run(with("report")));
        String implicit = out();
        streams();
        run(with("report", "--as-of", "2026-10-16T18:00+05:30"));
        assertEquals(out(), implicit);
    }

    @Test
    void jsonReport() throws Exception {
        assertEquals(0, run(with("report", "--as-of", "2026-10-16T18:00", "--json")));
        JsonNode root = new ObjectMapper().readTree(out());
        assertEquals(10, root.get("tickets").size());
        JsonNode t4 = root.get("tickets").get(3);
        assertEquals("T-1004", t4.get("id").asText());
        assertEquals(2940, t4.get("elapsedBusinessMinutes").asInt());
        assertEquals("2026-10-14T11:00+05:30", t4.get("dueBy").asText());
        assertTrue(t4.get("breached").asBoolean());
        assertEquals(20.0, root.get("summary").get("overall").get("breachPercent").asDouble());
        assertTrue(root.get("tickets").get(4).get("dueBy").isNull());
    }

    @Test
    void csvReport() {
        assertEquals(0, run(with("report", "--as-of", "2026-10-16T18:00", "--csv")));
        String[] lines = out().split("\n");
        assertEquals(11, lines.length);
        assertTrue(lines[0].startsWith("id,priority,assigneeGroup"));
        assertTrue(lines[2].startsWith("T-1002,P1,Network,RESOLVED,240,300,2026-10-05T11:00+05:30,true,60,BREACHED"), lines[2]);
    }

    @Test
    void validate() {
        assertEquals(0, run(with("validate")));
        assertTrue(out().startsWith("OK: 10 ticket(s)"), out());
    }

    @Test
    void invalidTicketsStopTheReportUnlessSkipped(@TempDir Path dir) throws Exception {
        Path f = dir.resolve("t.json");
        Files.writeString(f, """
                [{"id":"GOOD","priority":"P1","createdAt":"2026-10-05T09:00"},
                 {"id":"BAD","priority":"P7","createdAt":"2026-10-05T09:00"},
                 {"id":"FUTURE","priority":"P1","createdAt":"2027-01-01T09:00"}]""");
        assertEquals(1, run("report", "--tickets", f.toString(), "--as-of", "2026-10-16T18:00"));
        assertTrue(err().contains("2 invalid ticket(s)"), err());
        assertTrue(err().contains("priority 'P7' has no SLA target"), err());
        assertTrue(err().contains("created after the as-of time"), err());
        assertEquals("", out());

        streams();
        assertEquals(0, run("report", "--tickets", f.toString(), "--as-of", "2026-10-16T18:00", "--skip-invalid"));
        assertTrue(out().contains("SKIPPED (invalid)"), out());
        assertTrue(out().contains(": 1 ticket(s)"), out());
    }

    @Test
    void builtInDefaultsWhenNoPolicyOrHolidays() {
        assertEquals(0, run("report", "--tickets", "data/tickets.json", "--as-of", "2026-10-16T18:00"));
        // Without the holidays file, T-1002 also counts Fri 2026-10-02: 120 + 540 + 180 = 840 minutes.
        assertTrue(out().matches("(?s).*T-1002 .* 840 .*"), out());
    }

    @Test
    void badCommandLines() {
        assertEquals(2, run());
        assertEquals(2, run("report"));
        assertEquals(2, run("frobnicate", "--tickets", "x"));
        assertEquals(2, run(with("report", "--bogus")));
        assertEquals(2, run(with("report", "--json", "--csv")));
        assertEquals(2, run("report", "--tickets"));
        assertEquals(1, run(with("report", "--as-of", "next tuesday")));
        assertEquals(1, run("report", "--tickets", "missing.json"));
        assertEquals(1, run("report", "--tickets", "data/tickets.json", "--policy", "data/holidays.json"));
    }
}
