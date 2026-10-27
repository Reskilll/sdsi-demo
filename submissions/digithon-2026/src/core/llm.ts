import './env.js';
import Anthropic from '@anthropic-ai/sdk';
import type { AgentId, TokenUsage } from './events.js';
import type { RunContext } from './context.js';

export const MODEL = process.env.NITRO_MODEL ?? 'claude-sonnet-5-5';

const client = process.env.ANTHROPIC_API_KEY ? new Anthropic() : null;

export const llmAvailable = client !== null;

/** List prices in USD per million tokens. Cache writes cost 1.25x input, cache reads 0.1x input. */
const PRICES: Record<string, { input: number; output: number }> = {
  'claude-sonnet-5-5': { input: 2, output: 10 },
  'claude-opus-5-5': { input: 4, output: 20 },
  'claude-haiku-5-5': { input: 0.1, output: 0.5 },
};

export function costOf(model: string, u: Omit<TokenUsage, 'model' | 'costUsd'>): number | null {
  const p = PRICES[model];
  if (!p) return null;
  return (u.input * p.input + u.cacheWrite * p.input * 1.25 + u.cacheRead * p.input * 0.1 + u.output * p.output) / 1e6;
}

export interface LlmOptions {
  maxTokens?: number;
  /** PNG screenshots to attach for vision calls. */
  images?: Buffer[];
  /** Called with the number of characters received so far (streaming). */
  onProgress?: (chars: number) => void;
  /** Posts the call's token usage to this run's feed, attributed to this agent. */
  usage?: { run: RunContext; agent: AgentId };
}

/** Thrown when the model stopped because it ran out of output tokens, so the text is incomplete. */
export class TruncatedError extends Error {
  constructor(readonly partial: string) { super('Model output was cut off at the token limit.'); }
}

/** Returns the model's text, or null when no API key is configured so callers use their offline fallback. */
export async function llmText(system: string, user: string, opts: LlmOptions = {}): Promise<string | null> {
  if (!client) return null;
  const content: Anthropic.ContentBlockParam[] = [
    ...(opts.images ?? []).map(
      (img): Anthropic.ImageBlockParam => ({
        type: 'image',
        source: { type: 'base64', media_type: 'image/png', data: img.toString('base64') },
      }),
    ),
    { type: 'text', text: user },
  ];
  const stream = client.messages.stream({
    model: MODEL,
    max_tokens: opts.maxTokens ?? 4000,
    system,
    messages: [{ role: 'user', content }],
  });
  let chars = 0;
  if (opts.onProgress) stream.on('text', (t) => { chars += t.length; opts.onProgress!(chars); });
  const res = await stream.finalMessage();
  if (opts.usage) {
    const u = res.usage;
    const counts = { input: u.input_tokens, output: u.output_tokens, cacheRead: u.cache_read_input_tokens ?? 0, cacheWrite: u.cache_creation_input_tokens ?? 0 };
    const usage: TokenUsage = { model: MODEL, ...counts, costUsd: costOf(MODEL, counts) };
    opts.usage.run.bus.emit({ from: opts.usage.agent, kind: 'usage', friendly: `${counts.input + counts.output} tokens`, usage });
  }
  const text = res.content.map((b) => (b.type === 'text' ? b.text : '')).join('');
  if (res.stop_reason === 'max_tokens') throw new TruncatedError(text);
  return text;
}

export function extractJson<T>(text: string): T {
  const m = text.match(/```(?:json)?\s*([\s\S]*?)```/);
  return JSON.parse(m ? m[1] : text.slice(text.indexOf('{'), text.lastIndexOf('}') + 1)) as T;
}
