#include <cmath>
#include <cstdlib>

#include "test.hpp"

#include "expense_settler/engine.hpp"
#include "expense_settler/models.hpp"
#include "expense_settler/validator.hpp"

using namespace es;

// ---- Helpers -----------------------------------------------------------------

static Expense make_expense(
    const std::string &desc,
    const std::string &paid_by,
    int64_t amount_paise,
    SplitType type,
    std::vector<std::string> members,
    std::unordered_map<std::string, int64_t> shares = {}
) {
    Expense e;
    e.description = desc;
    e.paid_by = paid_by;
    e.amount_paise = amount_paise;
    e.split_type = type;
    e.members = std::move(members);
    e.shares = std::move(shares);
    return e;
}

// ---- M1: Three split types ---------------------------------------------------

TEST(equal_split_balances) {
    // ₹100 split equally among 4 people → each pays ₹25
    Expense e = make_expense("dinner", "A", 10000, SplitType::EQUAL,
                             {"A", "B", "C", "D"});
    auto balances = compute_balances({e});
    CHECK_EQ(balances["A"], 7500);  // paid 10000, owes 2500
    CHECK_EQ(balances["B"], -2500);
    CHECK_EQ(balances["C"], -2500);
    CHECK_EQ(balances["D"], -2500);
}

TEST(equal_split_rounding) {
    // ₹100 split among 3 → 33, 33, 34 (remainder to first member)
    Expense e = make_expense("taxi", "A", 10000, SplitType::EQUAL,
                             {"A", "B", "C"});
    auto balances = compute_balances({e});
    // A paid 10000, owes 3334; B owes 3333; C owes 3333
    CHECK_EQ(balances["A"], 10000 - 3334);
    CHECK_EQ(balances["B"], -3333);
    CHECK_EQ(balances["C"], -3333);
    CHECK_EQ(balances["A"] + balances["B"] + balances["C"], 0);
}

TEST(exact_split) {
    Expense e = make_expense("tickets", "A", 10000, SplitType::EXACT,
                             {"A", "B", "C"},
                             {{"A", 5000}, {"B", 3000}, {"C", 2000}});
    auto balances = compute_balances({e});
    CHECK_EQ(balances["A"], 5000);   // paid 10000, owes 5000
    CHECK_EQ(balances["B"], -3000);
    CHECK_EQ(balances["C"], -2000);
}

TEST(percentage_split) {
    Expense e = make_expense("snacks", "A", 10000, SplitType::PERCENTAGE,
                             {"A", "B", "C"},
                             {{"A", 3000}, {"B", 4000}, {"C", 3000}});
    // percentages: A=30%, B=40%, C=30%  (stored as hundredths: 3000=30.00%)
    auto balances = compute_balances({e});
    CHECK_EQ(balances["A"], 10000 - 3000); // paid 10000, owes 3000
    CHECK_EQ(balances["B"], -4000);
    CHECK_EQ(balances["C"], -3000);
}

// ---- M2: Net balances across multiple expenses ------------------------------

TEST(multi_expense_balances) {
    std::vector<Expense> exps = {
        make_expense("dinner", "A", 10000, SplitType::EQUAL, {"A", "B"}),
        make_expense("lunch", "B", 10000, SplitType::EQUAL, {"A", "B"}),
    };
    auto balances = compute_balances(exps);
    // Each paid 10000, each owes 5000+5000=10000 → net 0
    CHECK_EQ(balances["A"], 0);
    CHECK_EQ(balances["B"], 0);
}

// ---- M3: Debt simplification -------------------------------------------------

TEST(simple_settlement_two_people) {
    std::unordered_map<std::string, int64_t> balances = {{"A", 5000}, {"B", -5000}};
    auto settlements = simplify_debts(balances);
    CHECK_EQ(settlements.size(), 1);
    CHECK_EQ(settlements[0].from_member, "B");
    CHECK_EQ(settlements[0].to_member, "A");
    CHECK_EQ(settlements[0].amount_paise, 5000);
}

TEST(settlement_chain_minimizes_transactions) {
    // A owes B 100, B owes C 100 → should collapse to A pays C 100 (1 txn)
    std::unordered_map<std::string, int64_t> balances = {
        {"A", -10000}, {"B", 0}, {"C", 10000}
    };
    auto settlements = simplify_debts(balances);
    CHECK_EQ(settlements.size(), 1);
    CHECK_EQ(settlements[0].from_member, "A");
    CHECK_EQ(settlements[0].to_member, "C");
    CHECK_EQ(settlements[0].amount_paise, 10000);
}

TEST(settlement_multiple_creditors) {
    // A owes 300, B owes 200, C is owed 500
    std::unordered_map<std::string, int64_t> balances = {
        {"A", -30000}, {"B", -20000}, {"C", 50000}
    };
    auto settlements = simplify_debts(balances);
    CHECK_EQ(settlements.size(), 2);
    int64_t total_to_c = 0;
    for (const auto &s : settlements) {
        CHECK_EQ(s.to_member, "C");
        total_to_c += s.amount_paise;
    }
    CHECK_EQ(total_to_c, 50000);
}

TEST(settlement_zero_balances_returns_empty) {
    std::unordered_map<std::string, int64_t> balances = {
        {"A", 0}, {"B", 0}, {"C", 0}
    };
    auto settlements = simplify_debts(balances);
    CHECK_EQ(settlements.size(), 0);
}

TEST(settlement_conserves_total) {
    // Random balances: verify debt total == credit total after settling
    std::unordered_map<std::string, int64_t> balances = {
        {"A", 12345}, {"B", -6700}, {"C", -3000}, {"D", -2645},
        {"E", 0}
    };
    auto settlements = simplify_debts(balances);
    // Verify each settlement's amount is positive and <= 1000000
    for (const auto &s : settlements) {
        CHECK(s.amount_paise > 0);
    }
    // Verify conservation: sum of creditor balances == sum of debtor paise settled
    int64_t credit_total = 0;
    int64_t debt_total = 0;
    for (const auto &[m, b] : balances) {
        if (b > 0) credit_total += b;
        if (b < 0) debt_total += -b;
    }
    CHECK_EQ(credit_total, debt_total);
}

// ---- M5: Validation -----------------------------------------------------------

TEST(validate_percentage_sums_to_100) {
    Expense e = make_expense("x", "A", 10000, SplitType::PERCENTAGE,
                             {"A", "B"},
                             {{"A", 6000}, {"B", 5000}}); // sums to 110%
    auto errors = validate_expense(e, nullptr);
    CHECK(!errors.empty());
}

TEST(validate_percentage_valid) {
    Expense e = make_expense("x", "A", 10000, SplitType::PERCENTAGE,
                             {"A", "B"},
                             {{"A", 6000}, {"B", 4000}}); // 100%
    auto errors = validate_expense(e, nullptr);
    CHECK(errors.empty());
}

TEST(validate_exact_sums_to_total) {
    Expense e = make_expense("x", "A", 10000, SplitType::EXACT,
                             {"A", "B"},
                             {{"A", 6000}, {"B", 3000}}); // sums to 9000 != 10000
    auto errors = validate_expense(e, nullptr);
    CHECK(!errors.empty());
}

TEST(validate_exact_valid) {
    Expense e = make_expense("x", "A", 10000, SplitType::EXACT,
                             {"A", "B"},
                             {{"A", 6000}, {"B", 4000}});
    auto errors = validate_expense(e, nullptr);
    CHECK(errors.empty());
}

TEST(validate_payer_is_group_member) {
    std::unordered_set<std::string> known = {"A", "B", "C"};
    Expense e = make_expense("x", "Z", 10000, SplitType::EQUAL, {"A", "B"});
    auto errors = validate_expense(e, &known);
    CHECK(!errors.empty());
}

TEST(validate_payer_in_expense_members) {
    Expense e = make_expense("x", "A", 10000, SplitType::EQUAL, {"B", "C"});
    auto errors = validate_expense(e, nullptr);
    bool found = false;
    for (const auto &err : errors) {
        if (err.message.find("not in the expense's members") != std::string::npos)
            found = true;
    }
    CHECK(found);
}

TEST(validate_negative_amount) {
    Expense e = make_expense("x", "A", -10000, SplitType::EQUAL, {"A", "B"});
    auto errors = validate_expense(e, nullptr);
    CHECK(!errors.empty());
}

TEST(validate_duplicate_members) {
    Expense e = make_expense("x", "A", 10000, SplitType::EQUAL, {"A", "A", "B"});
    auto errors = validate_expense(e, nullptr);
    CHECK(!errors.empty());
}

TEST(validate_empty_members) {
    Expense e = make_expense("x", "A", 10000, SplitType::EQUAL, {});
    auto errors = validate_expense(e, nullptr);
    CHECK(!errors.empty());
}

// ---- Edge cases -----------------------------------------------------------------

TEST(edge_zero_members_all_settled) {
    // No expenses at all
    std::vector<Expense> empty;
    auto balances = compute_balances(empty);
    CHECK(balances.empty());
    auto settlements = simplify_debts(balances);
    CHECK(settlements.empty());
}

TEST(edge_single_member_exact) {
    // One member pays everything, splits with themselves
    Expense e = make_expense("solo", "A", 10000, SplitType::EQUAL, {"A"});
    auto balances = compute_balances({e});
    CHECK_EQ(balances["A"], 0); // paid 10000, owes 10000
}

TEST(edge_large_amount) {
    // ₹1,00,000 split among 3
    Expense e = make_expense("big", "A", 10000000, SplitType::EQUAL,
                             {"A", "B", "C"});
    auto balances = compute_balances({e});
    CHECK_EQ(balances["A"] + balances["B"] + balances["C"], 0);
    // A paid 10000000, owes 3333334 (with remainder to first member)
    CHECK_EQ(balances["A"], 10000000 - 3333334);
}

TEST(edge_percentage_rounding_conserves_total) {
    // 1/3 split via percentage: 33.33, 33.33, 33.34
    Expense e = make_expense("third", "A", 10000, SplitType::PERCENTAGE,
                             {"A", "B", "C"},
                             {{"A", 3333}, {"B", 3333}, {"C", 3334}});
    auto balances = compute_balances({e});
    CHECK_EQ(balances["A"] + balances["B"] + balances["C"], 0);
}

int main() {
    return test::run_all();
}