#include <iostream>
#include <stdexcept>

#include "expense_settler/cli.hpp"
#include "expense_settler/json_loader.hpp"
#include "expense_settler/validator.hpp"

int main(int argc, char *argv[]) {
    if (argc < 2) {
        std::cerr << "Usage: expense-settler <expenses.json>\n";
        std::cerr << "       expense-settler --validate <expenses.json>\n";
        return 1;
    }

    std::string arg1 = argv[1];
    bool validate_only = false;
    std::string filepath;

    if (arg1 == "--validate") {
        validate_only = true;
        if (argc < 3) {
            std::cerr << "Error: --validate requires a file path\n";
            return 1;
        }
        filepath = argv[2];
    } else {
        filepath = arg1;
    }

    try {
        auto expenses = es::load_expenses_from_file(filepath);

        // Build known members set from all expenses
        std::unordered_set<std::string> known_members;
        for (const auto &e : expenses) {
            for (const auto &m : e.members) {
                known_members.insert(m);
            }
        }

        if (validate_only) {
            // Validate-only mode
            bool all_valid = true;
            for (size_t i = 0; i < expenses.size(); ++i) {
                auto errors = es::validate_expense(expenses[i], &known_members);
                if (!errors.empty()) {
                    all_valid = false;
                    std::cerr << "Expense #" << (i + 1)
                              << " (" << expenses[i].description << "): "
                              << es::format_errors(errors) << "\n";
                }
            }
            if (all_valid) {
                std::cout << "All " << expenses.size() << " expense(s) are valid.\n";
                return 0;
            }
            return 1;
        } else {
            // Validate and report
            bool all_valid = true;
            for (size_t i = 0; i < expenses.size(); ++i) {
                auto errors = es::validate_expense(expenses[i], &known_members);
                if (!errors.empty()) {
                    all_valid = false;
                    std::cerr << "Validation error in expense #" << (i + 1)
                              << " (" << expenses[i].description << "): "
                              << es::format_errors(errors) << "\n";
                }
            }
            if (!all_valid) {
                std::cerr << "\nAborting due to validation errors.\n";
                return 1;
            }

            std::cout << es::generate_report(expenses);
        }

    } catch (const std::exception &e) {
        std::cerr << "Error: " << e.what() << "\n";
        return 1;
    }

    return 0;
}