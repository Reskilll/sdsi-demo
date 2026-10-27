import * as chromeLauncher from 'chrome-launcher';
import { chromiumExecutable } from './browser.js';

export interface LighthouseResult {
  score: number;
  lcp: number; fcp: number; tbt: number; cls: number; speedIndex: number; bytes: number;
  opportunities: { title: string; savingsMs: number }[];
  version: string;
}

const TIMEOUT_MS = 90_000;

/** Runs Lighthouse (performance only, mobile profile, simulated throttling) in its own headless Chrome. */
export async function runLighthouse(url: string): Promise<LighthouseResult> {
  const chromePath = chromiumExecutable();
  if (!chromePath) throw new Error('No Chromium executable found for Lighthouse.');
  const chrome = await chromeLauncher.launch({ chromePath, chromeFlags: ['--headless=new', '--disable-gpu'] });
  let timer: NodeJS.Timeout | undefined;
  try {
    const { default: lighthouse } = await import('lighthouse');
    const run = lighthouse(url, { port: chrome.port, output: 'json', onlyCategories: ['performance'], logLevel: 'error' });
    const timeout = new Promise<never>((_, rej) => { timer = setTimeout(() => rej(new Error('Lighthouse timed out')), TIMEOUT_MS); });
    const result = await Promise.race([run, timeout]);
    const lhr = result?.lhr;
    if (!lhr || lhr.runtimeError) throw new Error(lhr?.runtimeError?.message ?? 'Lighthouse returned no result');
    const num = (id: string) => Number(lhr.audits[id]?.numericValue ?? 0);
    const opportunities = Object.values(lhr.audits)
      .filter((a) => a.details?.type === 'opportunity' && Number((a.details as { overallSavingsMs?: number }).overallSavingsMs ?? 0) > 300)
      .map((a) => ({ title: a.title, savingsMs: Math.round(Number((a.details as { overallSavingsMs?: number }).overallSavingsMs)) }))
      .sort((a, b) => b.savingsMs - a.savingsMs).slice(0, 3);
    return {
      score: Math.round((lhr.categories.performance?.score ?? 0) * 100),
      lcp: Math.round(num('largest-contentful-paint')), fcp: Math.round(num('first-contentful-paint')),
      tbt: Math.round(num('total-blocking-time')), cls: +num('cumulative-layout-shift').toFixed(3),
      speedIndex: Math.round(num('speed-index')), bytes: num('total-byte-weight'), opportunities, version: lhr.lighthouseVersion,
    };
  } finally {
    clearTimeout(timer);
    await chrome.kill();
  }
}
