package com.sdsi.sla.io;

import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.StreamReadConstraints;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sdsi.sla.core.ValidationException;
import com.sdsi.sla.model.SlaPolicy;
import com.sdsi.sla.model.Ticket;

import java.io.IOException;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.DateTimeException;
import java.time.DayOfWeek;
import java.time.Duration;
import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.EnumSet;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.regex.Pattern;

/**
 * Reads and validates {@code sla_policy.json}, {@code holidays.json} and {@code tickets.json}.
 * Every file is treated as untrusted: sizes are capped, unknown fields and duplicate keys are rejected,
 * and every problem is reported with where it is.
 */
public final class InputLoader {

    static final long MAX_FILE_BYTES = 50L * 1024 * 1024;
    private static final Pattern ID = Pattern.compile("[A-Za-z0-9_.:#-]{1,64}");
    private static final Pattern GROUP = Pattern.compile("[\\p{L}\\p{M}\\p{N} &._/-]{1,60}");
    private static final Pattern STATUS = Pattern.compile("[A-Z_]{1,40}");
    private static final Set<String> POLICY_FIELDS =
            Set.of("timezone", "businessHours", "targetsHours", "statuses", "atRiskFraction");
    private static final Set<String> TICKET_FIELDS =
            Set.of("id", "title", "priority", "assigneeGroup", "createdAt", "statusHistory");

    private static final ObjectMapper MAPPER = new ObjectMapper()
            .enable(JsonParser.Feature.STRICT_DUPLICATE_DETECTION)
            .enable(DeserializationFeature.USE_BIG_DECIMAL_FOR_FLOATS);

    static {
        MAPPER.getFactory().setStreamReadConstraints(StreamReadConstraints.builder()
                .maxNestingDepth(16).maxStringLength(10_000).maxNumberLength(30).build());
    }

    /** One ticket that failed validation; {@code index} is its 0-based position in the file. */
    public record Rejected(int index, String id, List<String> errors) {
    }

    public record TicketBatch(List<Ticket> tickets, List<Rejected> rejected) {
    }

    private InputLoader() {
    }

    // ------------------------------------------------------------------ policy

    /** Reads the policy file, or returns the problem-statement defaults (IST) when {@code file} is null. */
    public static SlaPolicy loadPolicy(Path file) {
        return file == null ? SlaPolicy.defaults(ZoneId.of("Asia/Kolkata")) : parsePolicy(readFile(file));
    }

    public static SlaPolicy parsePolicy(String json) {
        JsonNode root = readTree(json, "policy");
        if (!root.isObject()) {
            throw new ValidationException("policy: must be a JSON object");
        }
        List<String> errors = new ArrayList<>();
        unknownFields(root, POLICY_FIELDS, "policy", errors);
        SlaPolicy d = SlaPolicy.defaults(ZoneId.of("Asia/Kolkata"));

        ZoneId zone = d.zone();
        if (root.has("timezone")) {
            try {
                zone = ZoneId.of(root.get("timezone").asText());
            } catch (DateTimeException e) {
                errors.add("policy.timezone: unknown time zone '" + root.get("timezone").asText() + "'");
            }
        }

        Set<DayOfWeek> days = d.workDays();
        LocalTime start = d.dayStart();
        LocalTime end = d.dayEnd();
        JsonNode bh = root.get("businessHours");
        if (bh != null) {
            unknownFields(bh, Set.of("days", "start", "end"), "policy.businessHours", errors);
            if (bh.has("days")) {
                days = EnumSet.noneOf(DayOfWeek.class);
                for (JsonNode n : bh.get("days")) {
                    DayOfWeek day = dayOfWeek(n.asText());
                    if (day == null) {
                        errors.add("policy.businessHours.days: '" + n.asText() + "' is not a day (use MON..SUN)");
                    } else {
                        days.add(day);
                    }
                }
                if (days.isEmpty() && errors.isEmpty()) {
                    errors.add("policy.businessHours.days: at least one working day is required");
                }
            }
            start = bh.has("start") ? time(bh.get("start"), "policy.businessHours.start", errors) : start;
            end = bh.has("end") ? time(bh.get("end"), "policy.businessHours.end", errors) : end;
            if (start != null && end != null && !start.isBefore(end)) {
                errors.add("policy.businessHours: start must be before end (overnight shifts are not supported)");
            }
        }

        Map<String, Duration> targets = d.targets();
        JsonNode th = root.get("targetsHours");
        if (th != null) {
            targets = new LinkedHashMap<>();
            if (!th.isObject() || th.isEmpty()) {
                errors.add("policy.targetsHours: must be an object like {\"P1\": 4}");
            } else {
                for (Map.Entry<String, JsonNode> e : th.properties()) {
                    String p = e.getKey().strip().toUpperCase(Locale.ROOT);
                    JsonNode v = e.getValue();
                    if (!ID.matcher(p).matches()) {
                        errors.add("policy.targetsHours: bad priority name '" + e.getKey() + "'");
                    } else if (!v.isNumber() || v.decimalValue().signum() <= 0
                            || v.decimalValue().compareTo(BigDecimal.valueOf(10_000)) > 0) {
                        errors.add("policy.targetsHours." + e.getKey() + ": must be a number of hours between 0 and 10000");
                    } else {
                        BigDecimal minutes = v.decimalValue().multiply(BigDecimal.valueOf(60));
                        if (minutes.stripTrailingZeros().scale() > 0) {
                            errors.add("policy.targetsHours." + e.getKey() + ": must be a whole number of minutes");
                        } else {
                            targets.put(p, Duration.ofMinutes(minutes.longValueExact()));
                        }
                    }
                }
            }
        }

        Set<String> running = d.runningStatuses();
        Set<String> paused = d.pausedStatuses();
        Set<String> stopped = d.stoppedStatuses();
        JsonNode st = root.get("statuses");
        if (st != null) {
            unknownFields(st, Set.of("running", "paused", "stopped"), "policy.statuses", errors);
            running = st.has("running") ? statusSet(st.get("running"), "running", errors) : running;
            paused = st.has("paused") ? statusSet(st.get("paused"), "paused", errors) : paused;
            stopped = st.has("stopped") ? statusSet(st.get("stopped"), "stopped", errors) : stopped;
            Set<String> seen = new HashSet<>();
            for (Set<String> s : List.of(running, paused, stopped)) {
                for (String x : s) {
                    if (!seen.add(x)) {
                        errors.add("policy.statuses: '" + x + "' appears in more than one list");
                    }
                }
            }
            if (running.isEmpty()) {
                errors.add("policy.statuses.running: at least one status is required");
            }
        }

        double atRisk = d.atRiskFraction();
        if (root.has("atRiskFraction")) {
            JsonNode v = root.get("atRiskFraction");
            if (!v.isNumber() || v.doubleValue() < 0 || v.doubleValue() > 1) {
                errors.add("policy.atRiskFraction: must be a number between 0 and 1");
            } else {
                atRisk = v.doubleValue();
            }
        }

        if (!errors.isEmpty()) {
            throw new ValidationException(errors);
        }
        return new SlaPolicy(zone, days, start, end, Map.copyOf(targets), running, paused, stopped, atRisk);
    }

    // ------------------------------------------------------------------ holidays

    /** Reads the holidays file, or returns none when {@code file} is null. */
    public static Set<LocalDate> loadHolidays(Path file) {
        return file == null ? Set.of() : parseHolidays(readFile(file));
    }

    /** Accepts {@code {"holidays": [...]}} or a bare array of "YYYY-MM-DD" strings or {"date", "name"} objects. */
    public static Set<LocalDate> parseHolidays(String json) {
        JsonNode root = readTree(json, "holidays");
        JsonNode items = root.isArray() ? root : root.get("holidays");
        if (items == null || !items.isArray()) {
            throw new ValidationException("holidays: expected an array or an object with a \"holidays\" array");
        }
        List<String> errors = new ArrayList<>();
        Set<LocalDate> out = new LinkedHashSet<>();
        for (int i = 0; i < items.size(); i++) {
            JsonNode n = items.get(i);
            String where = "holidays[" + i + "]";
            JsonNode date = n.isObject() ? n.get("date") : n;
            if (n.isObject()) {
                unknownFields(n, Set.of("date", "name"), where, errors);
            }
            if (date == null || !date.isTextual()) {
                errors.add(where + ": needs a date like \"2026-10-02\"");
                continue;
            }
            try {
                out.add(LocalDate.parse(date.asText().strip()));
            } catch (DateTimeParseException e) {
                errors.add(where + ": '" + date.asText() + "' is not a valid date (YYYY-MM-DD)");
            }
        }
        if (!errors.isEmpty()) {
            throw new ValidationException(errors);
        }
        return Set.copyOf(out);
    }

    // ------------------------------------------------------------------ tickets

    public static TicketBatch loadTickets(Path file, SlaPolicy policy) {
        return parseTickets(readFile(file), policy);
    }

    /** Accepts {@code {"tickets": [...]}}, a bare array, or a single ticket object. */
    public static TicketBatch parseTickets(String json, SlaPolicy policy) {
        JsonNode root = readTree(json, "tickets");
        List<JsonNode> items = new ArrayList<>();
        if (root.isArray()) {
            root.forEach(items::add);
        } else if (root.isObject() && root.has("tickets")) {
            JsonNode t = root.get("tickets");
            if (!t.isArray()) {
                throw new ValidationException("tickets: \"tickets\" must be an array");
            }
            if (root.size() > 1) {
                throw new ValidationException("tickets: only the \"tickets\" field is allowed at the top level");
            }
            t.forEach(items::add);
        } else if (root.isObject()) {
            items.add(root);
        } else {
            throw new ValidationException("tickets: expected an array of tickets or an object with a \"tickets\" array");
        }

        List<Ticket> ok = new ArrayList<>();
        List<Rejected> rejected = new ArrayList<>();
        Set<String> ids = new HashSet<>();
        for (int i = 0; i < items.size(); i++) {
            JsonNode n = items.get(i);
            String id = n.path("id").isTextual() ? n.get("id").asText() : null;
            List<String> errors = new ArrayList<>();
            Ticket t = ticket(n, policy, errors);
            if (t != null && !ids.add(t.id())) {
                errors.add("id '" + t.id() + "' is used by another ticket");
            }
            if (errors.isEmpty()) {
                ok.add(t);
            } else {
                rejected.add(new Rejected(i, id, errors));
            }
        }
        return new TicketBatch(List.copyOf(ok), List.copyOf(rejected));
    }

    private static Ticket ticket(JsonNode n, SlaPolicy policy, List<String> errors) {
        if (!n.isObject()) {
            errors.add("must be a JSON object");
            return null;
        }
        unknownFields(n, TICKET_FIELDS, "", errors);

        String id = text(n, "id");
        if (id == null || !ID.matcher(id).matches()) {
            errors.add("id is required: 1-64 chars of [A-Za-z0-9_.:#-]");
        }
        String priority = text(n, "priority");
        if (priority == null) {
            errors.add("priority is required");
        } else {
            priority = priority.strip().toUpperCase(Locale.ROOT);
            if (!policy.targets().containsKey(priority)) {
                errors.add("priority '" + priority + "' has no SLA target (known: "
                        + String.join(", ", policy.targets().keySet().stream().sorted().toList()) + ")");
            }
        }
        String group = text(n, "assigneeGroup");
        if (group == null || group.isBlank()) {
            group = "Unassigned";
        } else if (!GROUP.matcher(group.strip()).matches()) {
            errors.add("assigneeGroup must be 1-60 letters, digits, spaces or & . _ / -");
        } else {
            group = group.strip();
        }
        if (n.has("title") && !n.get("title").isTextual()) {
            errors.add("title must be a string");
        }

        Instant created = instant(n.get("createdAt"), "createdAt", policy.zone(), errors);

        List<Ticket.StatusChange> history = new ArrayList<>();
        JsonNode h = n.get("statusHistory");
        if (h != null && !h.isNull()) {
            if (!h.isArray()) {
                errors.add("statusHistory must be an array of {\"status\", \"at\"}");
            } else {
                for (int i = 0; i < h.size(); i++) {
                    JsonNode e = h.get(i);
                    String where = "statusHistory[" + i + "]";
                    if (!e.isObject()) {
                        errors.add(where + " must be an object");
                        continue;
                    }
                    unknownFields(e, Set.of("status", "at"), where, errors);
                    String status = normaliseStatus(text(e, "status"));
                    if (status == null || !STATUS.matcher(status).matches() || !policy.isKnownStatus(status)) {
                        errors.add(where + ".status '" + text(e, "status") + "' is not a known status");
                        continue;
                    }
                    Instant at = instant(e.get("at"), where + ".at", policy.zone(), errors);
                    if (at == null) {
                        continue;
                    }
                    if (created != null && at.isBefore(created)) {
                        errors.add(where + ".at is before createdAt");
                        continue;
                    }
                    history.add(new Ticket.StatusChange(status, at));
                }
            }
        }
        if (!errors.isEmpty()) {
            return null;
        }
        // List.sort is stable: changes with the same timestamp keep their file order.
        history.sort(Comparator.comparing(Ticket.StatusChange::at));
        return new Ticket(id, priority, group, created, List.copyOf(history));
    }

    /** "on hold", "On-Hold" and "ON_HOLD" all become ON_HOLD. */
    static String normaliseStatus(String raw) {
        return raw == null ? null : raw.strip().toUpperCase(Locale.ROOT).replaceAll("[\\s-]+", "_");
    }

    /**
     * Parses an ISO-8601 timestamp. With an offset ("2026-10-05T10:15:00+05:30" or "...Z") it is exact;
     * without one ("2026-10-05T10:15") it is read in the policy's time zone.
     */
    public static Instant parseInstant(String s, ZoneId zone) {
        String v = s.strip();
        try {
            return OffsetDateTime.parse(v).toInstant();
        } catch (DateTimeParseException ignored) {
            return LocalDateTime.parse(v).atZone(zone).toInstant();
        }
    }

    private static Instant instant(JsonNode v, String label, ZoneId zone, List<String> errors) {
        if (v == null || !v.isTextual()) {
            errors.add(label + " is required: an ISO-8601 time like 2026-10-05T10:15:00+05:30");
            return null;
        }
        try {
            return parseInstant(v.asText(), zone);
        } catch (DateTimeParseException e) {
            errors.add(label + " '" + v.asText() + "' is not an ISO-8601 time like 2026-10-05T10:15:00+05:30");
            return null;
        }
    }

    // ------------------------------------------------------------------ helpers

    private static Set<String> statusSet(JsonNode n, String label, List<String> errors) {
        Set<String> out = new LinkedHashSet<>();
        if (!n.isArray()) {
            errors.add("policy.statuses." + label + ": must be an array of names");
            return out;
        }
        for (JsonNode s : n) {
            String v = normaliseStatus(s.asText());
            if (v == null || !STATUS.matcher(v).matches()) {
                errors.add("policy.statuses." + label + ": bad status name '" + s.asText() + "'");
            } else {
                out.add(v);
            }
        }
        return Set.copyOf(out);
    }

    private static DayOfWeek dayOfWeek(String raw) {
        String s = raw.strip().toUpperCase(Locale.ROOT);
        for (DayOfWeek d : DayOfWeek.values()) {
            if (d.name().equals(s) || d.name().substring(0, 3).equals(s)) {
                return d;
            }
        }
        return null;
    }

    private static LocalTime time(JsonNode n, String label, List<String> errors) {
        try {
            return LocalTime.parse(n.asText().strip());
        } catch (DateTimeParseException e) {
            errors.add(label + ": '" + n.asText() + "' is not a time like 09:00");
            return null;
        }
    }

    private static String text(JsonNode n, String field) {
        JsonNode v = n.get(field);
        return v != null && v.isTextual() ? v.asText() : null;
    }

    private static void unknownFields(JsonNode node, Set<String> allowed, String where, List<String> errors) {
        node.fieldNames().forEachRemaining(f -> {
            if (!allowed.contains(f)) {
                errors.add((where.isEmpty() ? "" : where + ": ") + "unknown field '" + f
                        + "' (allowed: " + String.join(", ", allowed.stream().sorted().toList()) + ")");
            }
        });
    }

    private static String readFile(Path file) {
        try {
            if (!Files.isRegularFile(file)) {
                throw new ValidationException("file not found: " + file);
            }
            if (Files.size(file) > MAX_FILE_BYTES) {
                throw new ValidationException(file + " is larger than " + MAX_FILE_BYTES / (1024 * 1024) + " MB");
            }
            return Files.readString(file, StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new ValidationException("could not read " + file + ": " + e.getMessage());
        }
    }

    private static JsonNode readTree(String json, String what) {
        try {
            JsonNode root = MAPPER.readTree(json);
            if (root == null || root.isMissingNode()) {
                throw new ValidationException(what + ": the file is empty");
            }
            return root;
        } catch (JsonProcessingException e) {
            throw new ValidationException(what + ": not valid JSON: " + e.getOriginalMessage());
        }
    }
}
