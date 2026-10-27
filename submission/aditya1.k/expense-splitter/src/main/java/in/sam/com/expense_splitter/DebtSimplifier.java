package in.sam.com.expense_splitter;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.*;

public class DebtSimplifier {
    private static final BigDecimal ZERO = new BigDecimal("0.00");

    public record Settlement(
            String from,
            String to,
            BigDecimal amount
    ) {}

    private static class Account {
        String member;
        BigDecimal balance;

        Account(String member, BigDecimal balance) {
            this.member = member;
            this.balance = balance;
        }
    }

    public List<Settlement> simplify(
            Map<String, BigDecimal> netBalances) {

        List<Account> debtors = new ArrayList<>();
        List<Account> creditors = new ArrayList<>();

        netBalances.forEach((member, balance) -> {
            BigDecimal rounded = balance.setScale(
                    2, RoundingMode.HALF_UP);

            if (rounded.compareTo(ZERO) < 0) {
                debtors.add(new Account(member, rounded.negate()));
            } else if (rounded.compareTo(ZERO) > 0) {
                creditors.add(new Account(member, rounded));
            }
        });

        // Process larger balances first for a practical greedy result.
        debtors.sort((a, b) ->
                b.balance.compareTo(a.balance));
        creditors.sort((a, b) ->
                b.balance.compareTo(a.balance));

        List<Settlement> settlements = new ArrayList<>();
        int i = 0;
        int j = 0;

        while (i < debtors.size() && j < creditors.size()) {
            Account debtor = debtors.get(i);
            Account creditor = creditors.get(j);

            BigDecimal amount = debtor.balance.min(creditor.balance)
                    .setScale(2, RoundingMode.UNNECESSARY);

            if (amount.compareTo(ZERO) > 0) {
                settlements.add(new Settlement(
                        debtor.member, creditor.member, amount));
            }

            debtor.balance = debtor.balance.subtract(amount);
            creditor.balance = creditor.balance.subtract(amount);

            if (debtor.balance.compareTo(ZERO) == 0) {
                i++;
            }
            if (creditor.balance.compareTo(ZERO) == 0) {
                j++;
            }
        }

        if (i != debtors.size() || j != creditors.size()) {
            throw new IllegalArgumentException(
                    "Net balances do not sum to zero; "
                            + "check the expense ledger");
        }

        return settlements;
    }
}
