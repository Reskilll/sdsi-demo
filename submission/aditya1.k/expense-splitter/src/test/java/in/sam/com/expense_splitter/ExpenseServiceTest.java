package in.sam.com.expense_splitter;

import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.Collection;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class ExpenseServiceTest {

    private BigDecimal bd(String value) {
        return new BigDecimal(value);
    }

    private Expense expense(
            String description,
            String payer,
            String amount,
            String type,
            Split... splits) {

        Expense e = new Expense();
        e.setDescription(description);
        e.setPayer(payer);
        e.setAmount(bd(amount));
        e.setSplitType(type);
        e.setSplits(List.of(splits));
        return e;
    }

    private Split split(String member, String value) {
        return new Split(member,
                value == null ? null : bd(value));
    }

    private Collection<String> members(String... names) {
        return List.of(names);
    }

    @Test
    void equalSplitCalculatesBalances() {
        ExpenseService service =
                new ExpenseService(members("A", "B"));

        service.process(expense("Dinner", "A", "100.00", "EQUAL",
                split("A", null), split("B", null)));

        assertEquals(bd("50.00"),
                service.getNetBalances().get("A"));
        assertEquals(bd("-50.00"),
                service.getNetBalances().get("B"));
    }

    @Test
    void exactSplitCalculatesBalances() {
        ExpenseService service =
                new ExpenseService(members("A", "B"));

        service.process(expense("Lunch", "A", "100.00", "EXACT",
                split("A", "30.00"), split("B", "70.00")));

        assertEquals(bd("70.00"),
                service.getNetBalances().get("A"));
        assertEquals(bd("-70.00"),
                service.getNetBalances().get("B"));
    }

    @Test
    void percentageSplitCalculatesBalances() {
        ExpenseService service =
                new ExpenseService(members("A", "B"));

        service.process(expense("Rent", "A", "200.00", "PERCENTAGE",
                split("A", "25"), split("B", "75")));

        assertEquals(bd("150.00"),
                service.getNetBalances().get("A"));
        assertEquals(bd("-150.00"),
                service.getNetBalances().get("B"));
    }

    @Test
    void rejectsPercentagesNotSummingTo100() {
        ExpenseService service =
                new ExpenseService(members("A", "B"));

        Expense e = expense("Cab", "A", "100.00", "PERCENTAGE",
                split("A", "40"), split("B", "50"));

        assertThrows(IllegalArgumentException.class,
                () -> service.process(e));
    }

    @Test
    void rejectsExactAmountsNotMatchingTotal() {
        ExpenseService service =
                new ExpenseService(members("A", "B"));

        Expense e = expense("Groceries", "A", "100.00", "EXACT",
                split("A", "40"), split("B", "50"));

        assertThrows(IllegalArgumentException.class,
                () -> service.process(e));
    }

    @Test
    void rejectsPayerOutsideGroup() {
        ExpenseService service =
                new ExpenseService(members("A", "B"));

        Expense e = expense("Movie", "C", "100.00", "EQUAL",
                split("A", null), split("B", null));

        assertThrows(IllegalArgumentException.class,
                () -> service.process(e));
    }

    @Test
    void simplifiesDebtsIntoOnePayment() {
        DebtSimplifier simplifier = new DebtSimplifier();

        List<DebtSimplifier.Settlement> result =
                simplifier.simplify(Map.of(
                        "A", bd("100.00"),
                        "B", bd("-60.00"),
                        "C", bd("-40.00")
                ));

        assertEquals(2, result.size());

        BigDecimalTotal total = new BigDecimalTotal(result);
        assertEquals(bd("100.00"), total.amount);
    }

    private static class BigDecimalTotal {
        final java.math.BigDecimal amount;

        BigDecimalTotal(List<DebtSimplifier.Settlement> settlements) {
            amount = settlements.stream()
                    .map(DebtSimplifier.Settlement::amount)
                    .reduce(BigDecimal.ZERO, BigDecimal::add);
        }
    }
}