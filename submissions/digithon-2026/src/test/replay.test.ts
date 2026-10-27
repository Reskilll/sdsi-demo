import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';

// web/replay.js is a plain browser script with no page code; evaluate it here and test the timing rules directly.
const { replayDelay, replayWait } = runInNewContext(`${readFileSync('web/replay.js', 'utf8')}\n({ replayDelay, replayWait })`) as {
  replayDelay: (gap: number, speed: number) => number;
  replayWait: (shownAt: number, now: number, gap: number, speed: number, hold?: number) => number;
};

test('slower speeds wait longer, faster speeds wait less, instant does not wait', () => {
  assert.equal(replayDelay(2000, 1), 2000);
  assert.equal(replayDelay(2000, 0.5), 4000);
  assert.equal(replayDelay(2000, 4), 500);
  assert.equal(replayDelay(2000, 0), 0);
});

test('bursts are held apart and long model calls are shortened', () => {
  assert.equal(replayDelay(0, 1), 700);
  assert.equal(replayDelay(70_000, 1), 2500);
  assert.equal(replayDelay(70_000, 0.25), 10_000);
});

test('a speed change applies to the post that is already waiting', () => {
  const shownAt = 0, gap = 2000;
  assert.equal(replayWait(shownAt, 1000, gap, 0.5), 3000, 'slow: 4000 ms due, 1000 gone');
  assert.equal(replayWait(shownAt, 1000, gap, 1), 1000, 'switch to normal: 1000 ms left');
  assert.equal(replayWait(shownAt, 1000, gap, 4), 0, 'switch to 4x: already overdue, shows now');
  assert.equal(replayWait(shownAt, 1000, gap, 0), 0, 'switch to instant: shows now');
});

test('a major moment holds for a beat, but never at Instant', () => {
  assert.equal(replayWait(0, 0, 100, 4, 1700), 1700);
  assert.equal(replayWait(0, 0, 100, 0, 1700), 0);
});
