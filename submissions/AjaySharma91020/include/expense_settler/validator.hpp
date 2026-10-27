#ifndef EXPENSE_SETTLER_VALIDATOR_HPP
#define EXPENSE_SETTLER_VALIDATOR_HPP

#include <string>
#include <unordered_set>
#include <vector>

#include "models.hpp"

namespace es {

struct ValidationError {
    std::string message;
    std::string field; // empty if not field-specific
};

// Validate a single expense. Returns empty vector on success.
std::vector<ValidationError> validate_expense(
    const Expense &expense,
    const std::unordered_set<std::string> *known_members = nullptr
);

// Reconstruct a user-friendly error string from errors.
std::string format_errors(const std::vector<ValidationError> &errors);

} // namespace es

#endif // EXPENSE_SETTLER_VALIDATOR_HPP