package com.flashsale;

import java.util.*;

/**
 * Minimal zero-dependency JSON parser — supports objects, arrays, strings,
 * numbers, booleans, and null.  Just enough to parse inventory.json.
 *
 * <p>Not a general-purpose parser: no escape-sequence handling beyond
 * basic unicode, no streaming.  Handles the inventory file format reliably.
 */
public final class Json {

    private Json() { /* utility */ }

    // ── parse from String ──────────────────────────────────────

    public static Map<String, Object> parseObject(String json) {
        return parseObject(new Tokens(json));
    }

    public static List<Object> parseArray(String json) {
        return parseArray(new Tokens(json));
    }

    // ── parse from Tokens ──────────────────────────────────────

    static Map<String, Object> parseObject(Tokens t) {
        t.skip('{');
        Map<String, Object> map = new LinkedHashMap<>();
        if (t.peek() == '}') { t.advance(); return map; }
        while (true) {
            String key = parseString(t);
            t.skip(':');
            Object val = parseValue(t);
            map.put(key, val);
            if (t.peek() == '}') { t.advance(); return map; }
            t.skip(',');
        }
    }

    static List<Object> parseArray(Tokens t) {
        t.skip('[');
        List<Object> list = new ArrayList<>();
        if (t.peek() == ']') { t.advance(); return list; }
        while (true) {
            list.add(parseValue(t));
            if (t.peek() == ']') { t.advance(); return list; }
            t.skip(',');
        }
    }

    static Object parseValue(Tokens t) {
        char c = t.peek();
        return switch (c) {
            case '"' -> parseString(t);
            case '{' -> parseObject(t);
            case '[' -> parseArray(t);
            case 't', 'f' -> parseBool(t);
            case 'n' -> parseNull(t);
            default -> parseNumber(t);
        };
    }

    static String parseString(Tokens t) {
        t.skip('"');
        StringBuilder sb = new StringBuilder();
        while (t.pos < t.json.length()) {
            char c = t.json.charAt(t.pos);
            if (c == '"') { t.rawAdvance(); return sb.toString(); }
            if (c == '\\') {
                t.rawAdvance();
                char esc = t.json.charAt(t.pos);
                switch (esc) {
                    case '"', '\\', '/' -> sb.append(esc);
                    case 'n' -> sb.append('\n');
                    case 'r' -> sb.append('\r');
                    case 't' -> sb.append('\t');
                    case 'u' -> {
                        String hex = t.json.substring(t.pos + 1, t.pos + 5);
                        sb.append((char) Integer.parseInt(hex, 16));
                        t.pos += 4;
                    }
                    default -> sb.append('\\').append(esc);
                }
                t.rawAdvance();
            } else {
                sb.append(c);
                t.rawAdvance();
            }
        }
        throw new IllegalArgumentException("Unterminated string");
    }

    static Object parseNumber(Tokens t) {
        int start = t.pos;
        if (t.peek() == '-') t.pos++;
        while (t.pos < t.json.length() && Character.isDigit(t.json.charAt(t.pos)))
            t.pos++;
        boolean isDouble = false;
        if (t.pos < t.json.length() && t.json.charAt(t.pos) == '.') {
            isDouble = true;
            t.pos++;
            while (t.pos < t.json.length() && Character.isDigit(t.json.charAt(t.pos)))
                t.pos++;
        }
        if (t.pos < t.json.length() && (t.json.charAt(t.pos) == 'e' || t.json.charAt(t.pos) == 'E')) {
            isDouble = true;
            t.pos++;
            if (t.pos < t.json.length() && (t.json.charAt(t.pos) == '+' || t.json.charAt(t.pos) == '-'))
                t.pos++;
            while (t.pos < t.json.length() && Character.isDigit(t.json.charAt(t.pos)))
                t.pos++;
        }
        String numStr = t.json.substring(start, t.pos);
        if (isDouble) return Double.parseDouble(numStr);
        long lv = Long.parseLong(numStr);
        if (lv >= Integer.MIN_VALUE && lv <= Integer.MAX_VALUE) return (int) lv;
        return lv;
    }

    static Boolean parseBool(Tokens t) {
        if (t.json.startsWith("true", t.pos)) { t.pos += 4; return true; }
        if (t.json.startsWith("false", t.pos)) { t.pos += 5; return false; }
        throw new IllegalArgumentException("Expected true/false at " + t.pos);
    }

    static Object parseNull(Tokens t) {
        if (t.json.startsWith("null", t.pos)) { t.pos += 4; return null; }
        throw new IllegalArgumentException("Expected null at " + t.pos);
    }

    // ── tokenizer ─────────────────────────────────────────────

    static class Tokens {
        final String json;
        int pos;

        Tokens(String json) {
            this.json = json;
            this.pos = 0;
            skipWhitespace();
        }

        char peek() {
            skipWhitespace();
            if (pos >= json.length()) throw new IllegalArgumentException("Unexpected end of JSON");
            return json.charAt(pos);
        }

        void advance() { pos++; skipWhitespace(); }

        /** Advance one char WITHOUT stripping whitespace (for use inside strings). */
        void rawAdvance() { pos++; }

        void skip(char expected) {
            if (peek() != expected)
                throw new IllegalArgumentException("Expected '" + expected + "' at " + pos + ", got '" + peek() + "'");
            advance();
        }

        void skipWhitespace() {
            while (pos < json.length() && Character.isWhitespace(json.charAt(pos)))
                pos++;
        }
    }
}