#ifndef EXPENSE_SETTLER_MODELS_HPP
#define EXPENSE_SETTLER_MODELS_HPP

#include <cstdint>
#include <string>
#include <unordered_map>
#include <vector>

namespace es {

enum class SplitType { EQUAL, EXACT, PERCENTAGE };

struct Expense {
    std::string description;
    std::string paid_by;
    int64_t amount_paise; // total in paise (₹1 = 100 paise)
    SplitType split_type;
    std::vector<std::string> members;
    // For EXACT: member -> exact paise owed
    // For PERCENTAGE: member -> percentage (stored as hundredths, e.g. 30.50% = 3050)
    std::unordered_map<std::string, int64_t> shares;
};

struct Settlement {
    std::string from_member;
    std::string to_member;
    int64_t amount_paise;
};

} // namespace es

#endif // EXPENSE_SETTLER_MODELS_HPP