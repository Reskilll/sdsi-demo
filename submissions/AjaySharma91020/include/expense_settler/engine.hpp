#ifndef EXPENSE_SETTLER_ENGINE_HPP
#define EXPENSE_SETTLER_ENGINE_HPP

#include <cstdint>
#include <string>
#include <unordered_map>
#include <vector>

#include "models.hpp"

namespace es {

// Compute net balance for each member. Positive = owed, Negative = owes.
// All values in paise.
std::unordered_map<std::string, int64_t> compute_balances(
    const std::vector<Expense> &expenses
);

// Simplify debts into minimum (greedy optimal) list of settlements.
std::vector<Settlement> simplify_debts(
    const std::unordered_map<std::string, int64_t> &net_balances
);

} // namespace es

#endif // EXPENSE_SETTLER_ENGINE_HPP