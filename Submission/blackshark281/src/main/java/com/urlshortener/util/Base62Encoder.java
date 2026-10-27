package com.urlshortener.util;

/**
 * Encodes numeric IDs to base62 strings and decodes them back.
 * Base62 alphabet: 0-9, a-z, A-Z (62 characters).
 * Minimum output length is 6 characters; grows as needed for larger IDs.
 */
public final class Base62Encoder {

    private static final String ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ";
    private static final int BASE = 62;
    private static final int MIN_LENGTH = 6;

    private Base62Encoder() {
        // utility class
    }

    /**
     * Encode a positive long to a base62 string.
     *
     * @param id positive number to encode
     * @return base62 string of at least {@value MIN_LENGTH} characters
     * @throws IllegalArgumentException if id is negative
     */
    public static String encode(long id) {
        if (id < 0) {
            throw new IllegalArgumentException("ID must be non-negative, got: " + id);
        }

        if (id == 0) {
            return String.valueOf(ALPHABET.charAt(0)).repeat(MIN_LENGTH);
        }

        StringBuilder sb = new StringBuilder();
        long value = id;
        while (value > 0) {
            sb.append(ALPHABET.charAt((int) (value % BASE)));
            value /= BASE;
        }

        // Pad to minimum length
        while (sb.length() < MIN_LENGTH) {
            sb.append(ALPHABET.charAt(0));
        }

        return sb.reverse().toString();
    }

    /**
     * Decode a base62 string back to its numeric ID.
     *
     * @param code base62-encoded string
     * @return the decoded long value
     * @throws IllegalArgumentException if code contains invalid characters
     */
    public static long decode(String code) {
        if (code == null || code.isEmpty()) {
            throw new IllegalArgumentException("Code must not be null or empty");
        }

        long value = 0;
        for (int i = 0; i < code.length(); i++) {
            char c = code.charAt(i);
            int index = ALPHABET.indexOf(c);
            if (index == -1) {
                throw new IllegalArgumentException(
                    "Invalid base62 character '" + c + "' at position " + i + " in code: " + code);
            }
            value = value * BASE + index;
        }
        return value;
    }
}