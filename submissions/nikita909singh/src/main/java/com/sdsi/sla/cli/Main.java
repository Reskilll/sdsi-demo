package com.sdsi.sla.cli;

import com.sdsi.sla.core.BusinessCalendar;
import com.sdsi.sla.core.SlaEngine;
import com.sdsi.sla.core.ValidationException;
import com.sdsi.sla.io.InputLoader;
import com.sdsi.sla.io.ReportWriter;
import com.sdsi.sla.model.SlaPolicy;
import com.sdsi.sla.model.Summary;
import com.sdsi.sla.model.Ticket;
import com.sdsi.sla.model.TicketResult;

import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.time.Clock;
import java.time.Instant;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** Command-line entry point. Exit codes: 0 success, 1 invalid data, 2 bad command line. */
public final class Main {

    static final String USAGE = """
            Usage:
              report   --tickets FILE [--policy FILE] [--holidays FILE] [--as-of TIME]
                       [--json | --csv] [--skip-invalid]
              validate --tickets FILE [--policy FILE] [--holidays FILE]

              --policy    SLA targets, business hours, time zone (default: P1 4h, P2 8h, P3 24h, P4 72h,
                          Mon-Fri 09:00-18:00, Asia/Kolkata)
              --holidays  dates excluded from SLA time (default: none)
              --as-of     measure open tickets up to this time, e.g. 2026-10-16T18:00 (default: now)
              --skip-invalid  report invalid tickets and continue with the rest (default: stop)
            """;

    private static final Set<String> FLAGS = Set.of("json", "csv", "skip-invalid");
    private static final Set<String> VALUED = Set.of("tickets", "policy", "holidays", "as-of");

    private Main() {
    }

    public static void main(String[] args) {
        PrintStream out = new PrintStream(System.out, true, StandardCharsets.UTF_8);
        PrintStream err = new PrintStream(System.err, true, StandardCharsets.UTF_8);
        System.exit(run(args, out, err, Clock.systemUTC()));
    }

    /** Testable entry point: returns the exit code; {@code clock} supplies "now" when --as-of is absent. */
    public static int run(String[] args, PrintStream out, PrintStream err, Clock clock) {
        if (args.length == 0 || args[0].equals("help") || args[0].equals("--help")) {
            out.print(USAGE);
            return args.length == 0 ? 2 : 0;
        }
        Map<String, String> opts;
        try {
            opts = parseOptions(args);
            if (!opts.containsKey("tickets")) {
                throw new IllegalArgumentException("--tickets is required");
            }
            if (opts.containsKey("json") && opts.containsKey("csv")) {
                throw new IllegalArgumentException("choose either --json or --csv");
            }
            if (!args[0].equals("report") && !args[0].equals("validate")) {
                throw new IllegalArgumentException("unknown command '" + args[0] + "'");
            }
        } catch (IllegalArgumentException e) {
            err.println("error: " + e.getMessage());
            err.print(USAGE);
            return 2;
        }

        try {
            SlaPolicy policy = InputLoader.loadPolicy(path(opts.get("policy")));
            BusinessCalendar calendar = new BusinessCalendar(policy, InputLoader.loadHolidays(path(opts.get("holidays"))));
            Instant asOf = asOf(opts.get("as-of"), policy, clock);
            InputLoader.TicketBatch batch = InputLoader.loadTickets(Path.of(opts.get("tickets")), policy);

            SlaEngine engine = new SlaEngine(policy, calendar);
            List<TicketResult> results = new ArrayList<>();
            List<InputLoader.Rejected> rejected = new ArrayList<>(batch.rejected());
            for (Ticket t : batch.tickets()) {
                try {
                    results.add(engine.evaluate(t, asOf));
                } catch (ValidationException e) {
                    rejected.add(new InputLoader.Rejected(-1, t.id(), e.errors()));
                }
            }

            if (!rejected.isEmpty() && (args[0].equals("validate") || !opts.containsKey("skip-invalid"))) {
                err.println(rejected.size() + " invalid ticket(s):");
                for (InputLoader.Rejected r : rejected) {
                    err.println("  " + (r.index() >= 0 ? "#" + (r.index() + 1) + " " : "")
                            + (r.id() == null ? "(no id)" : r.id()) + ":");
                    r.errors().forEach(m -> err.println("      - " + m));
                }
                if (args[0].equals("report")) {
                    err.println("No report printed. Fix the tickets above, or rerun with --skip-invalid.");
                }
                return 1;
            }
            if (args[0].equals("validate")) {
                out.println("OK: " + results.size() + " ticket(s), " + policy.targets().size()
                        + " priorities, no problems found.");
                return 0;
            }

            Summary summary = engine.summarize(results);
            var asOfZoned = asOf.atZone(policy.zone());
            if (opts.containsKey("json")) {
                out.println(ReportWriter.json(asOfZoned, results, summary, rejected));
            } else if (opts.containsKey("csv")) {
                out.print(ReportWriter.csv(results));
            } else {
                out.print(ReportWriter.text(asOfZoned, results, summary, rejected));
            }
            return 0;
        } catch (ValidationException e) {
            err.println("error:");
            e.errors().forEach(m -> err.println("  - " + m));
            return 1;
        }
    }

    private static Instant asOf(String raw, SlaPolicy policy, Clock clock) {
        if (raw == null) {
            return clock.instant();
        }
        try {
            return InputLoader.parseInstant(raw, policy.zone());
        } catch (DateTimeParseException e) {
            throw new ValidationException("--as-of '" + raw + "' is not an ISO-8601 time like 2026-10-16T18:00");
        }
    }

    private static Path path(String p) {
        return p == null ? null : Path.of(p);
    }

    static Map<String, String> parseOptions(String[] args) {
        Map<String, String> opts = new HashMap<>();
        for (int i = 1; i < args.length; i++) {
            String a = args[i];
            if (!a.startsWith("--")) {
                throw new IllegalArgumentException("unexpected argument '" + a + "'");
            }
            String key = a.substring(2);
            if (FLAGS.contains(key)) {
                opts.put(key, "true");
            } else if (VALUED.contains(key)) {
                if (i + 1 >= args.length) {
                    throw new IllegalArgumentException(a + " needs a value");
                }
                opts.put(key, args[++i]);
            } else {
                throw new IllegalArgumentException("unknown option " + a);
            }
        }
        return opts;
    }
}
