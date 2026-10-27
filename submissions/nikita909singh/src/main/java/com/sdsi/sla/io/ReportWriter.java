package com.sdsi.sla.io;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.sdsi.sla.model.Summary;
import com.sdsi.sla.model.TicketResult;

import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Renders results as a text table, JSON or CSV. */
public final class ReportWriter {

    private static final DateTimeFormatter SHORT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm");
    private static final ObjectMapper JSON = new ObjectMapper().enable(SerializationFeature.INDENT_OUTPUT);

    private ReportWriter() {
    }

    public static String text(ZonedDateTime asOf, List<TicketResult> results, Summary summary,
                              List<InputLoader.Rejected> skipped) {
        StringBuilder sb = new StringBuilder();
        sb.append("SLA report as of ").append(asOf.format(SHORT)).append(" ").append(asOf.getZone())
                .append(": ").append(results.size()).append(" ticket(s)\n");

        if (!skipped.isEmpty()) {
            sb.append("\nSKIPPED (invalid)\n");
            for (InputLoader.Rejected r : skipped) {
                sb.append("  #").append(r.index() + 1).append(r.id() == null ? "" : " " + r.id()).append(": ")
                        .append(String.join("; ", r.errors())).append("\n");
            }
        }

        sb.append("\nTICKETS (minutes are business minutes)\n");
        int idW = Math.max(6, results.stream().mapToInt(r -> r.id().length()).max().orElse(6));
        int grpW = Math.max(5, results.stream().mapToInt(r -> r.assigneeGroup().length()).max().orElse(5));
        String fmt = "  %-" + idW + "s %-4s %-" + grpW + "s %-11s %7s %8s  %-16s %-6s %7s  %s\n";
        sb.append(String.format(fmt, "Ticket", "Pri", "Group", "Status", "Target", "Elapsed", "Due by", "Breach",
                "Over", "State"));
        for (TicketResult r : results) {
            sb.append(String.format(fmt, r.id(), r.priority(), r.assigneeGroup(), r.currentStatus(),
                    r.targetMinutes(), r.elapsedMinutes(),
                    r.dueBy() == null ? "(paused)" : r.dueBy().format(SHORT),
                    r.breached() ? "YES" : "no", r.breachMinutes(), r.state()));
        }

        sb.append("\nBREACH % BY PRIORITY\n");
        summary.byPriority().forEach(b -> sb.append(bucketLine(b)));
        sb.append("\nBREACH % BY ASSIGNEE GROUP\n");
        summary.byAssigneeGroup().forEach(b -> sb.append(bucketLine(b)));
        sb.append("\nOVERALL\n").append(bucketLine(summary.overall()));
        return sb.toString();
    }

    private static String bucketLine(Summary.Bucket b) {
        return String.format("  %-20s %3d ticket(s), %3d breached, %3d open   %6.2f%% breached\n",
                b.key(), b.total(), b.breached(), b.open(), b.breachPercent());
    }

    public static String json(ZonedDateTime asOf, List<TicketResult> results, Summary summary,
                              List<InputLoader.Rejected> skipped) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("asOf", asOf.toOffsetDateTime().toString());
        out.put("timezone", asOf.getZone().getId());
        List<Map<String, Object>> rows = new ArrayList<>();
        for (TicketResult r : results) {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("id", r.id());
            m.put("priority", r.priority());
            m.put("assigneeGroup", r.assigneeGroup());
            m.put("status", r.currentStatus());
            m.put("resolved", r.resolved());
            m.put("targetMinutes", r.targetMinutes());
            m.put("elapsedBusinessMinutes", r.elapsedMinutes());
            m.put("dueBy", r.dueBy() == null ? null : r.dueBy().toOffsetDateTime().toString());
            m.put("breached", r.breached());
            m.put("breachMinutes", r.breachMinutes());
            m.put("state", r.state().name());
            rows.add(m);
        }
        out.put("tickets", rows);
        out.put("summary", summary);
        out.put("skipped", skipped);
        try {
            return JSON.writeValueAsString(out);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException(e);
        }
    }

    public static String csv(List<TicketResult> results) {
        StringBuilder sb = new StringBuilder(
                "id,priority,assigneeGroup,status,targetMinutes,elapsedBusinessMinutes,dueBy,breached,breachMinutes,state\n");
        for (TicketResult r : results) {
            sb.append(String.join(",",
                    csvCell(r.id()), csvCell(r.priority()), csvCell(r.assigneeGroup()), csvCell(r.currentStatus()),
                    Long.toString(r.targetMinutes()), Long.toString(r.elapsedMinutes()),
                    r.dueBy() == null ? "" : r.dueBy().toOffsetDateTime().toString(),
                    Boolean.toString(r.breached()), Long.toString(r.breachMinutes()), r.state().name()))
                    .append("\n");
        }
        return sb.toString();
    }

    /**
     * Quotes a CSV cell and defuses spreadsheet formulas: a cell starting with = + - @ would run as a
     * formula when the CSV is opened in Excel ("CSV injection"), so it gets a leading apostrophe.
     */
    static String csvCell(String v) {
        String s = v == null ? "" : v;
        if (!s.isEmpty() && "=+-@\t\r".indexOf(s.charAt(0)) >= 0) {
            s = "'" + s;
        }
        if (s.contains(",") || s.contains("\"") || s.contains("\n") || s.contains("\r") || s.startsWith("'")) {
            s = "\"" + s.replace("\"", "\"\"") + "\"";
        }
        return s;
    }
}
