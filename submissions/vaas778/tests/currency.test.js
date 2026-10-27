import { describe, it, expect } from 'vitest';
import { rupeesToPaise, paiseToRupees, formatSignedBalance, paiseToDecimal } from '../src/utils/currency.js';

describe('Currency utilities', () => {
  describe('rupeesToPaise', () => {
    it('converts whole rupees correctly', () => {
      expect(rupeesToPaise(100)).toBe(10000);
    });
    it('converts fractional rupees correctly', () => {
      expect(rupeesToPaise(99.99)).toBe(9999);
    });
    it('rounds correctly', () => {
      expect(rupeesToPaise(0.995)).toBe(100); // rounds up
    });
    it('throws on non-finite input', () => {
      expect(() => rupeesToPaise(NaN)).toThrow();
      expect(() => rupeesToPaise(Infinity)).toThrow();
    });
  });

  describe('paiseToRupees', () => {
    it('formats paise to rupees display', () => {
      const result = paiseToRupees(150000);
      expect(result).toBe('₹1,500.00');
    });
    it('formats zero', () => {
      expect(paiseToRupees(0)).toBe('₹0.00');
    });
    it('throws on non-integer input', () => {
      expect(() => paiseToRupees(1.5)).toThrow();
    });
  });

  describe('formatSignedBalance', () => {
    it('shows + for positive', () => {
      expect(formatSignedBalance(50000)).toBe('+₹500.00');
    });
    it('shows - for negative', () => {
      expect(formatSignedBalance(-50000)).toBe('-₹500.00');
    });
    it('shows no sign for zero', () => {
      expect(formatSignedBalance(0)).toBe('₹0.00');
    });
  });

  describe('paiseToDecimal', () => {
    it('formats paise as decimal string', () => {
      expect(paiseToDecimal(150000)).toBe('1500.00');
    });
  });
});