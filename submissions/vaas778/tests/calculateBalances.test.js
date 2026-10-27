import { describe, it, expect } from 'vitest';
import { calculateBalances, verifyBalancesZero } from '../src/logic/calculateBalances.js';

const members = [
  { id: 'aman', name: 'Aman' },
  { id: 'rahul', name: 'Rahul' },
  { id: 'priya', name: 'Priya' },
  { id: 'neha', name: 'Neha' },
];

describe('calculateBalances', () => {
  it('calculates correct balances for a single equal expense', () => {
    const expenses = [
      {
        paidBy: 'aman',
        amountPaise: 240000, // ₹2400
        shares: { aman: 60000, rahul: 60000, priya: 60000, neha: 60000 },
      },
    ];
    const balances = calculateBalances(members, expenses);
    // Aman paid 2400, owes 600 → net +1800 (owes to receive)
    // Others owe 600 each → net -600
    const aman = balances.find((b) => b.memberId === 'aman');
    expect(aman.paid).toBe(240000);
    expect(aman.owed).toBe(60000);
    expect(aman.balance).toBe(180000);

    const rahul = balances.find((b) => b.memberId === 'rahul');
    expect(rahul.paid).toBe(0);
    expect(rahul.owed).toBe(60000);
    expect(rahul.balance).toBe(-60000);
  });

  it('returns zero for all members with no expenses', () => {
    const balances = calculateBalances(members, []);
    for (const b of balances) {
      expect(b.balance).toBe(0);
      expect(b.paid).toBe(0);
      expect(b.owed).toBe(0);
    }
  });

  it('aggregates across multiple expenses', () => {
    const expenses = [
      {
        paidBy: 'aman',
        amountPaise: 100000,
        shares: { aman: 50000, rahul: 50000 },
      },
      {
        paidBy: 'rahul',
        amountPaise: 60000,
        shares: { aman: 30000, rahul: 30000 },
      },
    ];
    const balances = calculateBalances(members, expenses);
    const aman = balances.find((b) => b.memberId === 'aman');
    // Aman paid 1000, owes 500 + 300 = 800 → net +200
    expect(aman.paid).toBe(100000);
    expect(aman.owed).toBe(80000);
    expect(aman.balance).toBe(20000);

    const rahul = balances.find((b) => b.memberId === 'rahul');
    // Rahul paid 600, owes 500 + 300 = 800 → net -200
    expect(rahul.paid).toBe(60000);
    expect(rahul.owed).toBe(80000);
    expect(rahul.balance).toBe(-20000);
  });

  it('handles payer excluded from split', () => {
    const expenses = [
      {
        paidBy: 'aman',
        amountPaise: 100000,
        shares: { rahul: 100000 },
      },
    ];
    const balances = calculateBalances(members, expenses);
    const aman = balances.find((b) => b.memberId === 'aman');
    expect(aman.paid).toBe(100000);
    expect(aman.owed).toBe(0);
    expect(aman.balance).toBe(100000);

    const rahul = balances.find((b) => b.memberId === 'rahul');
    expect(rahul.paid).toBe(0);
    expect(rahul.owed).toBe(100000);
    expect(rahul.balance).toBe(-100000);
  });

  it('handles members with no participation', () => {
    const expenses = [
      {
        paidBy: 'aman',
        amountPaise: 100000,
        shares: { rahul: 100000 },
      },
    ];
    const balances = calculateBalances(members, expenses);
    const priya = balances.find((b) => b.memberId === 'priya');
    expect(priya.balance).toBe(0);
    expect(priya.paid).toBe(0);
    expect(priya.owed).toBe(0);
  });

  it('total balances sum to zero', () => {
    const expenses = [
      {
        paidBy: 'aman',
        amountPaise: 100000,
        shares: { aman: 30000, rahul: 30000, priya: 40000 },
      },
      {
        paidBy: 'priya',
        amountPaise: 50000,
        shares: { aman: 25000, neha: 25000 },
      },
    ];
    const balances = calculateBalances(members, expenses);
    const total = balances.reduce((s, b) => s + b.balance, 0);
    expect(total).toBe(0);
    expect(verifyBalancesZero(balances)).toBe(true);
  });
});