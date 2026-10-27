#include "expense_settler/engine.hpp"

#include <algorithm>
#include <cmath>
#include <queue>
#include <unordered_map>

namespace es {

// ---- helper: compute one member's share for a given expense ------------------
static int64_t compute_share(const Expense &e, const std::string &member) {
    int n = static_cast<int>(e.members.size());
    if (n == 0) return 0;

    switch (e.split_type) {
    case SplitType::EQUAL: {
        int64_t base = e.amount_paise / n;
        int64_t remainder = e.amount_paise % n;

        // Distribute remainder paise to first members in list order
        // Find this member's index
        auto it = std::find(e.members.begin(), e.members.end(), member);
        if (it == e.members.end()) return 0;
        size_t idx = static_cast<size_t>(it - e.members.begin());
        return base + (static_cast<int64_t>(idx) < remainder ? 1 : 0);
    }

    case SplitType::EXACT: {
        auto it = e.shares.find(member);
        return (it != e.shares.end()) ? it->second : 0;
    }

    case SplitType::PERCENTAGE: {
        auto it = e.shares.find(member);
        if (it == e.shares.end()) return 0;
        // percentage stored in hundredths; compute share in paise
        // share = amount * pct / 10000  (integer arithmetic)
        int64_t share = (e.amount_paise * it->second) / 10000;
        return share;
    }
    }

    return 0;
}

// ---- M2: net balances -------------------------------------------------------

std::unordered_map<std::string, int64_t> compute_balances(
    const std::vector<Expense> &expenses
) {
    std::unordered_map<std::string, int64_t> net;

    for (const auto &e : expenses) {
        // Credit the payer
        net[e.paid_by] += e.amount_paise;

        // Special handling for percentage: compute total distributed and adjust
        if (e.split_type == SplitType::PERCENTAGE) {
            int64_t allocated = 0;
            int n = static_cast<int>(e.members.size());
            for (int i = 0; i < n - 1; ++i) {
                int64_t share = compute_share(e, e.members[i]);
                net[e.members[i]] -= share;
                allocated += share;
            }
            // Last member gets the remainder to avoid rounding drift
            if (n > 0) {
                int64_t last_share = e.amount_paise - allocated;
                net[e.members[n - 1]] -= last_share;
            }
        } else if (e.split_type == SplitType::EQUAL) {
            // Distribute remainder paise to first N members
            int eq_n = static_cast<int>(e.members.size());
            int64_t base = e.amount_paise / eq_n;
            int64_t remainder = e.amount_paise % eq_n;
            for (int i = 0; i < eq_n; ++i) {
                int64_t share = base + (i < remainder ? 1 : 0);
                net[e.members[i]] -= share;
            }
        } else {
            // EXACT
            for (const auto &member : e.members) {
                net[member] -= compute_share(e, member);
            }
        }
    }

    return net;
}

// ---- M3: debt simplification (greedy algorithm) ----------------------------

std::vector<Settlement> simplify_debts(
    const std::unordered_map<std::string, int64_t> &net_balances
) {
    // Max-heap for creditors, min-heap for debtors (using priority_queue)
    // priority_queue is max-heap by default; we store <priority, name>
    using Creditor = std::pair<int64_t, std::string>;
    using Debtor = std::pair<int64_t, std::string>;

    std::priority_queue<Creditor> creditors; // max-heap
    std::priority_queue<Debtor, std::vector<Debtor>, std::greater<Debtor>> debtors; // min-heap

    for (const auto &[member, balance] : net_balances) {
        if (balance > 0) {
            creditors.push({balance, member});
        } else if (balance < 0) {
            debtors.push({balance, member}); // negative balance = owes
        }
    }

    std::vector<Settlement> settlements;

    while (!creditors.empty() && !debtors.empty()) {
        auto [credit, creditor] = creditors.top();
        creditors.pop();

        auto [debt, debtor] = debtors.top(); // debt is negative
        debtors.pop();

        int64_t owed = -debt; // make positive
        int64_t settled = std::min(credit, owed);

        if (settled > 0) {
            settlements.push_back({debtor, creditor, settled});
        }

        int64_t credit_remaining = credit - settled;
        int64_t debt_remaining = owed - settled;

        if (credit_remaining > 0) {
            creditors.push({credit_remaining, creditor});
        }
        if (debt_remaining > 0) {
            debtors.push({-debt_remaining, debtor}); // store as negative
        }
    }

    // Sort for deterministic output
    std::sort(settlements.begin(), settlements.end(),
        [](const Settlement &a, const Settlement &b) {
            if (a.from_member != b.from_member)
                return a.from_member < b.from_member;
            return a.to_member < b.to_member;
        });

    return settlements;
}

} // namespace es