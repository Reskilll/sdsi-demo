#ifndef EXPENSE_SETTLER_CLI_HPP
#define EXPENSE_SETTLER_CLI_HPP

#include <string>
#include <vector>

#include "models.hpp"

namespace es {

// Generate a human-readable report from a list of expenses.
std::string generate_report(const std::vector<Expense> &expenses);

} // namespace es

#endif // EXPENSE_SETTLER_CLI_HPP