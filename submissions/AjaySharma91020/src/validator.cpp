#include "expense_settler/validator.hpp"

#include <cmath>
#include <cstdlib>
#include <sstream>

namespace es {

std::vector<ValidationError> validate_expense(
    const Expense &e,
    const std::unordered_set<std::string> *known_members
) {
    std::vector<ValidationError> errors;

    // --- description ----------------------------------------------------------
    if (e.description.empty()) {
        errors.push_back({"description must not be empty", "description"});
    }

    // --- paid_by ---------------------------------------------------------------
    if (e.paid_by.empty()) {
        errors.push_back({"paid_by must not be empty", "paid_by"});
    } else {
        // payer must be a known group member (if known_members provided)
        if (known_members && known_members->find(e.paid_by) == known_members->end()) {
            errors.push_back({
                "paid_by '" + e.paid_by + "' is not a known group member",
                "paid_by"
            });
        }
    }

    // --- amount ---------------------------------------------------------------
    if (e.amount_paise <= 0) {
        errors.push_back({"amount must be positive", "amount"});
    }

    // --- members --------------------------------------------------------------
    if (e.members.empty()) {
        errors.push_back({"members list must not be empty", "members"});
    } else {
        // Check for duplicates
        std::unordered_set<std::string> seen;
        for (size_t i = 0; i < e.members.size(); ++i) {
            const auto &m = e.members[i];
            if (m.empty()) {
                errors.push_back({
                    "members[" + std::to_string(i) + "] must not be empty",
                    "members"
                });
            } else if (seen.find(m) != seen.end()) {
                errors.push_back({
                    "Duplicate member '" + m + "' in members list",
                    "members"
                });
            }
            seen.insert(m);
        }

        // payer must be in members list
        if (!e.paid_by.empty() && seen.find(e.paid_by) == seen.end()) {
            errors.push_back({
                "paid_by '" + e.paid_by + "' is not in the expense's members list",
                "paid_by"
            });
        }
    }

    // --- shares validation (depends on split_type) ---------------------------
    std::unordered_set<std::string> member_set(
        e.members.begin(), e.members.end()
    );

    switch (e.split_type) {
    case SplitType::EQUAL:
        // No shares needed
        break;

    case SplitType::EXACT: {
        if (e.shares.empty()) {
            errors.push_back({"shares map is required for exact split", "shares"});
            break;
        }
        int64_t share_sum = 0;
        for (const auto &member : e.members) {
            auto it = e.shares.find(member);
            if (it == e.shares.end()) {
                errors.push_back({
                    "shares missing for member '" + member + "'",
                    "shares"
                });
                continue;
            }
            if (it->second < 0) {
                errors.push_back({
                    "shares['" + member + "'] must be non-negative",
                    "shares"
                });
            }
            share_sum += it->second;
        }
        // Check for extra members in shares not in members list
        for (const auto &[key, val] : e.shares) {
            if (member_set.find(key) == member_set.end()) {
                errors.push_back({
                    "shares key '" + key + "' is not in the members list",
                    "shares"
                });
            }
        }
        if (errors.empty()) {
            int64_t diff = std::abs(share_sum - e.amount_paise);
            if (diff > 1) { // 1 paisa tolerance for rounding
                errors.push_back({
                    "Exact shares sum (" + std::to_string(share_sum) +
                        " paise) does not match total (" +
                        std::to_string(e.amount_paise) + " paise), diff=" +
                        std::to_string(diff),
                    "shares"
                });
            }
        }
        break;
    }

    case SplitType::PERCENTAGE: {
        if (e.shares.empty()) {
            errors.push_back({"shares map is required for percentage split", "shares"});
            break;
        }
        int64_t pct_sum = 0;
        for (const auto &member : e.members) {
            auto it = e.shares.find(member);
            if (it == e.shares.end()) {
                errors.push_back({
                    "shares missing for member '" + member + "'",
                    "shares"
                });
                continue;
            }
            if (it->second < 0) {
                errors.push_back({
                    "shares['" + member + "'] percentage must be non-negative",
                    "shares"
                });
            }
            pct_sum += it->second;
        }
        for (const auto &[key, val] : e.shares) {
            if (member_set.find(key) == member_set.end()) {
                errors.push_back({
                    "shares key '" + key + "' is not in the members list",
                    "shares"
                });
            }
        }
        if (errors.empty()) {
            // percentages stored as hundredths: 100% = 10000
            int64_t diff = std::abs(pct_sum - 10000);
            if (diff > 1) { // 0.01% tolerance
                double pct = pct_sum / 100.0;
                errors.push_back({
                    "Percentages sum to " + std::to_string(pct).substr(0, 6) +
                        "%, must sum to 100%",
                    "shares"
                });
            }
        }
        break;
    }
    }

    return errors;
}

std::string format_errors(const std::vector<ValidationError> &errors) {
    std::ostringstream oss;
    for (size_t i = 0; i < errors.size(); ++i) {
        if (i > 0) oss << "; ";
        oss << errors[i].message;
    }
    return oss.str();
}

} // namespace es