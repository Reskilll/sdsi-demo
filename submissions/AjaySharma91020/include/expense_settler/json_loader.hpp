#ifndef EXPENSE_SETTLER_JSON_LOADER_HPP
#define EXPENSE_SETTLER_JSON_LOADER_HPP

#include <string>
#include <vector>

#include "models.hpp"

namespace es {

// Load expenses from a JSON file. Supports single object or array.
// Throws std::runtime_error on failure.
std::vector<Expense> load_expenses_from_file(const std::string &filepath);

} // namespace es

#endif // EXPENSE_SETTLER_JSON_LOADER_HPP