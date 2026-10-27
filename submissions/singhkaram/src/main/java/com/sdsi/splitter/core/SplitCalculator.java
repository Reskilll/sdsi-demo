package com.sdsi.splitter.core;

import com.sdsi.splitter.model.Expense;
import com.sdsi.splitter.model.ExpenseRequest;
import com.sdsi.splitter.model.Money;
import com.sdsi.splitter.model.SplitType;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Validates an {@link ExpenseRequest} against the group (M5) and turns it into per-person shares in
 * paise (M1).
 *
 * <p>Rounding rule: shares always add up to the exact total. Leftover paise go one each to the people
 * with the largest rounded-off fraction, ties broken by the order the participants were listed, so the
 * same input always gives the same output. Example: ₹100 split 3 ways is 33.34 / 33.33 / 33.33.
 */
final class SplitCalculator {

    private static final BigDecimal HUNDRED = BigDecimal.valueOf(100);
    private static final int MAX_PERCENT_DECIMALS = 4;
    private static final int MAX_DESCRIPTION = 200;

    private SplitCalculator() {
    }

    static Expense compute(ExpenseRequest req, List<String> members, String id) {
        List<String> errors = new ArrayList<>();
        Set<String> memberSet = Set.copyOf(members);

        String description = req.description() == null || req.description().isBlank()
                ? "Expense " + id : req.description().strip();
        if (description.length() > MAX_DESCRIPTION) {
            errors.add("description must be at most " + MAX_DESCRIPTION + " characters");
        }

        if (req.paidBy() == null || req.paidBy().isBlank()) {
            errors.add("paidBy is required");
        } else if (!memberSet.contains(req.paidBy())) {
            errors.add("payer '" + req.paidBy() + "' is not a member of the group");
        }

        long amount = 0;
        if (req.amount() == null) {
            errors.add("amount is required");
        } else {
            String problem = checkRupees(req.amount(), false);
            if (problem != null) {
                errors.add("amount " + problem);
            } else {
                amount = Money.toPaise(req.amount());
            }
        }

        if (req.split() == null) {
            errors.add("split must be one of: equal, exact, percentage");
            throw new ValidationException(errors);
        }

        Map<String, Long> shares = switch (req.split()) {
            case EQUAL -> equal(req, members, memberSet, amount, errors);
            case EXACT -> exact(req, memberSet, amount, errors);
            case PERCENTAGE -> percentage(req, memberSet, amount, errors);
        };
        if (!errors.isEmpty()) {
            throw new ValidationException(errors);
        }
        return new Expense(id, description, req.paidBy(), amount, req.split(), shares);
    }

    private static Map<String, Long> equal(ExpenseRequest req, List<String> members, Set<String> memberSet,
                                           long amount, List<String> errors) {
        if (req.shares() != null) {
            errors.add("an equal split takes 'participants', not 'shares'");
        }
        List<String> people = req.participants() == null ? members : req.participants();
        if (people.isEmpty()) {
            errors.add("participants must not be empty");
            return Map.of();
        }
        checkPeople(people, memberSet, errors);
        if (!errors.isEmpty()) {
            return Map.of();
        }
        long base = amount / people.size();
        long remainder = amount % people.size();
        Map<String, Long> shares = new LinkedHashMap<>();
        for (int i = 0; i < people.size(); i++) {
            shares.put(people.get(i), base + (i < remainder ? 1 : 0));
        }
        return shares;
    }

    private static Map<String, Long> exact(ExpenseRequest req, Set<String> memberSet, long amount,
                                           List<String> errors) {
        Map<String, BigDecimal> input = requireShares(req, memberSet, errors);
        Map<String, Long> shares = new LinkedHashMap<>();
        long sum = 0;
        boolean valuesOk = true;
        for (Map.Entry<String, BigDecimal> e : input.entrySet()) {
            String problem = e.getValue() == null ? "is required" : checkRupees(e.getValue(), true);
            if (problem != null) {
                errors.add("share for '" + e.getKey() + "' " + problem);
                valuesOk = false;
                continue;
            }
            long paise = Money.toPaise(e.getValue());
            shares.put(e.getKey(), paise);
            sum += paise;
        }
        // Checked even when other errors exist, so the user sees every problem in one go.
        if (valuesOk && amount > 0 && sum != amount) {
            errors.add("exact shares add up to " + Money.format(sum) + " but the amount is " + Money.format(amount));
        }
        return shares;
    }

    private static Map<String, Long> percentage(ExpenseRequest req, Set<String> memberSet, long amount,
                                                List<String> errors) {
        Map<String, BigDecimal> input = requireShares(req, memberSet, errors);
        BigDecimal total = BigDecimal.ZERO;
        boolean valuesOk = true;
        for (Map.Entry<String, BigDecimal> e : input.entrySet()) {
            BigDecimal pct = e.getValue();
            if (pct == null || pct.signum() < 0 || pct.compareTo(HUNDRED) > 0) {
                errors.add("percentage for '" + e.getKey() + "' must be between 0 and 100");
                valuesOk = false;
            } else if (pct.stripTrailingZeros().scale() > MAX_PERCENT_DECIMALS) {
                errors.add("percentage for '" + e.getKey() + "' has more than " + MAX_PERCENT_DECIMALS + " decimals");
                valuesOk = false;
            } else {
                total = total.add(pct);
            }
        }
        if (valuesOk && !input.isEmpty() && total.compareTo(HUNDRED) != 0) {
            errors.add("percentages add up to " + total.stripTrailingZeros().toPlainString() + ", not 100");
        }
        if (!errors.isEmpty()) {
            return Map.of();
        }

        // Largest-remainder method: floor every share, then hand out the missing paise.
        List<String> people = new ArrayList<>(input.keySet());
        Map<String, Long> shares = new LinkedHashMap<>();
        Map<String, BigDecimal> fractions = new LinkedHashMap<>();
        long allocated = 0;
        for (String p : people) {
            BigDecimal exactShare = BigDecimal.valueOf(amount).multiply(input.get(p)).divide(HUNDRED);
            long floor = exactShare.setScale(0, RoundingMode.FLOOR).longValueExact();
            shares.put(p, floor);
            fractions.put(p, exactShare.subtract(BigDecimal.valueOf(floor)));
            allocated += floor;
        }
        List<String> byFraction = new ArrayList<>(people);
        // List.sort is stable, so equal fractions keep input order.
        byFraction.sort(Comparator.comparing(fractions::get).reversed());
        for (int i = 0; i < amount - allocated; i++) {
            shares.merge(byFraction.get(i), 1L, Long::sum);
        }
        return shares;
    }

    private static Map<String, BigDecimal> requireShares(ExpenseRequest req, Set<String> memberSet, List<String> errors) {
        if (req.participants() != null) {
            errors.add("an " + req.split().name().toLowerCase() + " split takes 'shares', not 'participants'");
        }
        if (req.shares() == null || req.shares().isEmpty()) {
            errors.add("shares must list at least one member");
            return Map.of();
        }
        checkPeople(new ArrayList<>(req.shares().keySet()), memberSet, errors);
        return req.shares();
    }

    private static void checkPeople(List<String> people, Set<String> memberSet, List<String> errors) {
        Set<String> seen = new HashSet<>();
        for (String p : people) {
            if (p == null || !memberSet.contains(p)) {
                errors.add("'" + p + "' is not a member of the group");
            } else if (!seen.add(p)) {
                errors.add("'" + p + "' is listed more than once");
            }
        }
    }

    /** Returns a problem description, or null when the value is a valid rupee amount. */
    private static String checkRupees(BigDecimal v, boolean allowZero) {
        if (v.signum() < 0 || (!allowZero && v.signum() == 0)) {
            return allowZero ? "must not be negative" : "must be greater than 0";
        }
        if (v.stripTrailingZeros().scale() > 2) {
            return "must have at most 2 decimal places";
        }
        if (v.compareTo(Money.toRupees(Money.MAX_PAISE)) > 0) {
            return "must not exceed " + Money.format(Money.MAX_PAISE);
        }
        return null;
    }
}
