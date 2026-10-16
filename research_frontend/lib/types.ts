/**
 * research_frontend/lib/types.ts
 *
 * TypeScript type definitions for the Deep Research Agent M1 frontend.
 *
 * These types are the client-side mirror of `specs/001-m1-infra/contracts/openapi.yaml`
 * (M1 contract freeze, constitution VI). Whenever the OpenAPI contract changes
 * (RFC flow), these types MUST be updated in the same PR and reflected in
 * `tests/contract/test_openapi.py` parity checks.
 *
 * Three families of types live here:
 *   1. **Domain** — Thread, Message (correspond to OpenAPI components.schemas)
 *   2. **Action bodies** — MessageCreate, used for POST /threads/{id}/messages
 *   3. **SSE** — SSEEvent union + helpers for parsing `eventsource-parser` tokens
 *
 * Conventions:
 *   - All ids are UUID v4 (`brand`-style typing not used yet to keep types ergonomic;
 *     runtime validation handled by `zod` at the api boundary, not by type guards).
 *   - Dates are ISO 8601 UTC strings; conversion to `Date` happens at the UI layer.
 *   - Snake_case mirrors the OpenAPI wire format; UI code converts to camelCase where needed.
 *   - `null` vs `undefined`: optional fields use `?` (Property missing); nullable fields
 *     use `| null` matching `nullable: true` in the OpenAPI schema (see Message.completed_at).
 */

// =============================================================================
// Domain entities (mirror OpenAPI components.schemas.Thread / Message)
// =============================================================================

/** Backend /threads/{thread_id} UUID. */
export type UUID = string;

/**
 * Thread — conversation session.
 *
 * Note: `user_id` is included for completeness but the UI should never display it;
 * the backend enforces cookie-based ownership (FR-011a / SC-011).
 */
export interface Thread {
  thread_id: UUID;
  user_id: UUID;
  title: string;
  status: ThreadStatus;
  created_at: ISO8601;
  updated_at: ISO8601;
  /** Optional — populated by GET /threads/{id}, not by list endpoints. */
  message_count?: number;
}

export type ThreadStatus = "active" | "archived";

/**
 * Message — a single chat message (user / assistant / system).
 *
 * M1 mock behavior: assistant messages stream tokens and transition
 * `status: streaming → complete` via SSE `state_update` events.
 */
export interface Message {
  message_id: UUID;
  thread_id: UUID;
  role: MessageRole;
  content: string;
  status: MessageStatus;
  created_at: ISO8601;
  completed_at: ISO8601 | null;
}

export type MessageRole = "user" | "assistant" | "system";

export type MessageStatus = "streaming" | "complete" | "failed";

/** ISO 8601 timestamp string, e.g. `2026-10-16T08:30:00.123Z`. */
export type ISO8601 = string;

// =============================================================================
// Action bodies (mirror OpenAPI components.schemas.MessageCreate)
// =============================================================================

/**
 * MessageCreate — body for POST /threads/{thread_id}/messages.
 *
 * Content MUST pass constitution I whitelist validation on the server
 * (printable ASCII + CJK + newline; control characters rejected).
 * Length 1..10000 enforced server-side (413 / 422).
 */
export interface MessageCreate {
  content: string;
}

// =============================================================================
// SSE event stream (mirror OpenAPI components.schemas.SSEEvent + variants)
// =============================================================================

export type SSEEventName = "message" | "state_update" | "done" | "error";

/**
 * SSEEvent — discriminated union of the four event shapes that the backend
 * streams during a chat response. The discriminator is `event`.
 *
 * Per-event payload shapes are derived from the OpenAPI `oneOf` definitions.
 */
export type SSEEvent =
  | SSEMessageEvent
  | SSEStateUpdateEvent
  | SSEDoneEvent
  | SSEErrorEvent;

export interface SSEEventBase {
  /** Per-message correlation id, present on message/state_update/done. */
  message_id?: UUID;
}

export interface SSEMessageEvent extends SSEEventBase {
  event: "message";
  data: {
    message_id: UUID;
    /** Markdown fragment — single token / token group chunk. */
    chunk: string;
    /** 0-based chunk index within the streaming assistant message. */
    index: number;
  };
}

export interface SSEStateUpdateEvent extends SSEEventBase {
  event: "state_update";
  data: {
    message_id: UUID;
    status: Exclude<MessageStatus, "failed"> | "failed";
  };
}

export interface SSEDoneEvent extends SSEEventBase {
  event: "done";
  data: {
    message_id: UUID;
    total_chunks: number;
    latency_ms: number;
  };
}

export type SSEErrorCode = "internal_error" | "llm_error" | "timeout";

export interface SSEErrorEvent {
  event: "error";
  data: {
    code: SSEErrorCode;
    message: string;
  };
}

/**
 * Narrow an SSEEvent to the `message` variant. Use to satisfy TS exhaustive
 * matching in ui renderers (the discriminated union is preferred over runtime
 * `as` casts).
 */
export const isSSEMessageEvent = (e: SSEEvent): e is SSEMessageEvent =>
  e.event === "message";

export const isSSEStateUpdateEvent = (e: SSEEvent): e is SSEStateUpdateEvent =>
  e.event === "state_update";

export const isSSEDoneEvent = (e: SSEEvent): e is SSEDoneEvent =>
  e.event === "done";

export const isSSEErrorEvent = (e: SSEEvent): e is SSEErrorEvent =>
  e.event === "error";

// =============================================================================
// Standard error envelope (mirror OpenAPI components.schemas.Error)
// =============================================================================

export interface ApiError {
  error: string;
  message: string;
  details?: Record<string, unknown>;
}

export const isApiError = (v: unknown): v is ApiError =>
  typeof v === "object" &&
  v !== null &&
  typeof (v as { error?: unknown }).error === "string" &&
  typeof (v as { message?: unknown }).message === "string";

// =============================================================================
// Local UI extensions (not in OpenAPI — purely client-side convenience)
// =============================================================================

/**
 * Optimistic message — UI-only wrapper carrying the streaming buffer
 * separately from the persisted Message.content (which we only have a
 * subset of during streaming). Cleared once `state_update: complete`
 * is received.
 */
export interface StreamingBuffer {
  /** Chunks received so far; joined in order to render Markdown. */
  chunks: string[];
  /** Highest `index` observed (for gap detection — backend may resend on retry). */
  lastIndex: number;
}
