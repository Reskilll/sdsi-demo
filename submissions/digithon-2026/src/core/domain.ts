/** Second-level suffixes where the registrable domain has three labels (co.uk, com.au, co.in ...). */
const SLD = new Set(['co', 'com', 'org', 'net', 'gov', 'ac', 'edu']);

/** Approximate registrable domain ("shop.example.co.uk" -> "example.co.uk") without a public-suffix list. */
export function registrable(host: string): string {
  const parts = host.toLowerCase().split('.');
  if (parts.length <= 2) return host.toLowerCase();
  const last = parts.at(-1)!, second = parts.at(-2)!;
  return last.length === 2 && SLD.has(second) ? parts.slice(-3).join('.') : parts.slice(-2).join('.');
}
