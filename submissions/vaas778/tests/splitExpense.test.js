import { describe, it, expect } from 'vitest';
import { calculateShares } from '../src/logic/splitExpense.js';

describe('splitExpense — calculateShares', () => {
  describe('Equal split', () => {
    it('divides evenly among three participants', () => {
      const shares = calculateShares({
        amountPaise: 30000, // ₹300.00
        splitType: 'equal',
        participants: ['a', 'b', 'c'],
      });
      expect(shares).toEqual({ a: 10000, b: 10000, c: 10000 });
    });

    it('distributes remainder paise deterministically', () => {
      const shares = calculateShares({
        amountPaise: 100, // ₹1.00 among 3 = 33.33 paise each, 1 remaining
        splitType: 'equal',
        participants: ['c', 'a', 'b'],
      });
      // Sorted alphabetically: a, b, c. First gets the remainder.
      expect(shares.a).toBe(34);
      expect(shares.b).toBe(33);
      expect(shares.c).toBe(33);
      expect(Object.values(shares).reduce((s, v) => s + v, 0)).toBe(100);
    });

    it('handles single participant', () => {
      const shares = calculateShares({
        amountPaise: 50000,
        splitType: 'equal',
        participants: ['x'],
      });
      expect(shares).toEqual({ x: 50000 });
    });

    it('handles zero-remainder split', () => {
      const shares = calculateShares({
        amountPaise: 400,
        splitType: 'equal',
        participants: ['a', 'b'],
      });
      expect(shares).toEqual({ a: 200, b: 200 });
    });

    it('throws on empty participants', () => {
      expect(() =>
        calculateShares({
          amountPaise: 100,
          splitType: 'equal',
          participants: [],
        }),
      ).toThrow('at least one participant');
    });
  });

  describe('Exact split', () => {
    it('assigns exact amounts correctly', () => {
      const shares = calculateShares({
        amountPaise: 85000, // ₹850
        splitType: 'exact',
        participants: ['a', 'b', 'c'],
        exactAmounts: { a: 300, b: 250, c: 300 },
      });
      expect(shares).toEqual({ a: 30000, b: 25000, c: 30000 });
    });

    it('rejects when amounts do not sum to total', () => {
      expect(() =>
        calculateShares({
          amountPaise: 100000,
          splitType: 'exact',
          participants: ['a', 'b'],
          exactAmounts: { a: 400, b: 500 },
        }),
      ).toThrow(/sum to/);
    });

    it('rejects missing amount for a participant', () => {
      expect(() =>
        calculateShares({
          amountPaise: 50000,
          splitType: 'exact',
          participants: ['a', 'b'],
          exactAmounts: { a: 300 },
        }),
      ).toThrow(/Missing exact amount/);
    });

    it('rejects negative amount', () => {
      expect(() =>
        calculateShares({
          amountPaise: 50000,
          splitType: 'exact',
          participants: ['a', 'b'],
          exactAmounts: { a: 600, b: -100 },
        }),
      ).toThrow(/non-negative number/);
    });
  });

  describe('Percentage split', () => {
    it('calculates shares from percentages correctly', () => {
      const shares = calculateShares({
        amountPaise: 50000,
        splitType: 'percentage',
        participants: ['a', 'b', 'c'],
        percentages: { a: 40, b: 40, c: 20 },
      });
      expect(shares.a).toBe(20000);
      expect(shares.b).toBe(20000);
      expect(shares.c).toBe(10000);
    });

    it('handles rounding with largest-remainder method', () => {
      // ₹1.00 split 33/33/34% — total 100 paise
      const shares = calculateShares({
        amountPaise: 100,
        splitType: 'percentage',
        participants: ['a', 'b', 'c'],
        percentages: { a: 33.33, b: 33.33, c: 33.34 },
      });
      const sum = Object.values(shares).reduce((s, v) => s + v, 0);
      expect(sum).toBe(100);
      // c has largest fractional, should get the extra paise
      // 33.34% of 100 = 33.34; 33.33% of 100 = 33.33
      expect(shares.c).toBe(34);
    });

    it('rejects when percentages do not sum to 100', () => {
      expect(() =>
        calculateShares({
          amountPaise: 100000,
          splitType: 'percentage',
          participants: ['a', 'b'],
          percentages: { a: 60, b: 30 },
        }),
      ).toThrow(/sum to/);
    });

    it('rejects percentage > 100', () => {
      expect(() =>
        calculateShares({
          amountPaise: 10000,
          splitType: 'percentage',
          participants: ['a'],
          percentages: { a: 101 },
        }),
      ).toThrow(/between 0 and 100/);
    });

    it('rejects missing percentage', () => {
      expect(() =>
        calculateShares({
          amountPaise: 10000,
          splitType: 'percentage',
          participants: ['a', 'b'],
          percentages: { a: 100 },
        }),
      ).toThrow(/Missing percentage/);
    });

    it('accepts percentages summing to 100 within tolerance', () => {
      const shares = calculateShares({
        amountPaise: 10000,
        splitType: 'percentage',
        participants: ['a', 'b'],
        percentages: { a: 33.3333, b: 66.6667 },
      });
      const sum = Object.values(shares).reduce((s, v) => s + v, 0);
      expect(sum).toBe(10000);
    });
  });

  describe('Unknown split type', () => {
    it('throws on unknown split type', () => {
      expect(() =>
        calculateShares({
          amountPaise: 1000,
          splitType: 'bogus',
          participants: ['a'],
        }),
      ).toThrow('Unknown split type');
    });
  });
});