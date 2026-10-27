# Minimal Makefile (when CMake isn't available)
CXX      ?= g++
CXXFLAGS ?= -std=c++17 -Wall -Wextra -pedantic -O2
INC       = -Iinclude

SRC      = src/main.cpp src/validator.cpp src/engine.cpp src/json_loader.cpp src/cli.cpp
OBJ      = $(SRC:.cpp=.o)
TARGET   = expense-settler

TEST_SRC = tests/test_engine.cpp src/validator.cpp src/engine.cpp src/json_loader.cpp src/cli.cpp
TEST_OBJ = $(TEST_SRC:.cpp=.o)
TEST_TGT = expense-settler-tests

.PHONY: all clean test

all: $(TARGET)

$(TARGET): $(OBJ)
	$(CXX) $(CXXFLAGS) -o $@ $^

%.o: %.cpp
	$(CXX) $(CXXFLAGS) $(INC) -c -o $@ $<

test: $(TEST_TGT)
	./$(TEST_TGT)

$(TEST_TGT): $(TEST_OBJ)
	$(CXX) $(CXXFLAGS) -o $@ $^

clean:
	rm -f $(OBJ) $(TEST_OBJ) $(TARGET) $(TEST_TGT)