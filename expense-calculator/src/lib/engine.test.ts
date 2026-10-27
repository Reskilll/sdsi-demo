/**
 * Comprehensive test suite for the expense splitting engine.
 *
 * Run: npm test
 */

import { describe, it } from 'node:test';
import * as assert from 'node:assert/strict';

import {
  computeBalances,
  processExpenses,
  simplifyDebts,
  validateBatch,
  validateExpense,
} from './engine';
import type { Expense, ExpenseInput, Member } from './types';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeMembers(count: number): Member[] {
  return Array.from({ length: count }, (_, i) => ({
    id: `m${i + 1}`,
    name: `Member ${i + 1}`,
  }));
}

function round(n: number): number {
  return Math.round(n * 100) / 100;
}

// ---------------------------------------------------------------------------

describe('validateExpense', () => {
  const members = makeMembers(4);

  it('accepts a valid equal split', () => {
    const errors = validateExpense(
      {
        description: 'Test',
        total: 100,
        paidBy: 'm1',
        split: { type: 'equal', shareHolderIds: ['m1', 'm2', 'm3', 'm4'] },
      },
      members,
    );
    assert.equal(errors.length, 0);
  });

  it('accepts a valid exact split', () => {
    const errors = validateExpense(
      {
        description: 'Test',
        total: 100,
        paidBy: 'm1',
        split: {
          type: 'exact',
          shares: { m1: 40, m2: 30, m3: 30 },
        },
      },
      members,
    );
    assert.equal(errors.length, 0);
  });

  it('accepts a valid percentage split', () => {
    const errors = validateExpense(
      {
        description: 'Test',
        total: 200,
        paidBy: 'm2',
        split: {
          type: 'percentage',
          shares: { m1: 50, m2: 25, m3: 25 },
        },
      },
      members,
    );
    assert.equal(errors.length, 0);
  });

  it('rejects payer not in group', () => {
    const errors = validateExpense(
      {
        description: 'Test',
        total: 50,
        paidBy: 'stranger',
        split: { type: 'equal', shareHolderIds: ['m1'] },
      },
      members,
    );
    assert.ok(errors.some((e) => e.field === 'paidBy'));
  });

  it('rejects share-holder not in group', () => {
    const errors = validateExpense(
      {
        description: 'Test',
        total: 50,
        paidBy: 'm1',
        split: { type: 'equal', shareHolderIds: ['m1', 'ghost'] },
      },
      members,
    );
    assert.ok(errors.some((e) => e.field === 'split.shareHolderIds'));
  });

  it('rejects negative total', () => {
    const errors = validateExpense(
      {
        description: 'Test',
        total: -100,
        paidBy: 'm1',
        split: { type: 'equal', shareHolderIds: ['m1'] },
      },
      members,
    );
    assert.ok(errors.some((e) => e.field === 'total'));
  });

  it('rejects zero total', () => {
    const errors = validateExpense(
      {
        description: 'Test',
        total: 0,
        paidBy: 'm1',
        split: { type: 'equal', shareHolderIds: ['m1'] },
      },
      members,
    );
    assert.ok(errors.some((e) => e.field === 'total'));
  });

  it('rejects exact shares not summing to total', () => {
    const errors = validateExpense(
      {
        description: 'Test',
        total: 100,
        paidBy: 'm1',
        split: {
          type: 'exact',
          shares: { m1: 30, m2: 30 },
        },
      },
      members,
    );
    assert.ok(errors.some((e) => e.field === 'split.shares' && e.message.includes('sum')));
  });

  it('rejects percentages not summing to 100', () => {
    const errors = validateExpense(
      {
        description: 'Test',
        total: 100,
        paidBy: 'm1',
        split: {
          type: 'percentage',
          shares: { m1: 40, m2: 30 },
        },
      },
      members,
    );
    assert.ok(errors.some((e) => e.field === 'split.shares' && e.message.includes('100%')));
  });

  it('rejects negative share amount in exact split', () => {
    const errors = validateExpense(
      {
        description: 'Test',
        total: 100,
        paidBy: 'm1',
        split: {
          type: 'exact',
          shares: { m1: 120, m2: -20 },
        },
      },
      members,
    );
    assert.ok(errors.some((e) => e.message.includes('>= 0')));
  });

  it('rejects empty share-holder list (equal)', () => {
    const errors = validateExpense(
      {
        description: 'Test',
        total: 100,
        paidBy: 'm1',
        split: { type: 'equal', shareHolderIds: [] },
      },
      members,
    );
    assert.ok(errors.length > 0);
  });

  it('rejects unknown split type', () => {
    const errors = validateExpense(
      {
        description: 'Test',
        total: 100,
        paidBy: 'm1',
        split: { type: 'invalid' as never, shareHolderIds: ['m1'] },
      },
      members,
    );
    assert.ok(errors.some((e) => e.field === 'split.type'));
  });
});

// ---------------------------------------------------------------------------

describe('validateBatch', () => {
  it('accepts valid batch input', () => {
    const input: ExpenseInput = {
      members: makeMembers(3),
      expenses: [
        {
          description: 'Dinner',
          total: 300,
          paidBy: 'm1',
          split: { type: 'equal', shareHolderIds: ['m1', 'm2', 'm3'] },
        },
      ],
    };
    const errors = validateBatch(input);
    assert.equal(errors.length, 0);
  });

  it('rejects empty members', () => {
    const errors = validateBatch({ members: [], expenses: [] });
    assert.ok(errors.length > 0);
  });

  it('rejects empty expenses', () => {
    const errors = validateBatch({ members: makeMembers(3), expenses: [] });
    assert.ok(errors.length > 0);
  });

  it('rejects duplicate member IDs', () => {
    const errors = validateBatch({
      members: [
        { id: 'dup', name: 'One' },
        { id: 'dup', name: 'Two' },
      ],
      expenses: [
        {
          description: 'X',
          total: 10,
          paidBy: 'dup',
          split: { type: 'equal', shareHolderIds: ['dup'] },
        },
      ],
    });
    assert.ok(errors.some((e) => e.message.includes('Duplicate')));
  });

  it('returns multiple errors for multiple bad expenses', () => {
    const input: ExpenseInput = {
      members: makeMembers(3),
      expenses: [
        {
          description: 'E1',
          total: -5,
          paidBy: 'm1',
          split: { type: 'equal', shareHolderIds: ['m1'] },
        },
        {
          description: 'E2',
          total: 100,
          paidBy: 'ghost',
          split: { type: 'equal', shareHolderIds: ['m1'] },
        },
      ],
    };
    const errors = validateBatch(input);
    assert.ok(errors.length >= 2);
  });
});

// ---------------------------------------------------------------------------

describe('computeBalances', () => {
  const members = makeMembers(3);

  it('simple equal split: everyone owes net zero when they pay their share', () => {
    const expenses: Expense[] = [
      {
        id: 'e1',
        description: 'Equal Dinner',
        total: 300,
        paidBy: 'm1',
        split: { type: 'equal', shareHolderIds: ['m1', 'm2', 'm3'] },
      },
    ];
    const balances = computeBalances(expenses, members);
    // m1 paid 300, owes 100 → net +200
    // m2 paid 0, owes 100 → net -100
    // m3 paid 0, owes 100 → net -100
    const m1 = balances.find((b) => b.memberId === 'm1')!;
    const m2 = balances.find((b) => b.memberId === 'm2')!;
    const m3 = balances.find((b) => b.memberId === 'm3')!;

    assert.equal(m1.paid, 300);
    assert.equal(m1.owed, 100);
    assert.equal(m1.net, 200);

    assert.equal(m2.paid, 0);
    assert.equal(m2.owed, 100);
    assert.equal(m2.net, -100);

    assert.equal(m3.paid, 0);
    assert.equal(m3.owed, 100);
    assert.equal(m3.net, -100);
  });

  it('exact split with correct amounts', () => {
    const expenses: Expense[] = [
      {
        id: 'e1',
        description: 'Exact',
        total: 500,
        paidBy: 'm2',
        split: {
          type: 'exact',
          shares: { m1: 200, m2: 200, m3: 100 },
        },
      },
    ];
    const balances = computeBalances(expenses, members);
    const m2 = balances.find((b) => b.memberId === 'm2')!;
    assert.equal(m2.paid, 500);
    assert.equal(m2.owed, 200);
    assert.equal(m2.net, 300);
  });

  it('percentage split', () => {
    const expenses: Expense[] = [
      {
        id: 'e1',
        description: 'Pct',
        total: 1000,
        paidBy: 'm3',
        split: {
          type: 'percentage',
          shares: { m1: 10, m2: 30, m3: 60 },
        },
      },
    ];
    const balances = computeBalances(expenses, members);
    const m1 = balances.find((b) => b.memberId === 'm1')!;
    assert.equal(m1.owed, 100); // 10% of 1000
    const m2 = balances.find((b) => b.memberId === 'm2')!;
    assert.equal(m2.owed, 300); // 30%
  });

  it('total balance sum should be zero (conservation of money)', () => {
    const expenses: Expense[] = [
      {
        id: 'e1',
        description: 'A',
        total: 100,
        paidBy: 'm1',
        split: { type: 'equal', shareHolderIds: ['m1', 'm2'] },
      },
      {
        id: 'e2',
        description: 'B',
        total: 200,
        paidBy: 'm2',
        split: {
          type: 'exact',
          shares: { m1: 50, m2: 100, m3: 50 },
        },
      },
      {
        id: 'e3',
        description: 'C',
        total: 300,
        paidBy: 'm3',
        split: {
          type: 'percentage',
          shares: { m1: 33.33, m2: 33.33, m3: 33.34 },
        },
      },
    ];
    const balances = computeBalances(expenses, members);
    const totalNet = round(balances.reduce((s, b) => s + b.net, 0));
    assert.equal(totalNet, 0);
  });

  it('handles members with zero expenses', () => {
    const members4 = makeMembers(4);
    const expenses: Expense[] = [
      {
        id: 'e1',
        description: 'Only three',
        total: 300,
        paidBy: 'm1',
        split: { type: 'equal', shareHolderIds: ['m1', 'm2', 'm3'] },
      },
    ];
    const balances = computeBalances(expenses, members4);
    const m4 = balances.find((b) => b.memberId === 'm4')!;
    assert.equal(m4.paid, 0);
    assert.equal(m4.owed, 0);
    assert.equal(m4.net, 0);
  });
});

// ---------------------------------------------------------------------------

describe('simplifyDebts', () => {
  it('returns empty for zero balances', () => {
    const settlements = simplifyDebts([
      { memberId: 'a', name: 'A', paid: 100, owed: 100, net: 0 },
      { memberId: 'b', name: 'B', paid: 50, owed: 50, net: 0 },
    ]);
    assert.equal(settlements.length, 0);
  });

  it('single creditor, single debtor', () => {
    const settlements = simplifyDebts([
      { memberId: 'a', name: 'A', paid: 0, owed: 0, net: 100 },
      { memberId: 'b', name: 'B', paid: 0, owed: 0, net: -100 },
    ]);
    assert.equal(settlements.length, 1);
    assert.equal(settlements[0].from, 'b');
    assert.equal(settlements[0].to, 'a');
    assert.equal(settlements[0].amount, 100);
  });

  it('minimizes settlements for multi-party', () => {
    // A is owed 80; B owes 50; C owes 30
    // Optimal: B pays A 50, C pays A 30 → 2 settlements
    const settlements = simplifyDebts([
      { memberId: 'a', name: 'A', paid: 0, owed: 0, net: 80 },
      { memberId: 'b', name: 'B', paid: 0, owed: 0, net: -50 },
      { memberId: 'c', name: 'C', paid: 0, owed: 0, net: -30 },
    ]);
    // B owes 50 → pays A 50; C owes 30 → pays A 30 = 2 settlements
    assert.equal(settlements.length, 2);
    // Total settled should equal all debts
    const totalSettled = round(settlements.reduce((s, st) => s + st.amount, 0));
    assert.equal(totalSettled, 50 + 30);
  });

  it('handles complex multi-party with offsetting balances', () => {
    // A: +200, B: -150, C: +50, D: -100
    // Optimal: B→A 150, D→A 50, D→C 50 = 3 settlements
    const settlements = simplifyDebts([
      { memberId: 'a', name: 'A', paid: 0, owed: 0, net: 200 },
      { memberId: 'b', name: 'B', paid: 0, owed: 0, net: -150 },
      { memberId: 'c', name: 'C', paid: 0, owed: 0, net: 50 },
      { memberId: 'd', name: 'D', paid: 0, owed: 0, net: -100 },
    ]);
    // Greedy: largest creditor A(200), largest debtor B(-150)
    // B pays A 150, then D(-100) pays A 50, then D(-50) pays C 50
    assert.equal(settlements.length, 3);
    // Verify total settled
    const totalSettled = round(settlements.reduce((s, st) => s + st.amount, 0));
    assert.equal(totalSettled, 150 + 50 + 50);
  });

  it('settlements reconstruct original balances', () => {
    const balances = [
      { memberId: 'a', name: 'A', paid: 500, owed: 300, net: 200 },
      { memberId: 'b', name: 'B', paid: 400, owed: 550, net: -150 },
      { memberId: 'c', name: 'C', paid: 200, owed: 250, net: -50 },
    ];
    const settlements = simplifyDebts(balances);

    // Reconstruct net from settlements
    const net = new Map<string, number>();
    for (const b of balances) net.set(b.memberId, 0);
    for (const s of settlements) {
      net.set(s.from, round((net.get(s.from) ?? 0) - s.amount));
      net.set(s.to, round((net.get(s.to) ?? 0) + s.amount));
    }
    for (const b of balances) {
      assert.ok(
        Math.abs((net.get(b.memberId) ?? 0) - b.net) < 0.01,
        `Mismatch for ${b.memberId}: expected ${b.net}, got ${net.get(b.memberId)}`,
      );
    }
  });

  it('handles floating-point edge cases', () => {
    // These values are chosen to test rounding: 10/3 = 3.333...
    const settlements = simplifyDebts([
      { memberId: 'a', name: 'A', paid: 0, owed: 0, net: 3.33 },
      { memberId: 'b', name: 'B', paid: 0, owed: 0, net: 3.33 },
      { memberId: 'c', name: 'C', paid: 0, owed: 0, net: -6.66 },
    ]);
    assert.ok(settlements.length > 0);
    // Sum of settlements should be close to 6.66
    const total = round(settlements.reduce((s, st) => s + st.amount, 0));
    assert.ok(Math.abs(total - 6.66) < 0.02);
  });
});

// ---------------------------------------------------------------------------

describe('processExpenses (end-to-end)', () => {
  it('processes sample data correctly', () => {
    const input: ExpenseInput = {
      members: [
        { id: 'alice', name: 'Alice' },
        { id: 'bob', name: 'Bob' },
        { id: 'charlie', name: 'Charlie' },
        { id: 'diana', name: 'Diana' },
      ],
      expenses: [
        {
          description: 'Dinner',
          total: 4000,
          paidBy: 'alice',
          split: {
            type: 'equal',
            shareHolderIds: ['alice', 'bob', 'charlie', 'diana'],
          },
        },
        {
          description: 'Taxi',
          total: 600,
          paidBy: 'bob',
          split: {
            type: 'exact',
            shares: { alice: 200, bob: 100, charlie: 300 },
          },
        },
        {
          description: 'Concert',
          total: 3000,
          paidBy: 'charlie',
          split: {
            type: 'percentage',
            shares: { alice: 40, bob: 30, charlie: 30 },
          },
        },
        {
          description: 'Snacks',
          total: 500,
          paidBy: 'diana',
          split: {
            type: 'equal',
            shareHolderIds: ['alice', 'bob', 'charlie', 'diana'],
          },
        },
      ],
    };

    const { result, errors } = processExpenses(input);
    assert.equal(errors.length, 0);
    assert.ok(result !== null);

    // Conservation of money: net sum should be 0
    const netSum = round(result!.balances.reduce((s, b) => s + b.net, 0));
    assert.equal(netSum, 0);

    // Each settlement should resolve actual debts
    assert.ok(result!.settlements.length > 0);

    // Every settlement amount should be positive
    for (const s of result!.settlements) {
      assert.ok(s.amount > 0, `Settlement amount should be positive, got ${s.amount}`);
    }
  });

  it('returns errors for invalid input', () => {
    const input: ExpenseInput = {
      members: [
        { id: 'x', name: 'X' },
        { id: 'x', name: 'X duplicate' }, // duplicate!
      ],
      expenses: [
        {
          description: 'E',
          total: -10,
          paidBy: 'x',
          split: { type: 'equal', shareHolderIds: ['x'] },
        },
      ],
    };
    const { result, errors } = processExpenses(input);
    assert.equal(result, null);
    assert.ok(errors.length >= 2, `Expected at least 2 errors, got ${errors.length}`);
  });
});

// ---------------------------------------------------------------------------

describe('edge cases', () => {
  it('single member paying for themselves', () => {
    const input: ExpenseInput = {
      members: [{ id: 'solo', name: 'Solo' }],
      expenses: [
        {
          description: 'Self-spend',
          total: 100,
          paidBy: 'solo',
          split: { type: 'equal', shareHolderIds: ['solo'] },
        },
      ],
    };
    const { result, errors } = processExpenses(input);
    assert.equal(errors.length, 0);
    // Solo paid 100 and owes 100 → net 0, no settlements
    assert.equal(result!.settlements.length, 0);
    assert.equal(result!.balances[0].net, 0);
  });

  it('large number rounding: 1 cent difference', () => {
    // 10 split among 3: each pays 3.33, but 3*3.33 = 9.99
    // Engine should distribute the extra 0.01
    const input: ExpenseInput = {
      members: makeMembers(3),
      expenses: [
        {
          description: 'Rounding test',
          total: 10,
          paidBy: 'm1',
          split: { type: 'equal', shareHolderIds: ['m1', 'm2', 'm3'] },
        },
      ],
    };
    const { result, errors } = processExpenses(input);
    assert.equal(errors.length, 0);
    const totalOwed = round(result!.balances.reduce((s, b) => s + b.owed, 0));
    // The total owed should be very close to 10
    assert.ok(
      Math.abs(totalOwed - 10) < 0.03,
      `Total owed ${totalOwed} should be ~10`,
    );
  });

  it('percentage with non-integer values (33.33 + 33.33 + 33.34)', () => {
    const input: ExpenseInput = {
      members: makeMembers(3),
      expenses: [
        {
          description: 'Slightly off',
          total: 300,
          paidBy: 'm1',
          split: {
            type: 'percentage',
            shares: { m1: 33.33, m2: 33.33, m3: 33.34 },
          },
        },
      ],
    };
    const { result, errors } = processExpenses(input);
    assert.equal(errors.length, 0);
    const netSum = round(result!.balances.reduce((s, b) => s + b.net, 0));
    assert.equal(netSum, 0);
  });

  it('all members have zero net if everyone pays exactly their share', () => {
    const input: ExpenseInput = {
      members: makeMembers(3),
      expenses: [
        {
          description: 'A pays 300, all share equally',
          total: 300,
          paidBy: 'm1',
          split: { type: 'equal', shareHolderIds: ['m1', 'm2', 'm3'] },
        },
        {
          description: 'B pays 300, all share equally',
          total: 300,
          paidBy: 'm2',
          split: { type: 'equal', shareHolderIds: ['m1', 'm2', 'm3'] },
        },
        {
          description: 'C pays 300, all share equally',
          total: 300,
          paidBy: 'm3',
          split: { type: 'equal', shareHolderIds: ['m1', 'm2', 'm3'] },
        },
      ],
    };
    const { result, errors } = processExpenses(input);
    assert.equal(errors.length, 0);
    for (const b of result!.balances) {
      assert.equal(b.net, 0);
    }
    // Zero settlements because everyone is even
    assert.equal(result!.settlements.length, 0);
  });

  it('decimal total with exact split', () => {
    const input: ExpenseInput = {
      members: makeMembers(2),
      expenses: [
        {
          description: 'Decimal',
          total: 99.99,
          paidBy: 'm1',
          split: { type: 'exact', shares: { m1: 50, m2: 49.99 } },
        },
      ],
    };
    const { result, errors } = processExpenses(input);
    assert.equal(errors.length, 0);
  });
});