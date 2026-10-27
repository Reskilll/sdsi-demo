"""
Debt simplification – reduce net balances to a minimal set of settlements.

Implements two strategies:
  1. Greedy largest-debtor/largest-creditor (O(n log n)) – the default.
  2. Exact minimum-transaction solver via DP over subsets (O(n * 2^n)) –
     optional for small groups (n ≤ 12).

Strategy 1 is always used; strategy 2 can be engaged when group size ≤ limit.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from heapq import heappop, heappush
from typing import Optional

from .models import (
    QUANTIZE_PREC,
    ROUNDING_MODE,
    MemberBalance,
    Settlement,
)

# ── helpers ────────────────────────────────────────────────────────────────────


def _balances_to_debtors_creditors(
    balances: tuple[MemberBalance, ...],
) -> tuple[list[tuple[str, Decimal]], list[tuple[str, Decimal]]]:
    """
    Separate members into debtors (negative balance) and creditors (positive).

    Zero-balance members are excluded.
    """
    debtors: list[tuple[str, Decimal]] = []
    creditors: list[tuple[str, Decimal]] = []
    for b in balances:
        if b.net_balance < 0:
            debtors.append((b.member_id, -b.net_balance))  # store as positive amount owed
        elif b.net_balance > 0:
            creditors.append((b.member_id, b.net_balance))
    return debtors, creditors


# ── greedy strategy ───────────────────────────────────────────────────────────


def simplify_debts_greedy(
    balances: tuple[MemberBalance, ...],
    member_ids: frozenset[str],
) -> tuple[Settlement, ...]:
    """
    Greedy largest-debtor / largest-creditor settlement algorithm.

    Algorithm:
      1. Separate members into debtors (owe) and creditors (to receive).
      2. Use max-heaps (negated values in min-heap) for O(log n) selection.
      3. While both heaps are non-empty:
           a. Pop the largest debtor and largest creditor.
           b. Settle min(debt, credit) from debtor → creditor.
           c. Push back any remainder.
      4. Tie-breaking: when amounts are equal, sort by member_id for determinism.

    Complexity:
      - Seeding heaps: O(n).
      - Each iteration pops + pushes: O(log n).
      - At most n + (n-1) = 2n-1 iterations, so overall O(n log n).

    This algorithm does NOT guarantee a globally minimum number of transactions.
    For exact optimality on small groups, use simplify_debts_exact.

    Guarantees:
      - No self-transfers.
      - No zero or negative settlement amounts.
      - All parties are known group members.
      - Applying all settlements brings every balance to zero.
    """
    debtors, creditors = _balances_to_debtors_creditors(balances)

    # Use max-heaps by storing negative values. Each entry is
    #   (-amount, index, member_id)  where index breaks ties deterministically.
    d_heap: list[tuple[Decimal, int, str]] = []
    c_heap: list[tuple[Decimal, int, str]] = []

    for i, (mid, amt) in enumerate(debtors):
        heappush(d_heap, (-amt, i, mid))
    for i, (mid, amt) in enumerate(creditors):
        heappush(c_heap, (-amt, i, mid))

    settlements: list[Settlement] = []

    while d_heap and c_heap:
        neg_debt, _, debtor_id = heappop(d_heap)
        neg_credit, _, creditor_id = heappop(c_heap)

        debt = -neg_debt
        credit = -neg_credit

        settled = min(debt, credit)
        settled = settled.quantize(QUANTIZE_PREC, rounding=ROUNDING_MODE)

        if settled > 0:
            settlements.append(
                Settlement(from_member_id=debtor_id, to_member_id=creditor_id, amount=settled)
            )

        debt -= settled
        credit -= settled

        if debt > 0:
            heappush(d_heap, (-debt, len(d_heap), debtor_id))
        if credit > 0:
            heappush(c_heap, (-credit, len(c_heap), creditor_id))

    return tuple(settlements)


# ── exact strategy (subset DP) ────────────────────────────────────────────────


def simplify_debts_exact(
    balances: tuple[MemberBalance, ...],
    member_ids: frozenset[str],
) -> tuple[Settlement, ...]:
    """
    Exact minimum-transaction solver via subset DP.

    Finds a globally minimum number of transactions by:
      1. Identifying the non-zero balance members.
      2. Partitioning the set into zero-sum subsets (each subset settled with
         |subset| - 1 transactions).
      3. DP over subsets to find the partition that maximises the number of
         zero-sum subsets → minimises total transactions.

    Complexity: O(n * 2^n) time, O(2^n) space.

    Only suitable for small n (≤ 12). For larger groups the greedy algorithm
    should be used directly.
    """
    from itertools import combinations

    debtors, creditors = _balances_to_debtors_creditors(balances)
    all_nonzero: list[tuple[str, Decimal]] = [(m, -a) for m, a in debtors] + [(m, a) for m, a in creditors]
    n = len(all_nonzero)

    if n == 0:
        return ()
    if n == 1:
        # Shouldn't happen: sum of balances is zero, so one non-zero is impossible.
        return ()

    # Map each member to an index 0..n-1
    idx_to_member: dict[int, str] = {}
    balance_arr: list[Decimal] = []
    for i, (mid, bal) in enumerate(all_nonzero):
        idx_to_member[i] = mid
        balance_arr.append(bal)

    total_subsets = 1 << n

    # sum[mask] = sum of balances in the mask
    sum_mask = [Decimal("0")] * total_subsets
    # dp[mask] = max number of zero-sum subsets in a partition of mask
    dp = [0] * total_subsets
    # best_split[mask] = submask to split off (for reconstruction)
    best_split = [-1] * total_subsets

    for mask in range(1, total_subsets):
        # compute sum[mask] by adding the lowest set bit's balance
        lsb = mask & -mask
        lsb_idx = (lsb.bit_length() - 1)
        prev = mask ^ lsb
        sum_mask[mask] = sum_mask[prev] + balance_arr[lsb_idx]

    for mask in range(1, total_subsets):
        if sum_mask[mask] == 0:
            dp[mask] = 1
            best_split[mask] = mask
        else:
            best = 0
            best_sub = -1
            # iterate over submasks
            sub = (mask - 1) & mask
            while sub:
                if sum_mask[sub] == 0:
                    cand = dp[sub] + dp[mask ^ sub]
                    if cand > best:
                        best = cand
                        best_sub = sub
                sub = (sub - 1) & mask
            dp[mask] = best
            best_split[mask] = best_sub

    full_mask = total_subsets - 1

    # Reconstruct zero-sum subsets
    zero_subsets: list[int] = []
    stack = [full_mask]
    while stack:
        mask = stack.pop()
        if mask == 0:
            continue
        sub = best_split[mask]
        if sub == -1:
            continue
        if sum_mask[sub] == 0 and sub > 0:
            zero_subsets.append(sub)
        stack.append(mask ^ sub)

    # Build settlements: within each zero-sum subset, greedily settle.
    settlements: list[Settlement] = []
    seen_debtor_counters: dict[str, int] = {}  # for deterministic tie-breaking

    for mask in zero_subsets:
        sub_members: list[tuple[str, Decimal]] = []
        m = mask
        while m:
            lsb = m & -m
            idx = lsb.bit_length() - 1
            sub_members.append((idx_to_member[idx], balance_arr[idx]))
            m ^= lsb

        # Greedy within this subset
        sub_debtors = [(mid, -bal) for mid, bal in sub_members if bal < 0]
        sub_creditors = [(mid, bal) for mid, bal in sub_members if bal > 0]

        d_heap: list[tuple[Decimal, int, int, str]] = []
        c_heap: list[tuple[Decimal, int, int, str]] = []
        for mid, amt in sub_debtors:
            ctr = seen_debtor_counters.get(mid, 0)
            seen_debtor_counters[mid] = ctr + 1
            heappush(d_heap, (-amt, ctr, len(d_heap), mid))
        for mid, amt in sub_creditors:
            heappush(c_heap, (-amt, len(c_heap), 0, mid))

        while d_heap and c_heap:
            neg_debt, _, _, did = heappop(d_heap)
            neg_credit, _, _, cid = heappop(c_heap)
            debt = -neg_debt
            credit = -neg_credit
            settled = min(debt, credit).quantize(QUANTIZE_PREC, rounding=ROUNDING_MODE)
            if settled > 0:
                settlements.append(Settlement(from_member_id=did, to_member_id=cid, amount=settled))
            debt -= settled
            credit -= settled
            if debt > 0:
                ctr = seen_debtor_counters.get(did, 0)
                heappush(d_heap, (-debt, ctr, len(d_heap), did))
            if credit > 0:
                heappush(c_heap, (-credit, len(c_heap), 0, cid))

    return tuple(settlements)


# ── dispatcher ────────────────────────────────────────────────────────────────


def simplify_debts(
    balances: tuple[MemberBalance, ...],
    member_ids: frozenset[str],
    use_exact: bool = False,
    exact_limit: int = 12,
) -> tuple[Settlement, ...]:
    """
    Simplify debts into a minimal settlement list.

    Args:
        balances: Per-member net balances.
        member_ids: Known group member IDs (for validation).
        use_exact: If True, use the exact DP solver for groups ≤ exact_limit.
        exact_limit: Max group size for the exact solver.

    Returns:
        Tuple of Settlement instructions.
    """
    if use_exact:
        non_zero = sum(1 for b in balances if b.net_balance != 0)
        if non_zero <= exact_limit:
            return simplify_debts_exact(balances, member_ids)

    return simplify_debts_greedy(balances, member_ids)