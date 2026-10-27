#include "expense_settler/cli.hpp"

#include <algorithm>
#include <iomanip>
#include <sstream>

#include "expense_settler/engine.hpp"

namespace es {

static std::string paise_to_rupees(int64_t paise) {
    // Format as ₹X.YY  (paise → rupees string)
    int64_t rupees = paise / 100;
    int64_t frac = std::abs(paise % 100);
    std::ostringstream oss;
    if (paise < 0 && rupees == 0) {
        oss << "-0." << std::setw(2) << std::setfill('0') << frac;
    } else {
        oss << rupees << "." << std::setw(2) << std::setfill('0') << frac;
    }
    return oss.str();
}

static std::string format_signed(int64_t paise) {
    std::ostringstream oss;
    if (paise > 0) oss << "+";
    oss << paise_to_rupees(paise);
    return oss.str();
}

std::string generate_report(const std::vector<Expense> &expenses) {
    if (expenses.empty()) {
        return "No expenses to report.";
    }

    auto balances = compute_balances(expenses);
    auto settlements = simplify_debts(balances);

    std::ostringstream oss;

    // Divider
    const std::string div(60, '=');

    oss << div << "\n";
    oss << "  EXPENSE SETTLER — Report\n";
    oss << div << "\n\n";

    // --- Net Balances ---
    oss << "-- Net Balances --\n";
    oss << std::left << std::setw(24) << "  Member"
        << std::right << std::setw(14) << "Balance (₹)" << "\n";
    oss << "  " << std::string(22, '-') << " " << std::string(12, '-') << "\n";

    // Collect members sorted
    std::vector<std::string> members_sorted;
    for (const auto &[name, _] : balances) {
        members_sorted.push_back(name);
    }
    std::sort(members_sorted.begin(), members_sorted.end());

    for (const auto &member : members_sorted) {
        int64_t bal = balances[member];
        oss << "  " << std::left << std::setw(22) << member
            << std::right << std::setw(14) << format_signed(bal) << "\n";
    }
    oss << "\n";

    // --- Settlements ---
    oss << "-- Simplified Settlements --\n";
    if (settlements.empty()) {
        oss << "  All settled up!\n";
    } else {
        for (const auto &s : settlements) {
            oss << "  " << s.from_member
                << " pays " << s.to_member
                << " ₹" << paise_to_rupees(s.amount_paise) << "\n";
        }
    }
    oss << "\n";
    oss << div << "\n";

    return oss.str();
}

} // namespace es