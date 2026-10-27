"""Tests for expense_splitter. Run with: python -m pytest -q"""

from decimal import Decimal

import pytest

from expense_splitter import (
    Splitter, ValidationError, compute_shares, format_money, process, to_paise,
)


# --- money helpers ---------------------------------------------------------- #
def test_to_paise_formats():
    assert to_paise(1000) == 100000
    assert to_paise("12.34") == 1234
    assert to_paise("₹1,000.50") == 100050
    assert to_paise(Decimal("0.10")) == 10


def test_to_paise_rejects_bad():
    for bad in ["abc", "", "1.2.3", float("inf"), True, None]:
        with pytest.raises(ValidationError):
            to_paise(bad)


def test_format_money():
    assert format_money(1234) == "₹12.34"
    assert format_money(-500) == "-₹5.00"
    assert format_money(0) == "₹0.00"


# --- splits ---------------------------------------------------------------- #
def test_equal_split_with_remainder():
    # 1000 paise across 3 -> 334, 333, 333 and sums exactly
    shares = compute_shares(1000, {"type": "equal",
                                   "members": ["a", "b", "c"]}, ["a", "b", "c"])
    assert set(shares) == {"a", "b", "c"}
    assert sum(shares.values()) == 1000
    assert sorted(shares.values()) == [333, 333, 334]


def test_exact_split():
    shares = compute_shares(1000, {"type": "exact",
                                   "amounts": {"a": 600, "b": 400}}, ["a", "b"])
    assert shares == {"a": 600, "b": 400}


def test_exact_split_mismatch():
    with pytest.raises(ValidationError, match="sum to"):
        compute_shares(1000, {"type": "exact", "amounts": {"a": 600}}, ["a", "b"])


def test_percentage_split():
    shares = compute_shares(1000, {"type": "percentage",
                                   "percentages": {"a": 33.33, "b": 66.67}},
                            ["a", "b"])
    assert sum(shares.values()) == 1000


def test_percentage_sum_not_100():
    with pytest.raises(ValidationError, match="sum to"):
        compute_shares(1000, {"type": "percentage",
                              "percentages": {"a": 50, "b": 40}}, ["a", "b"])


def test_unknown_split_type():
    with pytest.raises(ValidationError, match="unknown split type"):
        compute_shares(1000, {"type": "bogus"}, ["a"])


def test_unknown_member():
    with pytest.raises(ValidationError, match="unknown member"):
        compute_shares(1000, {"type": "equal", "members": ["a", "z"]}, ["a", "b"])


# --- splitter --------------------------------------------------------------- #
def test_balances_and_settlements():
    s = Splitter(["a", "b", "c"])
    s.add_expense("a", 300, {"type": "equal", "members": ["a", "b", "c"]})
    b = s.balances()
    assert b["a"] == 200 and b["b"] == -100 and b["c"] == -100
    st = s.settlements()
    assert set((f, t) for f, t, _ in st) == {("b", "a"), ("c", "a")}
    assert sum(p for _, _, p in st) == 200


def test_settlement_count_within_n_minus_1():
    s = Splitter(["a", "b", "c", "d"])
    s.add_expense("a", 400, {"type": "equal"})
    assert len(s.settlements()) <= 3
    assert sum(p for _, _, p in s.settlements()) == 300


def test_no_settlements_when_square():
    s = Splitter(["a", "b"])
    s.add_expense("a", 100, {"type": "equal"})
    s.add_expense("b", 100, {"type": "equal"})
    assert s.settlements() == []


def test_payer_must_be_member():
    s = Splitter(["a", "b"])
    with pytest.raises(ValidationError, match="not a group member"):
        s.add_expense("z", 100, {"type": "equal"})


def test_zero_or_negative_amount_rejected():
    s = Splitter(["a", "b"])
    with pytest.raises(ValidationError):
        s.add_expense("a", 0, {"type": "equal"})
    with pytest.raises(ValidationError):
        s.add_expense("a", -50, {"type": "equal"})


# --- JSON processing -------------------------------------------------------- #
def test_process_batch():
    payload = {
        "members": ["a", "b"],
        "expenses": [
            {"payer": "a", "amount": 200, "split": {"type": "equal"}},
            {"payer": "b", "amount": 100, "split": {"type": "equal"}},
        ],
    }
    out = process(payload)
    assert out["total_expenses"] == "₹300.00"
    assert out["settlements"][0]["from"] == "b"
    assert out["settlements"][0]["amount"] == "₹50.00"


def test_process_single_expense_object():
    out = process({"members": ["a", "b"],
                   "expenses": {"payer": "a", "amount": 200,
                                "split": {"type": "equal"}}})
    assert out["total_expenses"] == "₹200.00"


def test_process_bad_members():
    with pytest.raises(ValidationError, match="members"):
        process({"members": [], "expenses": []})
