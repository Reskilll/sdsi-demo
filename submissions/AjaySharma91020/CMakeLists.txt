cmake_minimum_required(VERSION 3.16)
project(expense-settler VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# ---- Library ----------------------------------------------------------------

add_library(expense_settler STATIC
    src/validator.cpp
    src/engine.cpp
    src/json_loader.cpp
    src/cli.cpp
)

target_include_directories(expense_settler PUBLIC include)

# ---- Main executable --------------------------------------------------------

add_executable(expense-settler src/main.cpp)
target_link_libraries(expense-settler expense_settler)

# ---- Tests ------------------------------------------------------------------

add_executable(expense-settler-tests tests/test_engine.cpp)
target_link_libraries(expense-settler-tests expense_settler)

# Enable tests with CTest
enable_testing()
add_test(NAME engine_tests COMMAND expense-settler-tests)