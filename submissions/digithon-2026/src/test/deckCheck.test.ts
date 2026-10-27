import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { checkDeck, slideTexts } from '../core/deckCheck.js';

const analysis = {
  audit: { overall: 60, grade: 'D', categories: [{ category: 'speed', score: 37 }, { category: 'a11y', score: 45 }], topFixes: [{ category: 'speed', title: 'Main content takes 16.9s' }] },
  stack: { technologies: [{ name: 'React' }, { name: 'Akamai' }] },
  team: { orgScore: 91 },
  research: { items: [{ title: 'Weak sales in South India', angle: 'Regional languages' }] },
};

test('a deck is checked against the analysis: what it covers, on which slide, and what to add', () => {
  const r = checkDeck(['Your site scores 60/100 today', 'Speed: pages load slowly', 'We use React and Akamai', 'Our team and the price'], analysis, 'mine.pptx');
  const by = (item: string) => r.checks.find((c) => c.item.startsWith(item))!;
  assert.deepEqual(by('Site score').slides, [1]);
  assert.deepEqual(by('Speed').slides, [2]);
  assert.equal(by('Accessibility').found, false);
  assert.match(by('Accessibility').add, /accessibility/i);
  assert.equal(by('Their technologies').found, true);
  assert.equal(by('Weak sales').found, false);
  assert.equal(r.covered, r.checks.filter((c) => c.found).length);
  assert.equal(r.slides, 4);
});

test('slide text is read from a real .pptx in slide order', async () => {
  const texts = await slideTexts(readFileSync('docs/Nitro-Digithon-2026.pptx'));
  assert.ok(texts.length > 10);
  assert.match(texts[0], /Nitro/);
});
