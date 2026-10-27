export function grade(score: number): string {
  if (score >= 90) return 'A';
  if (score >= 80) return 'B';
  if (score >= 65) return 'C';
  if (score >= 50) return 'D';
  return 'F';
}

export const clamp = (n: number, lo = 0, hi = 100) => Math.max(lo, Math.min(hi, n));

/** Linear score: `good` or better = 100, `poor` or worse = 0. Works for lower-is-better metrics. */
export function scoreBetween(value: number, good: number, poor: number): number {
  if (value <= good) return 100;
  if (value >= poor) return 0;
  return Math.round(100 * (1 - (value - good) / (poor - good)));
}
