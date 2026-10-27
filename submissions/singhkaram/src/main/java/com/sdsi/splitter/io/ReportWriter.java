package com.sdsi.splitter.io;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.sdsi.splitter.core.Group;
import com.sdsi.splitter.model.Expense;
import com.sdsi.splitter.model.MemberBalance;
import com.sdsi.splitter.model.Money;
import com.sdsi.splitter.model.Settlement;
import com.sdsi.splitter.model.SettlementPlan;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/** Renders a group as a human-readable report or as JSON. */
public final class ReportWriter {

    private final String currency;

    /** @param ascii use "Rs." instead of "₹" for consoles that can't show the rupee sign */
    public ReportWriter(boolean ascii) {
        this.currency = ascii ? "Rs." : "₹";
    }

    public String text(Group group, List<ExpenseFile.Rejected> skipped) {
        List<Expense> expenses = group.expenses();
        long total = expenses.stream().mapToLong(Expense::amountPaise).sum();
        StringBuilder sb = new StringBuilder();
        sb.append(group.name()).append(": ").append(group.members().size()).append(" members, ")
                .append(expenses.size()).append(" expense(s), total ").append(money(total)).append("\n");

        if (!skipped.isEmpty()) {
            sb.append("\nSKIPPED (invalid)\n");
            for (ExpenseFile.Rejected r : skipped) {
                sb.append("  #").append(r.index() + 1)
                        .append(r.description() == null ? "" : " " + r.description()).append(": ")
                        .append(String.join("; ", r.errors())).append("\n");
            }
        }

        sb.append("\nEXPENSES\n");
        if (expenses.isEmpty()) {
            sb.append("  (none)\n");
        }
        int descWidth = Math.min(24, Math.max(11, expenses.stream().mapToInt(e -> e.description().length()).max().orElse(0)));
        for (Expense e : expenses) {
            sb.append(String.format("  %-5s %-" + descWidth + "s %14s paid by %-12s %-10s ",
                    e.id(), truncate(e.description(), descWidth), money(e.amountPaise()), e.paidBy(),
                    e.split().name().toLowerCase()));
            sb.append(e.shares().entrySet().stream()
                    .map(s -> s.getKey() + " " + Money.format(s.getValue()))
                    .collect(Collectors.joining(", "))).append("\n");
        }

        sb.append("\nBALANCES\n");
        int nameWidth = Math.max(6, group.members().stream().mapToInt(String::length).max().orElse(6));
        sb.append(String.format("  %-" + nameWidth + "s %15s %15s %16s%n", "Member", "Paid", "Share", "Net"));
        for (MemberBalance b : group.balances()) {
            String status = b.net() > 0 ? "gets back" : b.net() < 0 ? "owes" : "settled";
            sb.append(String.format("  %-" + nameWidth + "s %15s %15s %16s  %s%n", b.member(),
                    Money.format(b.paid()), Money.format(b.share()),
                    (b.net() > 0 ? "+" : "") + Money.format(b.net()), status));
        }

        SettlementPlan plan = group.settleUp();
        sb.append("\nSETTLEMENTS: ").append(plan.settlements().size()).append(" transfer(s)")
                .append(plan.optimal() ? ", proven minimum" : ", near-minimum (greedy, large group)").append("\n");
        if (plan.settlements().isEmpty()) {
            sb.append("  Everyone is settled up.\n");
        }
        for (Settlement s : plan.settlements()) {
            sb.append("  ").append(s.from()).append(" pays ").append(s.to()).append(" ")
                    .append(money(s.amountPaise())).append("\n");
        }
        return sb.toString();
    }

    public String json(Group group, List<ExpenseFile.Rejected> skipped) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("group", group.name());
        out.put("members", group.members());
        List<Map<String, Object>> expenses = new ArrayList<>();
        for (Expense e : group.expenses()) {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("id", e.id());
            m.put("description", e.description());
            m.put("paidBy", e.paidBy());
            m.put("amount", Money.toRupees(e.amountPaise()));
            m.put("split", e.split().name().toLowerCase());
            Map<String, Object> shares = new LinkedHashMap<>();
            e.shares().forEach((k, v) -> shares.put(k, Money.toRupees(v)));
            m.put("shares", shares);
            expenses.add(m);
        }
        out.put("expenses", expenses);
        List<Map<String, Object>> balances = new ArrayList<>();
        for (MemberBalance b : group.balances()) {
            balances.add(Map.of("member", b.member(), "paid", Money.toRupees(b.paid()),
                    "share", Money.toRupees(b.share()), "net", Money.toRupees(b.net())));
        }
        out.put("balances", balances);
        SettlementPlan plan = group.settleUp();
        out.put("settlements", plan.settlements().stream()
                .map(s -> Map.of("from", s.from(), "to", s.to(), "amount", Money.toRupees(s.amountPaise())))
                .toList());
        out.put("settlementsProvenMinimal", plan.optimal());
        out.put("skipped", skipped);
        try {
            return ExpenseFile.mapper().writeValueAsString(out);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException(e);
        }
    }

    private String money(long paise) {
        return currency + Money.format(paise);
    }

    private static String truncate(String s, int width) {
        return s.length() <= width ? s : s.substring(0, width - 1) + "…";
    }
}
