package sla;

import java.time.*;
import java.util.*;

/**
 * Entry point: reads input JSON files, computes SLA, outputs results.
 *
 * Usage: java sla.Main <tickets.json> [sla_policy.json] [holidays.json] [--output results.json]
 * Options:
 *   --zone         Timezone (default UTC — IANA ID e.g. "America/New_York")
 *   --as-of        Evaluation cutoff (ISO-8601), default: now
 *   --output       Output file path, default: stdout
 */
public class Main {

    public static void main(String[] args) {
        try {
            run(args);
        } catch (Validator.ValidationException e) {
            System.err.println("VALIDATION ERROR: " + e.getMessage());
            System.exit(2);
        } catch (Exception e) {
            System.err.println("ERROR: " + e.getMessage());
            e.printStackTrace();
            System.exit(1);
        }
    }

    static void run(String[] args) {
        List<String> positional = new ArrayList<>();
        String zoneId = "UTC";
        String asOfStr = null;
        String outputPath = null;

        for (int i = 0; i < args.length; i++) {
            switch (args[i]) {
                case "--zone" -> zoneId = args[++i];
                case "--as-of" -> asOfStr = args[++i];
                case "--output" -> outputPath = args[++i];
                default -> positional.add(args[i]);
            }
        }

        if (positional.isEmpty()) {
            System.err.println("Usage: java sla.Main <tickets.json> [sla_policy.json] [holidays.json] [--zone TZ] [--as-of ISO] [--output out.json]");
            System.exit(1);
            return;
        }

        String ticketsPath = positional.get(0);
        String policyPath = positional.size() > 1 ? positional.get(1) : null;
        String holidaysPath = positional.size() > 2 ? positional.get(2) : null;

        ZoneId zone = ZoneId.of(zoneId);
        ZonedDateTime asOf = (asOfStr != null)
            ? ZonedDateTime.parse(asOfStr).withZoneSameInstant(zone)
            : ZonedDateTime.now(zone);

        var raw = IoConfig.readInput(ticketsPath, policyPath, holidaysPath);

        // Validate
        var tickets = Validator.validateTickets(raw.tickets(), zone);
        var policy = Validator.validatePolicy(raw.policy());
        var holidays = Validator.validateHolidays(raw.holidays(), zone);

        var cal = new BusinessCalendar(zone, holidays);
        var calc = new SlaCalculator(cal, policy);

        // Compute
        List<SlaCalculator.TicketResult> results = new ArrayList<>();
        for (var t : tickets) results.add(calc.compute(t, asOf));

        // Summary
        StringBuilder sb = new StringBuilder();
        summaryText(sb, results, tickets, asOf, zone);

        // Output
        if (outputPath != null) {
            IoConfig.writeResults(outputPath, results, sb.toString());
            System.out.println("Results written to: " + outputPath);
        }
        System.out.println(sb);
    }

    static void summaryText(StringBuilder sb,
                            List<SlaCalculator.TicketResult> results,
                            List<Ticket> tickets,
                            ZonedDateTime asOf, ZoneId zone) {
        sb.append("SLA Tracker Summary\n");
        sb.append("Evaluated at: ").append(asOf.withZoneSameInstant(ZoneOffset.UTC)).append("\n");
        sb.append("Timezone: ").append(zone).append("\n");
        sb.append(String.format("Tickets: %d total | %d breached\n\n",
            results.size(), results.stream().filter(r -> r.breached()).count()));

        // By priority
        sb.append("By Priority:\n");
        sb.append(String.format("%-12s %8s %8s %8s\n", "Priority", "Total", "Breached", "Breach%"));
        for (String pri : List.of("P1","P2","P3","P4")) {
            var group = results.stream().filter(r -> r.priority().equals(pri)).toList();
            int total = group.size();
            long breached = group.stream().filter(r -> r.breached()).count();
            double pct = total > 0 ? 100.0 * breached / total : 0.0;
            sb.append(String.format("%-12s %8d %8d %7.1f%%\n", pri, total, breached, pct));
        }

        // By assignee group
        sb.append("\nBy Assignee Group:\n");
        sb.append(String.format("%-20s %8s %8s %8s\n", "Group", "Total", "Breached", "Breach%"));
        var byGroup = new TreeMap<String, List<SlaCalculator.TicketResult>>();
        for (var r : results)
            byGroup.computeIfAbsent(r.group(), k -> new ArrayList<>()).add(r);
        for (var e : byGroup.entrySet()) {
            int total = e.getValue().size();
            long breached = e.getValue().stream().filter(r -> r.breached()).count();
            double pct = total > 0 ? 100.0 * breached / total : 0.0;
            sb.append(String.format("%-20s %8d %8d %7.1f%%\n",
                e.getKey(), total, breached, pct));
        }

        // Per-ticket detail
        sb.append("\nPer-Ticket Detail:\n");
        sb.append(String.format("%-12s %-4s %-10s %-10s %6s %6s %s\n",
            "TicketID", "Pri", "Status", "Elapsed", "Target", "Breach", "DueBy"));
        for (var r : results) {
            sb.append(String.format("%-12s %-4s %-10s %6d %6d %6s %s\n",
                r.ticketId(), r.priority(), r.status(),
                r.elapsedMinutes(), r.slaTargetMinutes(),
                r.breached() ? "+" + r.breachMinutes() : "OK",
                r.dueBy().withZoneSameInstant(ZoneOffset.UTC)
                    .format(java.time.format.DateTimeFormatter.ISO_OFFSET_DATE_TIME)));
        }
    }
}