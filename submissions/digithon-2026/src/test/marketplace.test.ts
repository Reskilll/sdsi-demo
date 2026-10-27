import test from 'node:test';
import assert from 'node:assert/strict';
import { loadMarketplace, marketplaceSummary, validateCatalogue } from '../core/marketplace.js';
import { PERSONAS } from '../core/events.js';

test('the marketplace catalogue loads and lists every running agent as live', () => {
  const agents = loadMarketplace();
  for (const id of Object.keys(PERSONAS)) assert.equal(agents.find((a) => a.id === id)?.status, 'live', id);
});

test('summary counts add up to the total', () => {
  const s = marketplaceSummary(loadMarketplace());
  assert.equal(Object.values(s.byStatus).reduce((a, b) => a + b, 0), s.total);
  assert.equal(Object.values(s.byCategory).reduce((a, b) => a + b, 0), s.total);
});

test('rejects duplicates and a running agent marked as planned', () => {
  const agents = loadMarketplace();
  assert.throws(() => validateCatalogue({ agents: [...agents, agents[0]] }), /Duplicate/);
  assert.throws(() => validateCatalogue({ agents: agents.map((a) => (a.id === 'deck' ? { ...a, status: 'planned' } : a)) }), /deck/);
});
