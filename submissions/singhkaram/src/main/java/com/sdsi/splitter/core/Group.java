package com.sdsi.splitter.core;

import com.sdsi.splitter.model.Expense;
import com.sdsi.splitter.model.ExpenseRequest;
import com.sdsi.splitter.model.MemberBalance;
import com.sdsi.splitter.model.SettlementPlan;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.regex.Pattern;

/**
 * A group of people sharing expenses. Members are fixed when the group is created; expenses are
 * validated as they are added, and an invalid expense leaves the group unchanged.
 */
public final class Group {

    public static final int MAX_MEMBERS = 500;
    public static final int MAX_EXPENSES = 100_000;
    /**
     * Letters in any script (plus combining marks, which Devanagari and other Indic scripts need for vowel
     * signs), digits, space and . _ ' -; 1-40 characters.
     */
    private static final Pattern NAME = Pattern.compile("[\\p{L}\\p{M}\\p{N} ._'-]{1,40}");
    private static final Pattern ID = Pattern.compile("[A-Za-z0-9_.-]{1,40}");

    private final String name;
    private final List<String> members;
    /** lower-cased name -> member's own spelling, for case-insensitive lookups. */
    private final Map<String, String> byFoldedName;
    private final List<Expense> expenses = new ArrayList<>();
    private final Set<String> ids = new HashSet<>();

    public Group(String name, List<String> members) {
        List<String> errors = new ArrayList<>();
        this.name = name == null || name.isBlank() ? "Group" : name.strip();
        if (this.name.length() > 100) {
            errors.add("group name must be at most 100 characters");
        }
        if (members == null || members.isEmpty()) {
            throw new ValidationException("the group needs at least one member");
        }
        if (members.size() > MAX_MEMBERS) {
            throw new ValidationException("a group can have at most " + MAX_MEMBERS + " members");
        }
        Set<String> folded = new HashSet<>();
        List<String> clean = new ArrayList<>();
        for (String m : members) {
            String s = m == null ? "" : m.strip();
            if (!NAME.matcher(s).matches()) {
                errors.add("member name '" + m + "' must be 1-40 letters, digits, spaces or . _ ' -");
            } else if (!folded.add(s.toLowerCase(Locale.ROOT))) {
                // "Asha" and "asha" in one group is almost certainly a typo, and would confuse everyone.
                errors.add("member '" + s + "' is listed more than once (names are case-insensitive)");
            } else {
                clean.add(s);
            }
        }
        if (!errors.isEmpty()) {
            throw new ValidationException(errors);
        }
        this.members = List.copyOf(clean);
        Map<String, String> index = new LinkedHashMap<>();
        clean.forEach(m -> index.put(m.toLowerCase(Locale.ROOT), m));
        this.byFoldedName = Map.copyOf(index);
    }

    public String name() {
        return name;
    }

    public List<String> members() {
        return members;
    }

    public List<Expense> expenses() {
        return List.copyOf(expenses);
    }

    /** Validates and records an expense (M1, M5). Throws {@link ValidationException} listing every problem. */
    public Expense add(ExpenseRequest request) {
        if (expenses.size() >= MAX_EXPENSES) {
            throw new ValidationException("a group can have at most " + MAX_EXPENSES + " expenses");
        }
        String id = request.id();
        if (id == null) {
            int n = expenses.size() + 1;
            do {
                id = "e" + n++;
            } while (ids.contains(id));
        } else if (!ID.matcher(id).matches()) {
            throw new ValidationException("id must be 1-40 chars of [A-Za-z0-9_.-]");
        } else if (ids.contains(id)) {
            throw new ValidationException("id '" + id + "' is already used by another expense");
        }
        Expense expense = SplitCalculator.compute(canonicalNames(request), members, id);
        expenses.add(expense);
        ids.add(id);
        return expense;
    }

    /**
     * Maps names to the member's canonical spelling ("asha " -> "Asha"). Names that match no member are
     * left as they are, so the validator can report them.
     */
    private ExpenseRequest canonicalNames(ExpenseRequest r) {
        List<String> participants = null;
        if (r.participants() != null) {
            participants = new ArrayList<>();
            for (String p : r.participants()) {
                participants.add(canonical(p));
            }
        }
        Map<String, BigDecimal> shares = null;
        if (r.shares() != null) {
            shares = new LinkedHashMap<>();
            for (Map.Entry<String, BigDecimal> e : r.shares().entrySet()) {
                String key = canonical(e.getKey());
                if (shares.containsKey(key)) {
                    throw new ValidationException("'" + key + "' is listed more than once in shares");
                }
                shares.put(key, e.getValue());
            }
        }
        return new ExpenseRequest(r.id(), r.description(), canonical(r.paidBy()), r.amount(), r.split(),
                participants, shares);
    }

    private String canonical(String raw) {
        if (raw == null) {
            return null;
        }
        String s = raw.strip();
        return byFoldedName.getOrDefault(s.toLowerCase(Locale.ROOT), s);
    }

    /** Each member's paid, share and net (M2), in member order. Nets always sum to zero. */
    public List<MemberBalance> balances() {
        Map<String, long[]> acc = new LinkedHashMap<>();
        members.forEach(m -> acc.put(m, new long[2]));
        for (Expense e : expenses) {
            acc.get(e.paidBy())[0] += e.amountPaise();
            e.shares().forEach((member, share) -> acc.get(member)[1] += share);
        }
        List<MemberBalance> out = new ArrayList<>();
        acc.forEach((m, v) -> out.add(new MemberBalance(m, v[0], v[1], v[0] - v[1])));
        return out;
    }

    /** The fewest transfers that settle everyone (M3). */
    public SettlementPlan settleUp() {
        Map<String, Long> nets = new LinkedHashMap<>();
        balances().forEach(b -> nets.put(b.member(), b.net()));
        return DebtSimplifier.simplify(nets);
    }
}
