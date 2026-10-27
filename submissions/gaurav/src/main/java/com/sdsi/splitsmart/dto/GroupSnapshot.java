package com.sdsi.splitsmart.dto;

import com.sdsi.splitsmart.model.Balance;
import com.sdsi.splitsmart.model.Settlement;

import java.util.List;

/**
 * Full group snapshot returned by every API call.
 */
public record GroupSnapshot(
        List<Balance> balances,
        List<Settlement> settlements
) {}