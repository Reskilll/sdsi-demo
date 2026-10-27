package sla;

import java.time.*;
import java.time.format.DateTimeFormatter;
import java.util.*;

import com.google.gson.*;

/**
 * Reads and writes JSON input/output files using Gson.
 */
public class IoConfig {

    public static final ZoneId DEFAULT_ZONE = ZoneId.of("UTC");
    private static final Gson GSON = new GsonBuilder()
        .setPrettyPrinting()
        .disableHtmlEscaping()
        .create();

    record RawInput(List<Map<String, Object>> tickets,
                    Map<String, Object> policy,
                    List<String> holidays) {}

    @SuppressWarnings("unchecked")
    public static RawInput readInput(String ticketsPath, String policyPath,
                                      String holidaysPath) {
        try {
            var root = GSON.fromJson(new java.io.FileReader(ticketsPath),
                                     com.google.gson.JsonObject.class);
            var tArr = root.getAsJsonArray("tickets");
            List<Map<String, Object>> tickets = GSON.fromJson(tArr,
                (java.lang.reflect.Type) java.util.List.class);
            Map<String, Object> policy = null;
            if (policyPath != null) {
                var pRoot = GSON.fromJson(new java.io.FileReader(policyPath),
                                          com.google.gson.JsonObject.class);
                policy = GSON.fromJson(pRoot, Map.class);
            }
            List<String> holidays = null;
            if (holidaysPath != null) {
                var hArr = GSON.fromJson(new java.io.FileReader(holidaysPath),
                                         com.google.gson.JsonArray.class);
                holidays = GSON.fromJson(hArr,
                    (java.lang.reflect.Type) java.util.List.class);
            }
            // Filter holidays to only strings
            if (holidays != null)
                holidays = holidays.stream().filter(o -> o instanceof String)
                    .map(o -> (String) o).toList();
            return new RawInput(tickets, policy, holidays);
        } catch (java.io.FileNotFoundException e) {
            throw new RuntimeException("Input file not found: " + e.getMessage(), e);
        }
    }

    public static void writeResults(String path, List<SlaCalculator.TicketResult> results,
                                     String summaryText) {
        var out = new JsonObject();

        var arr = new JsonArray();
        for (var r : results) {
            var obj = new JsonObject();
            obj.addProperty("ticket_id", r.ticketId());
            obj.addProperty("priority", r.priority());
            obj.addProperty("assignee_group", r.group());
            obj.addProperty("current_status", r.status());
            obj.addProperty("elapsed_business_minutes", r.elapsedMinutes());
            obj.addProperty("sla_target_minutes", r.slaTargetMinutes());
            obj.addProperty("due_by", r.dueBy()
                .withZoneSameInstant(ZoneOffset.UTC)
                .format(DateTimeFormatter.ISO_OFFSET_DATE_TIME));
            obj.addProperty("breached", r.breached());
            obj.addProperty("breach_minutes", r.breachMinutes());
            arr.add(obj);
        }
        out.add("results", arr);

        var summary = new JsonObject();
        summary.addProperty("text", summaryText);
        summary.addProperty("evaluated_at",
            ZonedDateTime.now(ZoneOffset.UTC)
                .format(DateTimeFormatter.ISO_OFFSET_DATE_TIME));
        out.add("summary", summary);

        try (var w = new java.io.FileWriter(path)) {
            GSON.toJson(out, w);
        } catch (java.io.IOException e) {
            throw new RuntimeException("Failed to write output: " + e.getMessage(), e);
        }
    }
}