/**
 * research_frontend/lib/api.ts
 *
 * Client-side API layer for the Deep Research Agent M1 backend.
 *
 * Responsibilities:
 *   1. fetchJson<T>() — typed wrapper around the Fetch API. Always sends
 *      `credentials: 'include'` so the backend's `user_id` cookie travels
 *      with every request (constitution VI / FR-008).
 *   2. Error normalisation — every non-2xx response is parsed into an
 *      `ApiError` shape (OpenAPI components.schemas.Error) so callers can
 *      `instanceof ApiError` check uniformly.
 *   3. SSE client — opens a streaming connection via the native EventSource
 *      (browser) or via manual `fetch()` + `eventsource-parser` (Node test
 *      environments / SSR streaming). Emits strongly-typed SSEEvents and
 *      auto-reconnects on transient network errors (FR-007, spec Q1).
 *
 * Implementation notes:
 *   - No polyfill for EventSource on the server side; SSR users should call
 *     these from client components only.
 *   - `API_BASE` reads `NEXT_PUBLIC_API_URL` — *MUST* be set via
 *     `research_frontend/.env.example` (T011) to `http://localhost:8000`.
 *   - The `user_id` cookie is never read or written from JS (HttpOnly).
 *     The browser attaches it automatically with `credentials: 'include'`.
 *   - SSE retry: a non-2xx response OR a connection close before the
 *     `done` event triggers ONE automatic reconnect after 1s; UI code is
 *     expected to surface persistent failures via the second `error` event.
 */

import {
  createParser,
  type EventSourceMessage,
} from "eventsource-parser";
import { z } from "zod";
import {
  type ApiError,
  type SSEEvent,
  type Thread,
  type Message,
  type MessageCreate,
  isApiError,
} from "./types";

// =============================================================================
// Configuration
// =============================================================================

/**
 * Backend base URL. Resolved once at module load; clients can override at
 * test time by stubbing the global. Falls back to localhost:8000 to match
 * `deploy/docker-compose.yml` and the OpenAPI `servers` entry.
 */
export const API_BASE: string =
  process.env["NEXT_PUBLIC_API_URL"] ?? "http://localhost:8000";

/** Default headers sent on every fetch request (overridable per-call). */
const DEFAULT_HEADERS: Record<string, string> = {
  "Content-Type": "application/json",
  Accept: "application/json",
};

// =============================================================================
// API error envelope + helpers
// =============================================================================

export class ApiRequestError extends Error {
  readonly status: number;
  readonly body: ApiError;

  constructor(status: number, body: ApiError) {
    super(`[${status}] ${body.error}: ${body.message}`);
    this.name = "ApiRequestError";
    this.status = status;
    this.body = body;
  }
}

const isApiErrorLoose = (v: unknown): v is ApiError =>
  isApiError(v) || (typeof v === "object" && v !== null && "error" in v && "message" in v);

/**
 * Internal: parse and validate an ApiError from a non-2xx Response body.
 * Falls back to a generic envelope when the body is not JSON-typed so the
 * UI never crashes on malformed upstream payloads.
 */
async function parseApiError(res: Response): Promise<ApiError> {
  let parsed: unknown = null;
  try {
    parsed = await res.json();
  } catch {
    parsed = null;
  }
  if (isApiErrorLoose(parsed)) {
    return parsed;
  }
  return {
    error: "http_error",
    message: `Request failed with status ${res.status}`,
  };
}

// =============================================================================
// HTTP helpers
// =============================================================================

export interface RequestOptions {
  /** Query string parameters; appended with proper URLSearchParams. */
  query?: Record<string, string | number | boolean>;
  /** AbortSignal — useful for unmount cleanup in chat-thread components. */
  signal?: AbortSignal;
  /** Override default JSON headers (e.g. for SSE). */
  headers?: Record<string, string>;
}

async function buildUrl(
  path: string,
  query?: RequestOptions["query"],
): Promise<string> {
  const base = `${API_BASE}${path}`;
  if (!query || Object.keys(query).length === 0) {
    return base;
  }
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(query)) {
    qs.set(k, String(v));
  }
  return `${base}?${qs.toString()}`;
}

/**
 * Typed JSON helper. Returns the parsed body on 2xx; throws ApiRequestError
 * otherwise. Always carries cookies (`credentials: 'include'`).
 */
export async function fetchJson<T>(
  path: string,
  init: RequestInit & RequestOptions = {},
): Promise<T> {
  const url = await buildUrl(path, init.query);
  const res = await fetch(url, {
    ...init,
    headers: {
      ...DEFAULT_HEADERS,
      ...init.headers,
    },
    credentials: "include", // sends the backend HttpOnly user_id cookie
  });
  if (!res.ok) {
    const body = await parseApiError(res);
    throw new ApiRequestError(res.status, body);
  }
  return res.json() as Promise<T>;
}

// =============================================================================
// Threads
// =============================================================================

export const ThreadsApi = {
  create: () =>
    fetchJson<Thread>("/threads", { method: "POST" }),

  list: () =>
    fetchJson<{ threads: Thread[] }>("/threads", { method: "GET" }),

  get: (threadId: string) =>
    fetchJson<Thread>(`/threads/${threadId}`, { method: "GET" }),
};

// =============================================================================
// Messages
// =============================================================================

export const MessagesApi = {
  list: (threadId: string) =>
    fetchJson<{ messages: Message[] }>(`/threads/${threadId}/messages`, {
      method: "GET",
    }),
};

// =============================================================================
// SSE streaming
// =============================================================================

/**
 * Strongly-typed validator for the SSE payload. The backend's openapi.yaml
 * describes SSEEvent.data as a oneOf — we narrow it lazily per event type
 * for forward-compatibility.
 */
const MessageEventSchema = z.object({
  message_id: z.string().uuid(),
  chunk: z.string(),
  index: z.number().int().nonnegative(),
});
const StateUpdateEventSchema = z.object({
  message_id: z.string().uuid(),
  status: z.enum(["streaming", "complete", "failed"]),
});
const DoneEventSchema = z.object({
  message_id: z.string().uuid(),
  total_chunks: z.number().int().nonnegative(),
  latency_ms: z.number().int().nonnegative(),
});
const ErrorEventSchema = z.object({
  code: z.enum(["internal_error", "llm_error", "timeout"]),
  message: z.string(),
});

/** Callback signature for streaming SSE consumption. */
export interface StreamHandlers {
  onEvent: (event: SSEEvent) => void;
  /** Fires once when the stream finishes (after the terminal `done` event). */
  onComplete?: () => void;
  /** Fires on any non-transient error (after retries are exhausted). */
  onError?: (err: ApiRequestError | Error) => void;
}

/** Single-pass retry policy — second failure surfaces to `onError`. */
const MAX_STREAM_RETRIES = 1;

/**
 * Open an SSE connection and dispatch strongly-typed events to `handlers`.
 *
 * Implementation detail: we deliberately use `fetch()` + a manual SSE
 * parser rather than the browser-native `EventSource`, because:
 *   1. POST body support (the chat endpoint takes a MessageCreate JSON body).
 *   2. Custom headers (CSRF / auth in M2+).
 *   3. Identical behaviour under Node-based vitest (jsdom does not ship an
 *      EventSource impl that accepts POST + request bodies).
 */
export async function streamMessage(
  threadId: string,
  body: MessageCreate,
  handlers: StreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const url = `${API_BASE}/threads/${threadId}/messages`;
  let attempt = 0;

  while (attempt <= MAX_STREAM_RETRIES) {
    attempt += 1;
    try {
      await runStream(url, body, handlers, signal);
      handlers.onComplete?.();
      return;
    } catch (err) {
      const isAbort = signal?.aborted === true;
      if (isAbort) {
        // Caller cancelled; surface silently.
        return;
      }
      if (attempt > MAX_STREAM_RETRIES) {
        handlers.onError?.(
          err instanceof ApiRequestError
            ? err
            : err instanceof Error
              ? err
              : new Error("Unknown streaming failure"),
        );
        return;
      }
      // Brief backoff before retry on transient failure.
      await new Promise((r) => setTimeout(r, 1000));
    }
  }
}

async function runStream(
  url: string,
  body: MessageCreate,
  handlers: StreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(url, {
    method: "POST",
    headers: { ...DEFAULT_HEADERS, Accept: "text/event-stream" },
    body: JSON.stringify(body),
    credentials: "include",
    signal,
  });

  if (!res.ok || res.body === null) {
    const parsed = await parseApiError(res);
    throw new ApiRequestError(res.status, parsed);
  }

  // Wire the SSE parser to our handlers. We tolerate either the SSE event
  // name in the wire-protocol header OR in the JSON `event` field — openapi
  // uses the latter, but some backends omit the header.
  const parser = createParser({
    onEvent: (msg: EventSourceMessage) => dispatchEvent(msg, handlers),
  });

  const reader = res.body.getReader();
  const decoder = new TextDecoder("utf-8");
  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    parser.feed(decoder.decode(value, { stream: true }));
  }
}

function dispatchEvent(
  raw: EventSourceMessage,
  handlers: StreamHandlers,
): void {
  // Try to parse `data` as JSON and dispatch as our SSEEvent union.
  let data: unknown;
  try {
    data = JSON.parse(raw.data);
  } catch {
    data = raw.data;
  }

  // The OpenAPI event-types use a lowercase event name; the wire-format SSE
  // event header is typically the same. We reconcile by preferring `raw.event`
  // when it's a known type, falling back to `data.event`.
  const wireType =
    (raw.event as SSEEvent["event"] | undefined) ??
    (typeof data === "object" && data !== null && "event" in data
      ? (data as { event: SSEEvent["event"] }).event
      : undefined);

  switch (wireType) {
    case "message": {
      const parsed = MessageEventSchema.safeParse(data);
      if (parsed.success) {
        handlers.onEvent({ event: "message", data: parsed.data });
      }
      break;
    }
    case "state_update": {
      const parsed = StateUpdateEventSchema.safeParse(data);
      if (parsed.success) {
        handlers.onEvent({ event: "state_update", data: parsed.data });
      }
      break;
    }
    case "done": {
      const parsed = DoneEventSchema.safeParse(data);
      if (parsed.success) {
        handlers.onEvent({ event: "done", data: parsed.data });
      }
      break;
    }
    case "error": {
      const parsed = ErrorEventSchema.safeParse(data);
      if (parsed.success) {
        handlers.onEvent({ event: "error", data: parsed.data });
      }
      break;
    }
    default:
      // Unknown event-type — silent ignore per SSE spec (forward-compatible
      // with newer backend event-types the client has not been updated for).
      break;
  }
}
