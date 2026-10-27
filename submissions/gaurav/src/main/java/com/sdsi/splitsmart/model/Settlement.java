package com.sdsi.splitsmart.model;

/**
 * A single simplified settlement instruction: "from pays to ₹amount".
 */
public record Settlement(
        String from,
        String to,
        double amount
) {}