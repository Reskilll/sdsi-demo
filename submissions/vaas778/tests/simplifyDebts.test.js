import { describe, it, expect } from 'vitest';
import { simplifyDebts, verifySettlements } from '../src/logic/simplifyDebts.js';

describe('simplifyDebts', () => {
  it('returns empty settlements when all balances are zero', () => {
    const balances = [
      { memberId: 'a', balance: 0 },
      { memberId: 'b', balance: 0 },
    ];
    expect(simplifyDebts(balances)).toEqual([]);
  });

  it('returns empty settlements for empty balances', () => {
    expect(simplifyDebts([])).toEqual([]);
  });

  it('handles single debtor and single creditor', () => {
    const balances = [
      { memberId: 'aman', balance: 50000 },
      { memberId: 'rahul', balance: -50000 },
    ];
    const settlements = simplifyDebts(balances);
    expect(settlements).toHaveLength(1);
    expect(settlements[0]).toEqual({ from: 'rahul', to: 'aman', amount: 50000 });
    expect(verifySettlements(balances, settlements)).toBe(true);
  });

  it('handles multiple debtors and creditors', () => {
    const balances = [
      { memberId: 'a', balance: 100000 },
      { memberId: 'b', balance: 60000 },
      { memberId: 'c', balance: -70000 },
      { memberId: 'd', balance: -90000 },
    ];
    const settlements = simplifyDebts(balances);
    // Should produce minimal or near-minimal settlements
    expect(settlements.length).toBeGreaterThan(0);
    // Verify all settlements are valid
    for (const s of settlements) {
      expect(s.amount).toBeGreaterThan(0);
      expect(s.from).not.toBe(s.to);
    }
    expect(verifySettlements(balances, settlements)).toBe(true);
  });

  it('never generates self-payments', () => {
    const balances = [
      { memberId: 'a', balance: 50000 },
      { memberId: 'a', balance: -50000 }, // same ID with opposite balances (should not happen but test it)
    ];
    // Only one entry per member in real data — test actual scenario
    const realBalances = [
      { memberId: 'a', balance: 50000 },
      { memberId: 'b', balance: -30000 },
      { memberId: 'c', balance: -20000 },
    ];
    const settlements = simplifyDebts(realBalances);
    for (const s of settlements) {
      expect(s.from).not.toBe(s.to);
    }
    expect(verifySettlements(realBalances, settlements)).toBe(true);
  });

  it('never generates zero-value settlements', () => {
    const balances = [
      { memberId: 'a', balance: 10000 },
      { memberId: 'b', balance: -10000 },
      { memberId: 'c', balance: 0 },
    ];
    const settlements = simplifyDebts(balances);
    for (const s of settlements) {
      expect(s.amount).toBeGreaterThan(0);
    }
    expect(verifySettlements(balances, settlements)).toBe(true);
  });

  it('handles unequal creditors and debtors', () => {
    const balances = [
      { memberId: 'a', balance: 150000 }, // one big creditor
      { memberId: 'b', balance: -50000 },
      { memberId: 'c', balance: -50000 },
      { memberId: 'd', balance: -50000 },
    ];
    const settlements = simplifyDebts(balances);
    expect(settlements.length).toBe(3);
    const totalSettled = settlements.reduce((s, x) => s + x.amount, 0);
    expect(totalSettled).toBe(150000);
    expect(verifySettlements(balances, settlements)).toBe(true);
  });

  it('is deterministic for identical input', () => {
    const balances = [
      { memberId: 'a', balance: 100000 },
      { memberId: 'b', balance: -40000 },
      { memberId: 'c', balance: -30000 },
      { memberId: 'd', balance: -30000 },
    ];
    const s1 = simplifyDebts(balances);
    const s2 = simplifyDebts(balances);
    expect(s1).toEqual(s2);
  });

  it('verification detects invalid settlements', () => {
    const balances = [
      { memberId: 'a', balance: 50000 },
      { memberId: 'b', balance: -50000 },
    ];
    // Create a settlement that only pays 40000 instead of 50000
    const badSettlements = [{ from: 'b', to: 'a', amount: 40000 }];
    expect(verifySettlements(balances, badSettlements)).toBe(false);
  });

  it('complex case: multi-expense trip with 4 people', () => {
    // Simulating the sample data scenario
    const balances = [
      { memberId: 'aman', balance: 160000 },   // paid dinner + owes for groceries, cab
      { memberId: 'rahul', balance: 40000 },    // paid movie + owes dinner, cab
      { memberId: 'priya', balance: -100000 },   // paid groceries + owes dinner, movie
      { memberId: 'neha', balance: -100000 },    // paid cab + owes dinner, groceries
    ];
    const settlements = simplifyDebts(balances);
    for (const s of settlements) {
      expect(s.amount).toBeGreaterThan(0);
      expect(s.from).not.toBe(s.to);
    }
    expect(verifySettlements(balances, settlements)).toBe(true);
  });
});