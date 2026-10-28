/**
 * Model catalog: fetches the list of available models from an OpenAI-compatible
 * `/v1/models` endpoint so MasterX can present them in a dropdown instead of
 * asking the user to type a model id.
 *
 * The shape accepted is OpenAI's (`{ object: "list", data: [{ id, owned_by }] }`)
 * with tolerant fallbacks for gateways that return a bare array or a `models`
 * key, since several Claude-CLI-compatible proxies deviate slightly.
 */

/** One selectable model from the catalog. */
export interface ModelInfo {
  /** Model id passed to `claude --model`. */
  id: string;
  /** Provider / owner, shown as a secondary label in the dropdown. */
  ownedBy?: string;
  /** Creation timestamp from the API, when supplied. */
  created?: number;
}

/** Raised when the catalog cannot be fetched or parsed. */
export class ModelCatalogError extends Error {
  constructor(
    message: string,
    /** HTTP status when the failure came from an HTTP response. */
    public readonly status?: number,
    public override readonly cause?: unknown
  ) {
    super(message);
    this.name = 'ModelCatalogError';
  }
}

export interface FetchModelListOptions {
  /** Endpoint URL, e.g. https://creditclaim.reskilll.com/llm/v1/models */
  url: string;
  /** Bearer token for the `Authorization` header. */
  apiKey: string;
  /** Request timeout in milliseconds (default 20s). */
  timeoutMs?: number;
}

/**
 * GET the model catalog and return it sorted by id.
 */
export async function fetchModelList(options: FetchModelListOptions): Promise<ModelInfo[]> {
  const url = (options.url ?? '').trim();
  const apiKey = (options.apiKey ?? '').trim();

  if (!url) {
    throw new ModelCatalogError(
      'Model catalog URL is empty. Set `masterx.modelListUrl` (default https://creditclaim.reskilll.com/llm/v1/models).'
    );
  }
  if (!apiKey) {
    throw new ModelCatalogError(
      'OpenAI API key is missing. Set `masterx.openAiApiKey` in Settings or the OPENAI_API_KEY environment variable.'
    );
  }

  const timeoutMs = options.timeoutMs ?? 20_000;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  let response: Response;
  try {
    response = await fetch(url, {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${apiKey}`,
        Accept: 'application/json',
      },
      signal: controller.signal,
    });
  } catch (error) {
    clearTimeout(timer);
    if (error instanceof Error && error.name === 'AbortError') {
      throw new ModelCatalogError(
        `Model catalog request timed out after ${Math.round(timeoutMs / 1000)}s (${url}).`
      );
    }
    const detail = error instanceof Error ? error.message : String(error);
    throw new ModelCatalogError(`Failed to reach the model catalog at ${url}: ${detail}`);
  }
  clearTimeout(timer);

  const rawBody = await response.text();

  if (!response.ok) {
    // Surface the API's own message; never the key.
    let apiMessage = response.statusText || 'no response body';
    try {
      const parsed = JSON.parse(rawBody) as { error?: { message?: string } | string };
      if (typeof parsed?.error === 'string') {
        apiMessage = parsed.error;
      } else if (typeof parsed?.error?.message === 'string') {
        apiMessage = parsed.error.message;
      } else if (rawBody) {
        apiMessage = rawBody.slice(0, 300);
      }
    } catch {
      if (rawBody) {
        apiMessage = rawBody.slice(0, 300);
      }
    }

    const hint =
      response.status === 401 || response.status === 403
        ? ' Check that `masterx.openAiApiKey` is valid for this endpoint.'
        : '';
    throw new ModelCatalogError(
      `Model catalog request failed (HTTP ${response.status}): ${apiMessage}${hint}`,
      response.status
    );
  }

  let payload: unknown;
  try {
    payload = JSON.parse(rawBody);
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error);
    throw new ModelCatalogError(
      `Model catalog returned non-JSON content (${detail}). Body began with: ${rawBody.slice(0, 200)}`
    );
  }

  const models = parseModelList(payload);
  if (models.length === 0) {
    throw new ModelCatalogError('Model catalog returned no models.');
  }
  return models;
}

/**
 * Parse a model-list payload into ModelInfo records. Tolerates:
 *   - OpenAI:      { object: "list", data: [{ id, owned_by }] }
 *   - bare array:  [{ id }]
 *   - alt keys:    { models: [{ name | id }] }
 */
export function parseModelList(payload: unknown): ModelInfo[] {
  const raw: unknown[] = [];

  if (Array.isArray(payload)) {
    raw.push(...payload);
  } else if (payload !== null && typeof payload === 'object') {
    const obj = payload as { data?: unknown; models?: unknown };
    if (Array.isArray(obj.data)) {
      raw.push(...obj.data);
    } else if (Array.isArray(obj.models)) {
      raw.push(...obj.models);
    }
  }

  const out: ModelInfo[] = [];
  const seen = new Set<string>();

  for (const entry of raw) {
    if (typeof entry === 'string') {
      const id = entry.trim();
      if (id && !seen.has(id)) {
        seen.add(id);
        out.push({ id });
      }
      continue;
    }
    if (entry === null || typeof entry !== 'object') {
      continue;
    }
    const record = entry as {
      id?: unknown;
      name?: unknown;
      owned_by?: unknown;
      owner?: unknown;
      created?: unknown;
    };
    const id =
      typeof record.id === 'string' && record.id.trim()
        ? record.id.trim()
        : typeof record.name === 'string' && record.name.trim()
          ? record.name.trim()
          : '';
    if (!id || seen.has(id)) {
      continue;
    }
    seen.add(id);

    const ownedBy =
      typeof record.owned_by === 'string' && record.owned_by.trim()
        ? record.owned_by.trim()
        : typeof record.owner === 'string' && record.owner.trim()
          ? record.owner.trim()
          : undefined;

    const created = typeof record.created === 'number' ? record.created : undefined;

    out.push({ id, ownedBy, created });
  }

  out.sort((a, b) => a.id.localeCompare(b.id, undefined, { sensitivity: 'base' }));
  return out;
}

/**
 * Filter the catalog down to ids that look like text/chat models, dropping the
 * obvious non-conversational ones (embeddings, image, audio, moderation).
 * Returns the input unchanged when the filter would remove everything, so the
 * user is never left with an empty dropdown.
 */
export function preferChatModels(models: ModelInfo[]): ModelInfo[] {
  const nonChat = /(embedding|dall-e|whisper|tts|moderation|image|audio|search|realtime)/i;
  const filtered = models.filter((m) => !nonChat.test(m.id));
  return filtered.length > 0 ? filtered : models;
}
