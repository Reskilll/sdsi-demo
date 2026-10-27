package com.sdsi.splitter.model;

import java.util.Locale;

public enum SplitType {
    EQUAL,
    EXACT,
    PERCENTAGE;

    /** Case-insensitive; accepts "percent" as an alias. Returns null for anything else. */
    public static SplitType parse(String raw) {
        if (raw == null) {
            return null;
        }
        return switch (raw.strip().toLowerCase(Locale.ROOT)) {
            case "equal" -> EQUAL;
            case "exact" -> EXACT;
            case "percentage", "percent" -> PERCENTAGE;
            default -> null;
        };
    }
}
