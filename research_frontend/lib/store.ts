/**
 * research_frontend/lib/store.ts
 *
 * Client-side Zustand store for the Deep Research Agent M1 frontend.
 *
 * Three top-level slices:
 *   1. **Session** — anonymous user_id (mirrored from the cookie for
 *      debug visibility; the source of truth is the HttpOnly cookie set
 *      by the backend, never re-issued here).
 *   2. **Threads** — list of threads owned by the current user + the
 *      currently selected thread_id. UI only ever shows threads that come
 *      back from the backend (which enforces cross-user isolation
 *      server-side — SC-011 / FR-011a).
 *   3. **Messages** — keyed by thread_id, holding optimistic + persisted
 *      messages plus the per-message streaming buffer.
 *
 * Design rules:
 *   - All ids are stored as strings; comparison MUST be case-sensitive.
 *   - Selectors are co-located (useChatStore.getState() / selectors) so
 *     components can subscribe to a stable slice.
 *   - Imperative actions live next to their slice; mutations use immutable
 *     spreads (Zustand v5 devtools-friendly defaults).
 */

"use client";

import { create } from "zustand";
import { devtools } from "zustand/middleware";
import {
  type Message,
  type StreamingBuffer,
  type Thread,
  type UUID,
} from "./types";

// =============================================================================
// State shape
// =============================================================================

export interface SessionSlice {
  /** Read-only mirror of the user_id cookie; set after first /health ping. */
  user_id: UUID | null;
}

export interface ThreadSlice {
  threads: Thread[];
  /** Currently selected thread in the side panel / ChatThread area. */
  currentThreadId: UUID | null;
}

export interface MessageSlice {
  /** message_id → persisted Message record. */
  messagesByThread: Record<UUID, Message[]>;
  /** message_id → in-flight streaming buffer (assistant only). */
  streamingByMessage: Record<UUID, StreamingBuffer>;
  /** Per-thread counter, used to prevent stale SSE chunks overwriting newer state. */
  streamingGenByThread: Record<UUID, number>;
}

export interface ChatStore
  extends SessionSlice,
    ThreadSlice,
    MessageSlice {
  // ---- session actions ----
  setUserId: (id: UUID | null) => void;

  // ---- thread actions ----
  setThreads: (threads: Thread[]) => void;
  upsertThread: (thread: Thread) => void;
  selectThread: (id: UUID | null) => void;

  // ---- message actions ----
  setMessages: (threadId: UUID, messages: Message[]) => void;
  appendMessage: (threadId: UUID, message: Message) => void;
  updateMessage: (
    threadId: UUID,
    messageId: UUID,
    patch: Partial<Message>,
  ) => void;

  // ---- streaming actions ----
  appendStreamChunk: (
    threadId: UUID,
    messageId: UUID,
    chunk: string,
    index: number,
  ) => void;
  clearStream: (messageId: UUID) => void;
  bumpStreamingGen: (threadId: UUID) => number;
}

// =============================================================================
// Store
// =============================================================================

export const useChatStore = create<ChatStore>()(
  devtools(
    (set, get) => ({
      // ---- initial state ----
      user_id: null,
      threads: [],
      currentThreadId: null,
      messagesByThread: {},
      streamingByMessage: {},
      streamingGenByThread: {},

      // ---- session ----
      setUserId: (id) => set({ user_id: id }),

      // ---- threads ----
      setThreads: (threads) => set({ threads }),
      upsertThread: (thread) =>
        set((state) => {
          const idx = state.threads.findIndex(
            (t) => t.thread_id === thread.thread_id,
          );
          if (idx === -1) {
            return { threads: [thread, ...state.threads] };
          }
          const next = [...state.threads];
          next[idx] = { ...next[idx], ...thread };
          return { threads: next };
        }),
      selectThread: (id) => {
        // Reset streaming buffers for the previous thread to prevent
        // cross-thread visual bleed.
        if (id !== get().currentThreadId) {
          set({ streamingByMessage: {}, streamingGenByThread: {} });
        }
        set({ currentThreadId: id });
      },

      // ---- messages ----
      setMessages: (threadId, messages) =>
        set((state) => ({
          messagesByThread: { ...state.messagesByThread, [threadId]: messages },
        })),
      appendMessage: (threadId, message) =>
        set((state) => {
          const existing = state.messagesByThread[threadId] ?? [];
          return {
            messagesByThread: {
              ...state.messagesByThread,
              [threadId]: [...existing, message],
            },
          };
        }),
      updateMessage: (threadId, messageId, patch) =>
        set((state) => {
          const existing = state.messagesByThread[threadId];
          if (!existing) {
            return state;
          }
          const idx = existing.findIndex((m) => m.message_id === messageId);
          if (idx === -1) {
            return state;
          }
          const next = [...existing];
          next[idx] = { ...next[idx], ...patch };
          return {
            messagesByThread: {
              ...state.messagesByThread,
              [threadId]: next,
            },
          };
        }),

      // ---- streaming ----
      appendStreamChunk: (threadId, messageId, chunk, index) =>
        set((state) => {
          const current = state.streamingByMessage[messageId];
          // If we received a chunk after the stream was cleared (e.g. after
          // status='complete'), drop it. Backend re-sends should not race.
          if (!current && state.streamingGenByThread[threadId] === undefined) {
            return state;
          }
          const lastIndex = current?.lastIndex ?? -1;
          const chunks = current ? [...current.chunks] : [];
          // Fill gaps with empty strings so callers can join by index safely.
          while (chunks.length <= index) {
            chunks.push("");
          }
          chunks[index] = chunk;
          return {
            streamingByMessage: {
              ...state.streamingByMessage,
              [messageId]: { chunks, lastIndex: Math.max(lastIndex, index) },
            },
          };
        }),
      clearStream: (messageId) =>
        set((state) => {
          const next = { ...state.streamingByMessage };
          delete next[messageId];
          return { streamingByMessage: next };
        }),
      bumpStreamingGen: (threadId) => {
        const next = (get().streamingGenByThread[threadId] ?? 0) + 1;
        set((state) => ({
          streamingGenByThread: {
            ...state.streamingGenByThread,
            [threadId]: next,
          },
        }));
        return next;
      },
    }),
    {
      name: "research-frontend-chat",
      // devtools-only label
      enabled: process.env["NODE_ENV"] !== "production",
    },
  ),
);

// =============================================================================
// Selectors (export for component-level imports; keeps components shallow)
// =============================================================================

export const selectCurrentThread = (state: ChatStore): Thread | null => {
  if (state.currentThreadId === null) {
    return null;
  }
  return (
    state.threads.find((t) => t.thread_id === state.currentThreadId) ?? null
  );
};

export const selectMessagesForCurrent = (state: ChatStore): Message[] => {
  if (state.currentThreadId === null) {
    return [];
  }
  return state.messagesByThread[state.currentThreadId] ?? [];
};

export const selectStreamedText = (
  state: ChatStore,
  messageId: UUID,
): string => {
  const buf = state.streamingByMessage[messageId];
  if (!buf) {
    return "";
  }
  return buf.chunks.join("");
};
