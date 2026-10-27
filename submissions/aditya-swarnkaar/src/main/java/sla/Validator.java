package sla;

import java.time.*;
import java.time.format.DateTimeParseException;
import java.util.*;

/**
 * Validates input tickets, SLA policy, and holiday definitions.
 * Throws ValidationException with actionable messages.
 */
public class Validator {

    public static final Set<String> VALID_PRIORITIES = Set.of("P1", "P2", "P3", "P4");
    public static final Set<String> VALID_STATUSES =
        Set.of("NEW", "ASSIGNED", "IN_PROGRESS", "ON_HOLD",
               "RESOLVED", "CLOSED", "CANCELLED", "REOPENED");

    /** Parse and validate tickets.json structure. */
    public static List<Ticket> validateTickets(List<Map<String, Object>> raw,
                                                ZoneId zone) {
        Set<String> seen = new HashSet<>();
        List<Ticket> tickets = new ArrayList<>();
        if (raw == null) throw new ValidationException("tickets: missing or null array");

        for (int i = 0; i < raw.size(); i++) {
            var r = raw.get(i);
            if (!(r instanceof Map))
                throw new ValidationException("tickets[" + i + "]: not a JSON object");
            tickets.add(validateOneTicket(r, zone, seen));
        }
        return tickets;
    }

    @SuppressWarnings("unchecked")
    private static Ticket validateOneTicket(Map<String, Object> r, ZoneId zone,
                                             Set<String> seen) {
        String id = requireString(r, "ticket_id");
        if (!seen.add(id))
            throw new ValidationException("Duplicate ticket_id: " + id);

        String priority = requireString(r, "priority");
        if (!VALID_PRIORITIES.contains(priority))
            throw new ValidationException(id + ": unknown priority '" + priority + "'");

        String group = requireString(r, "assignee_group");

        ZonedDateTime created = parseTimestamp(requireString(r, "created_at"), zone);

        List<Ticket.StatusEntry> history = new ArrayList<>();
        var rawHist = (List<?>) r.get("status_history");
        if (rawHist == null)
            throw new ValidationException(id + ": missing status_history");

        for (int j = 0; j < rawHist.size(); j++) {
            Object hObj = rawHist.get(j);
            if (!(hObj instanceof Map))
                throw new ValidationException(id + ".status_history[" + j + "]: not an object");
            var hm = (Map<String, Object>) hObj;
            String st = requireString(hm, "status");
            if (!VALID_STATUSES.contains(st))
                throw new ValidationException(id + ".status_history[" + j + "]: unknown status '" + st + "'");
            ZonedDateTime ts = parseTimestamp(requireString(hm, "timestamp"), zone);
            if (!ts.isAfter(created) && !ts.equals(created))
                throw new ValidationException(id + ": history entry before creation time");
            history.add(new Ticket.StatusEntry(st, ts));
        }
        return new Ticket(id, priority, group, created, history);
    }

    /** Parse and validate SLA policy. */
    public static SlaPolicy validatePolicy(Map<String, Object> raw) {
        if (raw == null || raw.isEmpty())
            return SlaPolicy.defaults();

        Map<String, Long> targets = new HashMap<>();
        for (var e : raw.entrySet()) {
            String k = e.getKey();
            if (!VALID_PRIORITIES.contains(k))
                throw new ValidationException("sla_policy: unknown priority '" + k + "'");
            Object v = e.getValue();
            long mins;
            if (v instanceof Number n) {
                mins = n.longValue();
            } else {
                throw new ValidationException("sla_policy." + k + ": not a number");
            }
            if (mins < 0)
                throw new ValidationException("sla_policy." + k + ": negative target");
            targets.put(k, mins);
        }
        // Fill missing priorities with defaults
        for (var p : VALID_PRIORITIES) targets.putIfAbsent(p, SlaPolicy.DEFAULTS.get(p));
        return new SlaPolicy(targets);
    }

    /** Parse and validate holidays. */
    public static Set<LocalDate> validateHolidays(List<String> raw, ZoneId zone) {
        if (raw == null) return Set.of();
        Set<LocalDate> out = new HashSet<>();
        for (int i = 0; i < raw.size(); i++) {
            try {
                out.add(LocalDate.parse(raw.get(i)));
            } catch (DateTimeParseException e) {
                throw new ValidationException("holidays[" + i + "]: invalid date '" +
                    raw.get(i) + "' (expected YYYY-MM-DD)");
            }
        }
        return out;
    }

    private static String requireString(Map<String, Object> map, String key) {
        Object v = map.get(key);
        if (v == null)
            throw new ValidationException("Missing field: " + key);
        if (!(v instanceof String s) || s.isBlank())
            throw new ValidationException("Field '" + key + "' must be a non-empty string");
        return s;
    }

    static ZonedDateTime parseTimestamp(String s, ZoneId zone) {
        try {
            // Accept ISO-8601 with or without zone offset
            if (s.endsWith("Z") || s.contains("+") || s.lastIndexOf('-') > 8) {
                return ZonedDateTime.parse(s).withZoneSameInstant(zone);
            }
            // Treat as naive → attach zone
            return ZonedDateTime.of(LocalDateTime.parse(s), zone);
        } catch (DateTimeParseException e) {
            throw new ValidationException("Invalid timestamp: " + s);
        }
    }

    public static class ValidationException extends RuntimeException {
        public ValidationException(String msg) { super(msg); }
    }
}