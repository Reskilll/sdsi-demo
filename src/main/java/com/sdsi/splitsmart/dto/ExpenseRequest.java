package com.sdsi.splitsmart.dto;

import com.sdsi.splitsmart.model.SplitType;
import java.util.List;
import java.util.Map;

/**
 * JSON shape for submitting a single expense (M1).
 */
public record ExpenseRequest(

        String payer,

        double amount,

        SplitType splitType,

        /** Must be non-empty. Equals don't need values; EXACT/PERCENTAGE do. */
        List<String> members,

        /**
         * For EXACT: member → ₹ share.  For PERCENTAGE: member → % share.
         * Omitted for EQUAL.
         */
        Map<String, Double> shares

) {}