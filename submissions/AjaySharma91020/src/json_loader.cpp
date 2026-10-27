#include "expense_settler/json_loader.hpp"

#include <cctype>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <unordered_set>

namespace es {

// ============================================================================
// Minimal JSON parser — no external dependencies.
// Supports: null, bool, int, double (stored as string then converted),
//           string, array, object. Enough for expenses.json.
// ============================================================================

class JsonParser {
public:
    explicit JsonParser(const std::string &src) : src_(src), pos_(0) {}

    enum class Type { NUL, BOOL, NUMBER, STRING, ARRAY, OBJECT };

    struct Value {
        Type type = Type::NUL;
        std::string str;           // for STRING, NUMBER
        bool bval = false;         // for BOOL
        std::vector<Value> arr;    // for ARRAY
        std::vector<std::pair<std::string, Value>> obj; // for OBJECT

        bool is_null() const { return type == Type::NUL; }
        bool is_number() const { return type == Type::NUMBER; }
        bool is_string() const { return type == Type::STRING; }
        bool is_array() const { return type == Type::ARRAY; }
        bool is_object() const { return type == Type::OBJECT; }

        int64_t as_int64() const {
            // Parse from string representation
            return static_cast<int64_t>(std::stoll(str));
        }

        double as_double() const {
            return std::stod(str);
        }

        const Value &operator[](const std::string &key) const {
            for (const auto &[k, v] : obj) {
                if (k == key) return v;
            }
            throw std::runtime_error("Key not found: " + key);
        }

        bool has(const std::string &key) const {
            for (const auto &[k, v] : obj) {
                if (k == key) return true;
            }
            return false;
        }

        const std::vector<Value> &as_array() const { return arr; }
        size_t size() const {
            if (type == Type::ARRAY) return arr.size();
            if (type == Type::OBJECT) return obj.size();
            return 0;
        }
    };

    Value parse() {
        skip_whitespace();
        return parse_value();
    }

private:
    const std::string &src_;
    size_t pos_;

    void skip_whitespace() {
        while (pos_ < src_.size() && std::isspace(static_cast<unsigned char>(src_[pos_])))
            ++pos_;
    }

    char peek() {
        if (pos_ >= src_.size()) throw std::runtime_error("Unexpected end of JSON");
        return src_[pos_];
    }

    char next() {
        if (pos_ >= src_.size()) throw std::runtime_error("Unexpected end of JSON");
        return src_[pos_++];
    }

    void expect(char c) {
        char got = next();
        if (got != c) {
            throw std::runtime_error(
                std::string("Expected '") + c + "' but got '" + got + "'"
            );
        }
    }

    Value parse_value() {
        skip_whitespace();
        char c = peek();

        switch (c) {
        case 'n': return parse_null();
        case 't': case 'f': return parse_bool();
        case '"': return parse_string();
        case '[': return parse_array();
        case '{': return parse_object();
        default:
            if (c == '-' || std::isdigit(static_cast<unsigned char>(c)))
                return parse_number();
            throw std::runtime_error(
                std::string("Unexpected character: '") + c + "'"
            );
        }
    }

    Value parse_null() {
        if (src_.substr(pos_, 4) == "null") {
            pos_ += 4;
            Value v;
            v.type = Type::NUL;
            return v;
        }
        throw std::runtime_error("Expected 'null'");
    }

    Value parse_bool() {
        Value v;
        v.type = Type::BOOL;
        if (src_.substr(pos_, 4) == "true") {
            v.bval = true;
            pos_ += 4;
        } else if (src_.substr(pos_, 5) == "false") {
            v.bval = false;
            pos_ += 5;
        } else {
            throw std::runtime_error("Expected 'true' or 'false'");
        }
        return v;
    }

    Value parse_number() {
        Value v;
        v.type = Type::NUMBER;
        size_t start = pos_;
        if (peek() == '-') pos_++;
        while (pos_ < src_.size() && std::isdigit(static_cast<unsigned char>(src_[pos_])))
            pos_++;
        if (pos_ < src_.size() && src_[pos_] == '.') {
            pos_++;
            while (pos_ < src_.size() && std::isdigit(static_cast<unsigned char>(src_[pos_])))
                pos_++;
        }
        if (pos_ < src_.size() && (src_[pos_] == 'e' || src_[pos_] == 'E')) {
            pos_++;
            if (pos_ < src_.size() && (src_[pos_] == '+' || src_[pos_] == '-')) pos_++;
            while (pos_ < src_.size() && std::isdigit(static_cast<unsigned char>(src_[pos_])))
                pos_++;
        }
        v.str = src_.substr(start, pos_ - start);
        return v;
    }

    Value parse_string() {
        expect('"');
        Value v;
        v.type = Type::STRING;
        std::ostringstream oss;

        while (pos_ < src_.size()) {
            char c = next();
            if (c == '"') {
                v.str = oss.str();
                return v;
            }
            if (c == '\\') {
                char esc = next();
                switch (esc) {
                case '"':  oss << '"'; break;
                case '\\': oss << '\\'; break;
                case '/':  oss << '/'; break;
                case 'b':  oss << '\b'; break;
                case 'f':  oss << '\f'; break;
                case 'n':  oss << '\n'; break;
                case 'r':  oss << '\r'; break;
                case 't':  oss << '\t'; break;
                case 'u': {
                    // Parse 4 hex digits
                    std::string hex = src_.substr(pos_, 4);
                    pos_ += 4;
                    uint32_t codepoint = static_cast<uint32_t>(std::stoul(hex, nullptr, 16));
                    if (codepoint <= 0x7F) {
                        oss << static_cast<char>(codepoint);
                    } else if (codepoint <= 0x7FF) {
                        oss << static_cast<char>(0xC0 | (codepoint >> 6));
                        oss << static_cast<char>(0x80 | (codepoint & 0x3F));
                    } else {
                        oss << static_cast<char>(0xE0 | (codepoint >> 12));
                        oss << static_cast<char>(0x80 | ((codepoint >> 6) & 0x3F));
                        oss << static_cast<char>(0x80 | (codepoint & 0x3F));
                    }
                    break;
                }
                default:
                    throw std::runtime_error(
                        std::string("Invalid escape: \\") + esc
                    );
                }
            } else {
                oss << c;
            }
        }
        throw std::runtime_error("Unterminated string");
    }

    Value parse_array() {
        expect('[');
        Value v;
        v.type = Type::ARRAY;
        skip_whitespace();

        if (peek() == ']') {
            pos_++;
            return v;
        }

        while (true) {
            v.arr.push_back(parse_value());
            skip_whitespace();
            char c = next();
            if (c == ']') break;
            if (c != ',')
                throw std::runtime_error(
                    std::string("Expected ',' or ']' in array, got '") + c + "'"
                );
            skip_whitespace();
        }
        return v;
    }

    Value parse_object() {
        expect('{');
        Value v;
        v.type = Type::OBJECT;
        skip_whitespace();

        if (peek() == '}') {
            pos_++;
            return v;
        }

        while (true) {
            skip_whitespace();
            std::string key = parse_string().str;
            skip_whitespace();
            expect(':');
            Value val = parse_value();
            v.obj.emplace_back(key, std::move(val));
            skip_whitespace();
            char c = next();
            if (c == '}') break;
            if (c != ',')
                throw std::runtime_error(
                    std::string("Expected ',' or '}' in object, got '") + c + "'"
                );
        }
        return v;
    }
};

// ============================================================================
// Parse expense from JSON object
// ============================================================================

static SplitType parse_split_type(const std::string &s) {
    if (s == "equal")      return SplitType::EQUAL;
    if (s == "exact")      return SplitType::EXACT;
    if (s == "percentage") return SplitType::PERCENTAGE;
    throw std::runtime_error("Invalid split_type: " + s);
}

static Expense expense_from_json(const JsonParser::Value &v) {
    Expense e;

    if (!v.is_object())
        throw std::runtime_error("Each expense must be a JSON object");

    // Description
    if (!v.has("description"))
        throw std::runtime_error("Missing 'description' field");
    e.description = v["description"].str;

    // Paid by
    if (!v.has("paid_by"))
        throw std::runtime_error("Missing 'paid_by' field");
    e.paid_by = v["paid_by"].str;

    // Amount — accept integer or float, convert to paise
    if (!v.has("amount"))
        throw std::runtime_error("Missing 'amount' field");
    {
        double raw = v["amount"].as_double();
        e.amount_paise = static_cast<int64_t>(std::llround(raw * 100.0));
    }

    // Split type
    if (!v.has("split_type"))
        throw std::runtime_error("Missing 'split_type' field");
    e.split_type = parse_split_type(v["split_type"].str);

    // Members
    if (!v.has("members"))
        throw std::runtime_error("Missing 'members' field");
    {
        const auto &members = v["members"];
        if (!members.is_array())
            throw std::runtime_error("'members' must be an array");
        for (const auto &m : members.arr) {
            if (!m.is_string())
                throw std::runtime_error("Each member must be a string");
            e.members.push_back(m.str);
        }
    }

    // Shares (optional for equal, required for exact/percentage)
    if (v.has("shares")) {
        const auto &shares = v["shares"];
        if (!shares.is_object())
            throw std::runtime_error("'shares' must be an object");
        for (const auto &[key, val] : shares.obj) {
            double raw = val.as_double();
            if (e.split_type == SplitType::PERCENTAGE) {
                // Store as hundredths of percent: 30.5% = 3050
                e.shares[key] = static_cast<int64_t>(std::llround(raw * 100.0));
            } else {
                // EXACT: store as paise
                e.shares[key] = static_cast<int64_t>(std::llround(raw * 100.0));
            }
        }
    }

    return e;
}

// ============================================================================
// Public API
// ============================================================================

std::vector<Expense> load_expenses_from_file(const std::string &filepath) {
    // Read entire file
    std::ifstream f(filepath, std::ios::binary);
    if (!f.is_open()) {
        throw std::runtime_error("Cannot open file: " + filepath);
    }

    // Security: check file size (max 10 MB)
    f.seekg(0, std::ios::end);
    auto size = f.tellg();
    if (size > 10 * 1024 * 1024) {
        throw std::runtime_error("File too large (max 10 MB)");
    }
    f.seekg(0, std::ios::beg);

    std::ostringstream buf;
    buf << f.rdbuf();
    std::string content = buf.str();

    if (content.empty()) {
        throw std::runtime_error("File is empty: " + filepath);
    }

    // Parse JSON
    JsonParser parser(content);
    auto root = parser.parse();

    std::vector<Expense> expenses;

    // Support single object or array at top level
    if (root.is_object()) {
        expenses.push_back(expense_from_json(root));
    } else if (root.is_array()) {
        for (const auto &item : root.arr) {
            expenses.push_back(expense_from_json(item));
        }
    } else {
        throw std::runtime_error(
            "Top-level JSON must be an object or array"
        );
    }

    if (expenses.empty()) {
        throw std::runtime_error("No expenses found in file");
    }

    return expenses;
}

} // namespace es