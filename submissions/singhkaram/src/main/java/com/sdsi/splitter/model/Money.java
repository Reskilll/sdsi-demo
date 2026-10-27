package com.sdsi.splitter.model;

import java.math.BigDecimal;
import java.math.RoundingMode;

/**
 * Money is stored as a {@code long} count of paise (1 rupee = 100 paise). Integer arithmetic means no
 * floating-point drift: every split adds up to the exact total.
 */
public final class Money {

    /** Upper bound for a single expense: ₹1 crore. Keeps all sums far away from {@code long} overflow. */
    public static final long MAX_PAISE = 1_000_000_000L;

    private Money() {
    }

    /** Converts a validated rupee amount (at most 2 decimals) to paise. */
    public static long toPaise(BigDecimal rupees) {
        return rupees.movePointRight(2).setScale(0, RoundingMode.UNNECESSARY).longValueExact();
    }

    /** Formats paise with Indian digit grouping, e.g. 123456789 -> "12,34,567.89". */
    public static String format(long paise) {
        String sign = paise < 0 ? "-" : "";
        long abs = Math.abs(paise);
        String whole = Long.toString(abs / 100);
        String fraction = String.format("%02d", abs % 100);
        if (whole.length() > 3) {
            String last3 = whole.substring(whole.length() - 3);
            StringBuilder rest = new StringBuilder(whole.substring(0, whole.length() - 3));
            for (int i = rest.length() - 2; i > 0; i -= 2) {
                rest.insert(i, ',');
            }
            whole = rest + "," + last3;
        }
        return sign + whole + "." + fraction;
    }

    /** Plain decimal rupees for machine-readable output, e.g. 12345 -> 123.45. */
    public static BigDecimal toRupees(long paise) {
        return BigDecimal.valueOf(paise, 2);
    }
}
