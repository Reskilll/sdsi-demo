package in.sam.com.expense_splitter;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.*;

public class ExpenseService {
    private static final BigDecimal ZERO = new BigDecimal("0.00");
    private static final BigDecimal HUNDRED = new BigDecimal("100");

    private final Set<String> members;
    private final Map<String, BigDecimal> paid = new LinkedHashMap<>();
    private final Map<String, BigDecimal> owed = new LinkedHashMap<>();

    public ExpenseService(Collection<String> groupMembers) {
        if (groupMembers == null || groupMembers.isEmpty()) {
            throw new IllegalArgumentException(
                "Group must contain at least one member");
        }

        members = new LinkedHashSet<>();
        for (String member : groupMembers) {
            if (member == null || member.isBlank()) {
                throw new IllegalArgumentException(
                    "Member names cannot be blank");
            }
            if (!members.add(member)) {
                throw new IllegalArgumentException(
                    "Duplicate group member: " + member);
            }
        }

        members.forEach(member -> {
            paid.put(member, ZERO);
            owed.put(member, ZERO);
        });
    }

    public void process(Expense expense) {
        validate(expense);

        Map<String, BigDecimal> shares = calculateShares(expense);

        paid.put(expense.getPayer(),
            paid.get(expense.getPayer()).add(expense.getAmount()));

        shares.forEach((member, share) ->
            owed.put(member, owed.get(member).add(share)));
    }

    public void validate(Expense expense) {
        if (expense == null) {
            throw new IllegalArgumentException("Expense cannot be null");
        }
        if (expense.getDescription() == null
                || expense.getDescription().isBlank()) {
            throw new IllegalArgumentException(
                "Expense description is required");
        }
        if (expense.getAmount() == null
                || expense.getAmount().signum() <= 0
                || expense.getAmount().scale() > 2) {
            throw new IllegalArgumentException(
                "Amount must be positive and have at most 2 decimal places");
        }
        if (!members.contains(expense.getPayer())) {
            throw new IllegalArgumentException(
                "Payer is not a group member: " + expense.getPayer());
        }
        if (expense.getSplitType() == null) {
            throw new IllegalArgumentException("Split type is required");
        }
        if (expense.getSplits() == null
                || expense.getSplits().isEmpty()) {
            throw new IllegalArgumentException(
                "At least one split participant is required");
        }

        Set<String> participants = new HashSet<>();
        for (Split split : expense.getSplits()) {
            if (split == null || split.getMember() == null
                    || !members.contains(split.getMember())) {
                throw new IllegalArgumentException(
                    "Every split participant must be a group member");
            }
            if (!participants.add(split.getMember())) {
                throw new IllegalArgumentException(
                    "Duplicate split participant: " + split.getMember());
            }
        }

        String type = expense.getSplitType()
            .trim().toUpperCase(Locale.ROOT);

        switch (type) {
            case "EQUAL" -> {
                // Values are ignored for equal splits.
            }
            case "EXACT" -> {
                BigDecimal total = ZERO;
                for (Split split : expense.getSplits()) {
                    BigDecimal value = split.getValue();
                    if (value == null || value.signum() < 0
                            || value.scale() > 2) {
                        throw new IllegalArgumentException(
                            "Exact shares must be non-negative amounts "
                            + "with at most 2 decimal places");
                    }
                    total = total.add(value);
                }
                if (total.compareTo(expense.getAmount()) != 0) {
                    throw new IllegalArgumentException(
                        "Exact shares must sum to expense amount");
                }
            }
            case "PERCENTAGE" -> {
                BigDecimal total = ZERO;
                for (Split split : expense.getSplits()) {
                    BigDecimal value = split.getValue();
                    if (value == null || value.signum() < 0
                            || value.compareTo(HUNDRED) > 0
                            || value.scale() > 2) {
                        throw new IllegalArgumentException(
                            "Percentages must be between 0 and 100 "
                            + "with at most 2 decimal places");
                    }
                    total = total.add(value);
                }
                if (total.compareTo(HUNDRED) != 0) {
                    throw new IllegalArgumentException(
                        "Percentages must sum to 100");
                }
            }
            default -> throw new IllegalArgumentException(
                "Unsupported split type: " + expense.getSplitType());
        }
    }

    private Map<String, BigDecimal> calculateShares(Expense expense) {
        List<Split> splits = expense.getSplits();
        Map<String, BigDecimal> shares = new LinkedHashMap<>();
        String type = expense.getSplitType()
            .trim().toUpperCase(Locale.ROOT);

        BigDecimal allocated = ZERO;

        for (int i = 0; i < splits.size(); i++) {
            Split split = splits.get(i);
            BigDecimal share;

            if (i == splits.size() - 1) {
                // Assign the remaining cents to the final participant.
                share = expense.getAmount().subtract(allocated);
            } else {
                switch (type) {
                    case "EQUAL" -> share = expense.getAmount()
                        .divide(BigDecimal.valueOf(splits.size()),
                            2, RoundingMode.DOWN);
                    case "EXACT" -> share = split.getValue()
                        .setScale(2, RoundingMode.UNNECESSARY);
                    case "PERCENTAGE" -> share = expense.getAmount()
                        .multiply(split.getValue())
                        .divide(HUNDRED, 2, RoundingMode.DOWN);
                    default -> throw new IllegalStateException(
                        "Unexpected split type");
                }
            }

            shares.put(split.getMember(), share);
            allocated = allocated.add(share);
        }

        return shares;
    }

    public Map<String, BigDecimal> getNetBalances() {
        Map<String, BigDecimal> result = new LinkedHashMap<>();
        for (String member : members) {
            result.put(member, paid.get(member)
                .subtract(owed.get(member))
                .setScale(2, RoundingMode.UNNECESSARY));
        }
        return Collections.unmodifiableMap(result);
    }

    public Map<String, BigDecimal> getTotalPaid() {
        return Collections.unmodifiableMap(new LinkedHashMap<>(paid));
    }

    public Map<String, BigDecimal> getTotalOwed() {
        return Collections.unmodifiableMap(new LinkedHashMap<>(owed));
    }

    public Set<String> getMembers() {
        return Collections.unmodifiableSet(members);
    }
}