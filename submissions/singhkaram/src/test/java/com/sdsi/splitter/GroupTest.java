package com.sdsi.splitter;

import com.sdsi.splitter.core.Group;
import com.sdsi.splitter.core.ValidationException;
import com.sdsi.splitter.model.Expense;
import com.sdsi.splitter.model.ExpenseRequest;
import com.sdsi.splitter.model.MemberBalance;
import com.sdsi.splitter.model.SplitType;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import java.math.BigDecimal;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class GroupTest {

    private Group group;

    @BeforeEach
    void setUp() {
        group = new Group("Trip", List.of("Asha", "Bhavesh", "Chirag"));
    }

    private static Map<String, BigDecimal> shares(Object... kv) {
        Map<String, BigDecimal> m = new LinkedHashMap<>();
        for (int i = 0; i < kv.length; i += 2) {
            m.put((String) kv[i], new BigDecimal(kv[i + 1].toString()));
        }
        return m;
    }

    private static void assertInvalid(String fragment, Runnable action) {
        ValidationException e = assertThrows(ValidationException.class, action::run);
        assertTrue(e.getMessage().contains(fragment), "expected '" + fragment + "' in: " + e.getMessage());
    }

    private static Map<String, Long> paise(Object... kv) {
        Map<String, Long> m = new LinkedHashMap<>();
        for (int i = 0; i < kv.length; i += 2) {
            m.put((String) kv[i], ((Number) kv[i + 1]).longValue());
        }
        return m;
    }

    @Nested
    class EqualSplit {

        @Test
        void defaultsToEveryMember() {
            Expense e = group.add(ExpenseRequest.equal("Dinner", "Asha", "300", null));
            assertEquals(paise("Asha", 10000, "Bhavesh", 10000, "Chirag", 10000), e.shares());
        }

        @Test
        void subsetOfMembers() {
            Expense e = group.add(ExpenseRequest.equal("Cab", "Asha", "500", List.of("Bhavesh", "Chirag")));
            assertEquals(paise("Bhavesh", 25000, "Chirag", 25000), e.shares());
        }

        @Test
        void leftoverPaiseGoToFirstListed() {
            Expense e = group.add(ExpenseRequest.equal("Snacks", "Asha", "100", null));
            assertEquals(paise("Asha", 3334, "Bhavesh", 3333, "Chirag", 3333), e.shares());
        }

        @Test
        void onePaisaAmongThree() {
            Expense e = group.add(ExpenseRequest.equal("Tiny", "Asha", "0.01", null));
            assertEquals(paise("Asha", 1, "Bhavesh", 0, "Chirag", 0), e.shares());
        }

        @Test
        void payerNeedNotBeAParticipant() {
            group.add(ExpenseRequest.equal("Gift", "Asha", "200", List.of("Bhavesh", "Chirag")));
            assertEquals(20000, group.balances().get(0).net());
        }

        @Test
        void rejectsEmptyDuplicateOrUnknownParticipants() {
            assertInvalid("must not be empty", () -> group.add(ExpenseRequest.equal("x", "Asha", "10", List.of())));
            assertInvalid("more than once", () -> group.add(ExpenseRequest.equal("x", "Asha", "10", List.of("Asha", "asha"))));
            assertInvalid("'Zed' is not a member", () -> group.add(ExpenseRequest.equal("x", "Asha", "10", List.of("Zed"))));
        }

        @Test
        void rejectsSharesOnEqualSplit() {
            assertInvalid("takes 'participants'", () -> group.add(new ExpenseRequest(null, "x", "Asha",
                    BigDecimal.TEN, SplitType.EQUAL, null, shares("Asha", 10))));
        }
    }

    @Nested
    class ExactSplit {

        @Test
        void usesGivenAmounts() {
            Expense e = group.add(ExpenseRequest.exact("Cab", "Chirag", "900", shares("Asha", 300, "Chirag", 600)));
            assertEquals(paise("Asha", 30000, "Chirag", 60000), e.shares());
        }

        @Test
        void zeroShareIsAllowed() {
            group.add(ExpenseRequest.exact("Cab", "Chirag", "900", shares("Asha", 900, "Bhavesh", 0)));
        }

        @Test
        void sharesMustAddUpToTotal() {
            assertInvalid("add up to 800.00 but the amount is 900.00",
                    () -> group.add(ExpenseRequest.exact("Cab", "Chirag", "900", shares("Asha", 300, "Chirag", 500))));
            assertInvalid("add up to 900.01",
                    () -> group.add(ExpenseRequest.exact("Cab", "Chirag", "900", shares("Asha", "300.01", "Chirag", 600))));
        }

        @Test
        void rejectsNegativeOrFractionalPaise() {
            assertInvalid("must not be negative",
                    () -> group.add(ExpenseRequest.exact("x", "Asha", "100", shares("Asha", 200, "Bhavesh", -100))));
            assertInvalid("at most 2 decimal places",
                    () -> group.add(ExpenseRequest.exact("x", "Asha", "100", shares("Asha", "99.999", "Bhavesh", "0.001"))));
        }

        @Test
        void reportsEveryProblemAtOnce() {
            ValidationException e = assertThrows(ValidationException.class, () -> group.add(
                    ExpenseRequest.exact("x", "Zed", "100", shares("Asha", 30, "Nobody", 20))));
            assertEquals(3, e.errors().size(), e.errors().toString()); // payer, member, sum
        }
    }

    @Nested
    class PercentageSplit {

        @Test
        void splitsByPercent() {
            Expense e = group.add(ExpenseRequest.percentage("Scuba", "Asha", "1000", shares("Asha", 50, "Bhavesh", 30, "Chirag", 20)));
            assertEquals(paise("Asha", 50000, "Bhavesh", 30000, "Chirag", 20000), e.shares());
        }

        @Test
        void roundingAlwaysAddsUpToTotal() {
            Expense e = group.add(ExpenseRequest.percentage("x", "Asha", "100",
                    shares("Asha", "33.3333", "Bhavesh", "33.3333", "Chirag", "33.3334")));
            assertEquals(10000, e.shares().values().stream().mapToLong(Long::longValue).sum());
            assertEquals(paise("Asha", 3333, "Bhavesh", 3333, "Chirag", 3334), e.shares());
        }

        @Test
        void largestRemainderGetsTheExtraPaisa() {
            // 0.10 * 15% = 1.5p, 0.10 * 85% = 8.5p: tie on .5, first listed wins the extra paisa.
            Expense e = group.add(ExpenseRequest.percentage("x", "Asha", "0.10", shares("Asha", 15, "Bhavesh", 85)));
            assertEquals(paise("Asha", 2, "Bhavesh", 8), e.shares());
        }

        @Test
        void percentagesMustAddUpTo100() {
            assertInvalid("add up to 99.99, not 100",
                    () -> group.add(ExpenseRequest.percentage("x", "Asha", "100", shares("Asha", 50, "Bhavesh", "49.99"))));
            assertInvalid("add up to 110",
                    () -> group.add(ExpenseRequest.percentage("x", "Asha", "100", shares("Asha", 60, "Bhavesh", 50))));
        }

        @Test
        void rejectsOutOfRangeOrTooPrecise() {
            assertInvalid("between 0 and 100",
                    () -> group.add(ExpenseRequest.percentage("x", "Asha", "100", shares("Asha", 120, "Bhavesh", -20))));
            assertInvalid("more than 4 decimals",
                    () -> group.add(ExpenseRequest.percentage("x", "Asha", "100", shares("Asha", "50.00001", "Bhavesh", "49.99999"))));
        }

        @Test
        void rejectsParticipantsOnPercentageSplit() {
            assertInvalid("takes 'shares'", () -> group.add(new ExpenseRequest(null, "x", "Asha",
                    BigDecimal.TEN, SplitType.PERCENTAGE, List.of("Asha"), shares("Asha", 100))));
        }
    }

    @Nested
    class CommonValidation {

        @Test
        void payerMustBeMember() {
            assertInvalid("payer 'Zed' is not a member", () -> group.add(ExpenseRequest.equal("x", "Zed", "10", null)));
            assertInvalid("paidBy is required", () -> group.add(ExpenseRequest.equal("x", " ", "10", null)));
        }

        @ParameterizedTest
        @ValueSource(strings = {"0", "-5", "0.00"})
        void amountMustBePositive(String amount) {
            assertInvalid("greater than 0", () -> group.add(ExpenseRequest.equal("x", "Asha", amount, null)));
        }

        @Test
        void amountPrecisionAndUpperBound() {
            assertInvalid("2 decimal places", () -> group.add(ExpenseRequest.equal("x", "Asha", "10.005", null)));
            assertInvalid("must not exceed", () -> group.add(ExpenseRequest.equal("x", "Asha", "10000000.01", null)));
            group.add(ExpenseRequest.equal("max", "Asha", "10000000", null));
            group.add(ExpenseRequest.equal("trailing zeros ok", "Asha", "10.500", null));
        }

        @Test
        void namesMatchCaseInsensitively() {
            Expense e = group.add(ExpenseRequest.exact("x", " asha ", "10", shares("BHAVESH", 10)));
            assertEquals("Asha", e.paidBy());
            assertEquals(paise("Bhavesh", 1000), e.shares());
        }

        @Test
        void idsAreGeneratedAndMustBeUnique() {
            Expense a = group.add(ExpenseRequest.equal("x", "Asha", "10", null));
            assertEquals("e1", a.id());
            group.add(new ExpenseRequest("e2", "y", "Asha", BigDecimal.ONE, SplitType.EQUAL, null, null));
            // The next generated id skips over the user's "e2".
            assertEquals("e3", group.add(ExpenseRequest.equal("z", "Asha", "10", null)).id());
            assertInvalid("already used", () -> group.add(
                    new ExpenseRequest("e1", "dup", "Asha", BigDecimal.ONE, SplitType.EQUAL, null, null)));
        }

        @Test
        void invalidExpenseLeavesGroupUnchanged() {
            group.add(ExpenseRequest.equal("ok", "Asha", "90", null));
            assertThrows(ValidationException.class,
                    () -> group.add(ExpenseRequest.exact("bad", "Asha", "100", shares("Asha", 1))));
            assertEquals(1, group.expenses().size());
            assertEquals(6000, group.balances().get(0).net());
        }

        @Test
        void missingSplitType() {
            assertInvalid("split must be one of", () -> group.add(
                    new ExpenseRequest(null, "x", "Asha", BigDecimal.ONE, null, null, null)));
        }
    }

    @Nested
    class Members {

        @Test
        void rejectsDuplicateNamesIgnoringCase() {
            assertInvalid("listed more than once", () -> new Group("g", List.of("Asha", "ASHA")));
        }

        @Test
        void rejectsEmptyAndBadNames() {
            assertInvalid("at least one member", () -> new Group("g", List.of()));
            assertInvalid("must be 1-40", () -> new Group("g", List.of("ok", "")));
            assertInvalid("must be 1-40", () -> new Group("g", List.of("<script>")));
            assertInvalid("must be 1-40", () -> new Group("g", List.of("x".repeat(41))));
        }

        @Test
        void acceptsUnicodeNames() {
            new Group("g", List.of("आशा", "José", "O'Brien", "Mary-Jane"));
        }

        @Test
        void singleMemberGroupIsAlwaysSettled() {
            Group solo = new Group("solo", List.of("Asha"));
            solo.add(ExpenseRequest.equal("x", "Asha", "100", null));
            assertEquals(0, solo.balances().get(0).net());
            assertTrue(solo.settleUp().settlements().isEmpty());
        }
    }

    @Test
    void balancesShowPaidShareAndNet() {
        group.add(ExpenseRequest.equal("Hotel", "Asha", "300", null));
        group.add(ExpenseRequest.exact("Cab", "Bhavesh", "60", shares("Asha", 20, "Chirag", 40)));

        List<MemberBalance> b = group.balances();
        assertEquals(new MemberBalance("Asha", 30000, 12000, 18000), b.get(0));
        assertEquals(new MemberBalance("Bhavesh", 6000, 10000, -4000), b.get(1));
        assertEquals(new MemberBalance("Chirag", 0, 14000, -14000), b.get(2));
        assertEquals(0, b.stream().mapToLong(MemberBalance::net).sum());
    }
}
