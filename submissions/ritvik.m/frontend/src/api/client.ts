import { loadSessionAuth } from './session';
import type {
  ConflictView,
  FieldError,
  OccurrenceStatus,
  OccurrenceView,
} from './types';

const API_BASE = '/api';

export type QueryValue = string | number | boolean | null | undefined;

export type ResponseType = 'json' | 'blob' | 'text' | 'void';

export interface RequestOptions {
  method?: string;
  body?: unknown;
  query?: Record<string, QueryValue | QueryValue[]>;
  /** Explicit credential, used only while validating a login. */
  token?: string | null;
  responseType?: ResponseType;
  /** A failed login must not clear the current session or trigger a redirect. */
  skipUnauthorizedHandler?: boolean;
  signal?: AbortSignal;
}

export interface ApiErrorInit {
  status: number;
  title: string;
  detail: string;
  code: string | null;
  fieldErrors: FieldError[];
  conflicts: ConflictView[];
  occurrences: OccurrenceView[];
  conflictCount: number | null;
  totalOccurrences: number | null;
}

/** Typed RFC 9457 problem+json failure, plus a friendly network-error variant. */
export class ApiError extends Error {
  readonly status: number;
  readonly title: string;
  readonly detail: string;
  readonly code: string | null;
  readonly fieldErrors: FieldError[];
  readonly conflicts: ConflictView[];
  readonly occurrences: OccurrenceView[];
  readonly conflictCount: number | null;
  readonly totalOccurrences: number | null;

  constructor(init: ApiErrorInit) {
    super(init.detail);
    this.name = 'ApiError';
    this.status = init.status;
    this.title = init.title;
    this.detail = init.detail;
    this.code = init.code;
    this.fieldErrors = init.fieldErrors;
    this.conflicts = init.conflicts;
    this.occurrences = init.occurrences;
    this.conflictCount = init.conflictCount;
    this.totalOccurrences = init.totalOccurrences;
  }

  fieldError(field: string): string | null {
    return this.fieldErrors.find((entry) => entry.field === field)?.message ?? null;
  }

  get isConflict(): boolean {
    return this.status === 409;
  }
}

type UnauthorizedListener = (error: ApiError) => void;
const unauthorizedListeners = new Set<UnauthorizedListener>();

export function onUnauthorized(listener: UnauthorizedListener): () => void {
  unauthorizedListeners.add(listener);
  return () => unauthorizedListeners.delete(listener);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function readString(value: unknown): string | null {
  return typeof value === 'string' && value.trim() !== '' ? value : null;
}

function readNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function readArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function parseFieldErrors(value: unknown): FieldError[] {
  const result: FieldError[] = [];
  for (const entry of readArray(value)) {
    if (!isRecord(entry)) continue;
    const field = readString(entry.field);
    const message = readString(entry.message);
    if (field && message) result.push({ field, message });
  }
  return result;
}

function parseConflicts(value: unknown): ConflictView[] {
  const result: ConflictView[] = [];
  for (const entry of readArray(value)) {
    if (!isRecord(entry)) continue;
    result.push({
      bookingId: readString(entry.bookingId) ?? '',
      title: readString(entry.title) ?? 'Untitled booking',
      organiser: readString(entry.organiser) ?? 'Unknown organiser',
      start: readString(entry.start) ?? '',
      end: readString(entry.end) ?? '',
    });
  }
  return result;
}

function parseOccurrences(value: unknown): OccurrenceView[] {
  const result: OccurrenceView[] = [];
  for (const entry of readArray(value)) {
    if (!isRecord(entry)) continue;
    const status: OccurrenceStatus = entry.status === 'CONFLICT' ? 'CONFLICT' : 'FREE';
    const start = readString(entry.start);
    const end = readString(entry.end);
    if (!start || !end) continue;
    result.push({
      start,
      end,
      status,
      conflicts: parseConflicts(entry.conflicts),
    });
  }
  return result;
}

async function toApiError(response: Response): Promise<ApiError> {
  let body: unknown = null;
  const contentType = response.headers.get('content-type') ?? '';
  try {
    if (contentType.includes('json')) {
      body = await response.json();
    } else {
      const raw = await response.text();
      if (raw.trim() !== '') body = { detail: raw.slice(0, 300) };
    }
  } catch {
    body = null;
  }

  const problem = isRecord(body) ? body : {};
  const status = response.status;
  const fallbackDetail = `The request failed (HTTP ${status}). Please try again.`;

  return new ApiError({
    status,
    title: readString(problem.title) ?? response.statusText ?? 'Request failed',
    detail: readString(problem.detail) ?? fallbackDetail,
    code: readString(problem.code),
    fieldErrors: parseFieldErrors(problem.errors),
    conflicts: parseConflicts(problem.conflicts),
    occurrences: parseOccurrences(problem.occurrences),
    conflictCount: readNumber(problem.conflictCount),
    totalOccurrences: readNumber(problem.totalOccurrences),
  });
}

function buildQuery(query: RequestOptions['query']): string {
  if (!query) return '';
  const params = new URLSearchParams();
  for (const [key, raw] of Object.entries(query)) {
    if (raw === undefined || raw === null) continue;
    const values = Array.isArray(raw) ? raw : [raw];
    for (const value of values) {
      if (value === undefined || value === null || value === '') continue;
      params.append(key, String(value));
    }
  }
  const encoded = params.toString();
  return encoded ? `?${encoded}` : '';
}

function authHeader(options: RequestOptions): string | null {
  if (options.token !== undefined) {
    return options.token ? `Basic ${options.token}` : null;
  }
  const stored = loadSessionAuth();
  return stored ? `Basic ${stored.token}` : null;
}

/**
 * Single fetch wrapper: attaches Basic auth, parses problem+json into
 * ApiError, and notifies the auth layer on 401. All paths are relative to /api
 * so the Vite proxy and a same-origin deployment both work unchanged.
 */
export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const responseType = options.responseType ?? 'json';
  const headers: Record<string, string> = {
    Accept:
      responseType === 'blob' || responseType === 'text'
        ? '*/*'
        : 'application/json, application/problem+json',
  };
  const authorization = authHeader(options);
  if (authorization) headers.Authorization = authorization;
  if (options.body !== undefined) headers['Content-Type'] = 'application/json';

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}${buildQuery(options.query)}`, {
      method: options.method ?? 'GET',
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: options.signal,
    });
  } catch (cause: unknown) {
    if (options.signal?.aborted) throw cause;
    throw new ApiError({
      status: 0,
      title: 'Connection problem',
      detail: 'Could not reach the booking service. Check that it is running and try again.',
      code: 'NETWORK_ERROR',
      fieldErrors: [],
      conflicts: [],
      occurrences: [],
      conflictCount: null,
      totalOccurrences: null,
    });
  }

  if (!response.ok) {
    const error = await toApiError(response);
    if (response.status === 401 && !options.skipUnauthorizedHandler) {
      for (const listener of unauthorizedListeners) listener(error);
    }
    throw error;
  }

  if (responseType === 'void' || response.status === 204) return undefined as T;
  if (responseType === 'blob') return (await response.blob()) as T;
  if (responseType === 'text') return (await response.text()) as T;
  return (await response.json()) as T;
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.detail;
  if (error instanceof Error && error.message) return error.message;
  return 'Something went wrong. Please try again.';
}

export function triggerBlobDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.style.display = 'none';
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1500);
}
