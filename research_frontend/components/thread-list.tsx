"use client";

/**
 * research_frontend/components/thread-list.tsx
 *
 * M1 foundational SCaffold placeholder. The interactive behaviour — fetching
 * /threads, optimistic insert on creation, keyboard shortcuts — is implemented
 * in T063 (Phase 4, US-2 Implementation) on this same branch. Until then, this
 * component renders a static list sourced from the Zustand store so the
 * two-column layout (T034) is observable end-to-end.
 *
 * Replacement contract (T063):
 *   - Replace the no-op `useEffect` with a React Query /ThreadsApi.list() call.
 *   - Add a \"+ New thread\" action that calls ThreadsApi.create() and then
 *     useChatStore.upsertThread() + selectThread() on the response.
 *   - Wire keyboard navigation (ArrowUp/Down + Enter) per PR-006 acceptance
 *     criteria.
 */

import { selectCurrentThread, useChatStore } from "@/lib/store";
import { cn } from "@/lib/cn";
import type { Thread } from "@/lib/types";

export function ThreadList(): React.JSX.Element {
  const threads = useChatStore((s) => s.threads);
  const current = useChatStore(selectCurrentThread);
  const selectThread = useChatStore((s) => s.selectThread);

  return (
    <nav
      aria-label="线程列表"
      className="flex h-full flex-col gap-1 p-3"
      data-testid="thread-list"
    >
      <h2 className="mb-2 px-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        会话
      </h2>
      {threads.length === 0 ? (
        <p className="px-3 py-4 text-sm text-muted-foreground">
          暂无会话。点击右上角新建。
        </p>
      ) : (
        <ul className="flex flex-col gap-1">
          {threads.map((t: Thread) => {
            const active = current?.thread_id === t.thread_id;
            return (
              <li key={t.thread_id}>
                <button
                  type="button"
                  onClick={() => selectThread(t.thread_id)}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "thread-list-item",
                    "w-full text-left",
                    active && "thread-list-item-active",
                  )}
                >
                  <span className="line-clamp-1 text-sm">
                    {t.title || "新对话"}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </nav>
  );
}
