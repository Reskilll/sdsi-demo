// Replay timing, kept free of page code so it can be tested on its own (see src/test/replay.test.ts).
const REPLAY_MIN_GAP_MS = 700;   // shortest pause between two posts at 1x, so bursts stay readable
const REPLAY_MAX_GAP_MS = 2500;  // longest pause at 1x, so a 70 s model call does not become a 70 s wait

/** How long one post stays up before the next, at a given speed. Speed 0 means instant. */
function replayDelay(gapMs, speed) {
  if (!(speed > 0)) return 0;
  return Math.max(REPLAY_MIN_GAP_MS, Math.min(gapMs, REPLAY_MAX_GAP_MS)) / speed;
}

/**
 * Milliseconds to wait from `now` until the next post is due, given when the previous post was shown.
 * Called again whenever the speed changes, so a new speed applies to the post that is already waiting.
 * `holdMs` keeps a major moment on screen for a beat, except at Instant.
 */
function replayWait(shownAt, now, gapMs, speed, holdMs = 0) {
  if (!(speed > 0)) return 0;
  return Math.max(0, shownAt + Math.max(replayDelay(gapMs, speed), holdMs) - now);
}
