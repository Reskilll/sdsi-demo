package com.urlshortener.util;

/**
 * Thread-safe Base62 encoder/decoder for generating short codes from numeric IDs.
 * The character set is alphanumeric (0-9, a-z, A-Z) — URL-safe, no dashes or underscores.
 */
public final class Base62 {

    private static final String ALPHABET =
        "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";
    private static final int BASE = ALPHABET.length(); // 62

    private Base62() { /* utility class */ }

    /**
     * Encode a positive long into a Base62 string.
     * Produces codes of 6–8 characters for typical ID ranges.
     */
    public static String encode(long id) {
        if (id < 0) {
            throw new IllegalArgumentException("id must be non-negative, got " + id);
        }
        if (id == 0) {
            return String.valueOf(ALPHABET.charAt(0));
        }
        StringBuilder sb = new StringBuilder();
        long v = id;
        while (v > 0) {
            sb.append(ALPHABET.charAt((int) (v % BASE)));
            v /= BASE;
        }
        return sb.reverse().toString();
    }

    /**
     * Decode a Base62 string back to a long.
     */
    public static long decode(String code) {
        long result = 0;
        for (int i = 0; i < code.length(); i++) {
            char c = code.charAt(i);
            int idx = ALPHABET.indexOf(c);
            if (idx == -1) {
                throw new IllegalArgumentException("Invalid Base62 character: " + c);
            }
            result = result * BASE + idx;
        }
        return result;
    }
}