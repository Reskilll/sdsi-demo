package com.sdsi.splitsmart.dto;

import java.util.List;

/**
 * A batch of expenses to process at once (M4).
 */
public record BatchRequest(
        List<ExpenseRequest> expenses
) {}