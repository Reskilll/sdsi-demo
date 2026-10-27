package com.sdsi.splitsmart.service;

import com.sdsi.splitsmart.dto.ExpenseRequest;
import com.sdsi.splitsmart.dto.GroupSnapshot;
import com.sdsi.splitsmart.model.*;
import com.sdsi.splitsmart.validator.ExpenseValidator;
import org.springframework.stereotype.Service;

import java.util.*;

/**
 * Core engine — everything is in-memory; stateless across requests.
 */
@Service
public class SplitService {

    /** All expenses ever recorded this session. */
    private final List<Expense> expenses = new ArrayList<>();

    /**
     * Record one expense.  Validates business rules first (M5), then computes.
     */
    public GroupSnapshot addExpense(ExpenseRequest req) {
        ExpenseValidator.validate(req);

        Expense expense = buildExpense(req);
        expenses.add(expense);
        return computeSnapshot();
    }

    /**
     * Process a batch of expenses (M4).
     */
    public GroupSnapshot addBatch(List<ExpenseRequest> reqs) {
        for (ExpenseRequest req : reqs) {
            ExpenseValidator.validate(req);
            Expense expense = buildExpense(req);
            expenses.add(expense);
        }
        return computeSnapshot();
    }

    /**
     * Return current balances and simplified settlements without adding.
     */
    public GroupSnapshot getSnapshot() {
        return computeSnapshot();
    }

    /** Reset all data. */
    public GroupSnapshot reset() {
        expenses.clear();
        return computeSnapshot();
    }

    private Expense buildExpense(ExpenseRequest req) {
        return switch (req.splitType()) {
            case EQUAL -> new Expense(
                    req.payer(), req.amount(), SplitType.EQUAL,
                    List.copyOf(req.members()), Map.of());
            case EXACT, PERCENTAGE -> new Expense(
                    req.payer(), req.amount(), req.splitType(),
                    List.copyOf(req.members()), new HashMap<>(req.shares()));
        };
    }

    // ─── M2: Net balances ──────────────────────────────────────────────────

    private Map<String, Double> computeNetBalances() {
        Map<String, Double> net = new HashMap<>();
        for (Expense e : expenses) {
            net.putIfAbsent(e.payer(), 0.0);

            Map<String, Double> owed = resolveOwedPerMember(e);

            for (var entry : owed.entrySet()) {
                String member = entry.getKey();
                double owes = entry.getValue();
                net.putIfAbsent(member, 0.0);
                net.merge(member, owes, Double::sum);
            }
            // payer is credited for what others owe
            double totalOwed = owed.values().stream().mapToDouble(Double::doubleValue).sum();
            net.merge(e.payer(), -totalOwed, Double::sum);
        }
        return net;
    }

    /** How much each member (other than payer) owes for this expense. */
    private Map<String, Double> resolveOwedPerMember(Expense e) {
        return switch (e.splitType()) {
            case EQUAL -> {
                double each = e.amount() / e.members().size();
                Map<String, Double> m = new HashMap<>();
                for (String member : e.members()) m.put(member, each);
                yield m;
            }
            case EXACT -> new HashMap<>(e.shares());
            case PERCENTAGE -> {
                Map<String, Double> m = new HashMap<>();
                for (var entry : e.shares().entrySet()) {
                    m.put(entry.getKey(), e.amount() * entry.getValue() / 100.0);
                }
                yield m;
            }
        };
    }

    // ─── M3: Debt simplification ───────────────────────────────────────────

    /**
     * Greedy settlement: match biggest creditor with biggest debtor until
     * everyone is within rounding tolerance. This produces near-minimal
     * transactions.
     */
    private List<Settlement> simplifyDebts(Map<String, Double> net) {
        // Separate creditors (owed money → negative net) and debtors (owe → positive)
        record Person(String name, double balance) {}

        List<Person> creditors = new ArrayList<>();
        List<Person> debtors = new ArrayList<>();

        for (var entry : net.entrySet()) {
            double bal = Math.round(entry.getValue() * 100.0) / 100.0;
            if (bal > 0.001)      debtors.add(new Person(entry.getKey(), bal));
            else if (bal < -0.001) creditors.add(new Person(entry.getKey(), -bal));
        }

        creditors.sort((a, b) -> Double.compare(b.balance, a.balance));
        debtors.sort((a, b) -> Double.compare(b.balance, a.balance));

        List<Settlement> settlements = new ArrayList<>();
        int ci = 0, di = 0;

        while (ci < creditors.size() && di < debtors.size()) {
            Person creditor = creditors.get(ci);
            Person debtor    = debtors.get(di);
            double amount = Math.min(creditor.balance, debtor.balance);
            amount = Math.round(amount * 100.0) / 100.0;

            if (amount > 0.001) {
                settlements.add(new Settlement(debtor.name, creditor.name, amount));
            }

            double newCred = creditor.balance - amount;
            double newDebt = debtor.balance - amount;

            if (Math.abs(newCred) < 0.001) ci++; else creditors.set(ci, new Person(creditor.name, newCred));
            if (Math.abs(newDebt) < 0.001) di++; else debtors.set(di, new Person(debtor.name, newDebt));
        }

        return settlements;
    }

    // ─── Snapshot ──────────────────────────────────────────────────────────

    private GroupSnapshot computeSnapshot() {
        Map<String, Double> net = computeNetBalances();
        List<Balance> balances = new ArrayList<>();
        for (var entry : net.entrySet()) {
            double b = Math.round(entry.getValue() * 100.0) / 100.0;
            balances.add(new Balance(entry.getKey(), b));
        }
        balances.sort(Comparator.comparing(Balance::member));

        List<Settlement> settlements = simplifyDebts(net);
        return new GroupSnapshot(balances, settlements);
    }
}