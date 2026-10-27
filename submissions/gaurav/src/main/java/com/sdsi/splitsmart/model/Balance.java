package com.sdsi.splitsmart.model;

/**
 * How much each member owes (+ve) or is owed (-ve) across all recorded expenses.
 */
public record Balance(
        String member,
        double netOwed  // positive → owes money; negative → is owed money
) {}