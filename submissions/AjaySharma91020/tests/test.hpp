#ifndef EXPENSE_SETTLER_TEST_HPP
#define EXPENSE_SETTLER_TEST_HPP

#include <functional>
#include <iostream>
#include <string>
#include <vector>

namespace test {

struct TestCase {
    std::string name;
    std::function<void()> fn;
};

inline std::vector<TestCase> &registry() {
    static std::vector<TestCase> tests;
    return tests;
}

struct Registrar {
    Registrar(const std::string &name, std::function<void()> fn) {
        registry().push_back({name, fn});
    }
};

#define TEST(name) \
    static void test_##name(); \
    static ::test::Registrar registrar_##name(#name, test_##name); \
    static void test_##name()

#define CHECK(cond) \
    do { \
        if (!(cond)) { \
            throw std::runtime_error( \
                std::string("CHECK failed: ") + #cond + \
                " at " + __FILE__ + ":" + std::to_string(__LINE__) \
            ); \
        } \
    } while (0)

#define CHECK_EQ(a, b) \
    do { \
        auto _va = (a); auto _vb = (b); \
        if (!(_va == _vb)) { \
            throw std::runtime_error( \
                std::string("CHECK_EQ failed: ") + #a + " == " + #b + \
                " at " + __FILE__ + ":" + std::to_string(__LINE__) + \
                "  (got: " + std::to_string(_va) + ", expected: " + std::to_string(_vb) + ")" \
            ); \
        } \
    } while (0)

inline int run_all() {
    int passed = 0;
    int failed = 0;
    for (auto &t : registry()) {
        try {
            t.fn();
            std::cout << "[PASS] " << t.name << "\n";
            ++passed;
        } catch (const std::exception &e) {
            std::cout << "[FAIL] " << t.name << "\n";
            std::cout << "       " << e.what() << "\n";
            ++failed;
        }
    }
    std::cout << "\n" << passed << " passed, " << failed << " failed\n";
    return failed == 0 ? 0 : 1;
}

} // namespace test

#endif // EXPENSE_SETTLER_TEST_HPP