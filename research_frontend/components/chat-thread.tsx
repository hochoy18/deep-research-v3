"use client";

/**
 * research_frontend/components/chat-thread.tsx
 *
 * M1 foundational scaffold. Will be replaced by T061 (Phase 4, US-2
 * Implementation) on this same branch. Renders the messages of the
 * currently selected thread (via useChatStore) so the layout is
 * observable end-to-end. The streaming SSE pipeline (T060/T061) lands
 * in Phase 4.
 *
 * Replacement contract (T061):
 *   - Subscribe to streamingByMessage[id] for in-flight chunks.
 *   - Render Markdown with the streaming buffer joining in real time.
 *   - Drop the static empty-state once a thread is loaded.
 */

import { selectMessagesForCurrent, useChatStore } from "@/lib/store";
import { cn } from "@/lib/cn";
import type { Message } from "@/lib/types";

export function ChatThread(): React.JSX.Element {
  const messages = useChatStore(selectMessagesForCurrent);

  return (
    <section
      aria-label="对话内容"
      className="flex h-full flex-col gap-4 overflow-y-auto p-6"
      data-testid="chat-thread"
    >
      {messages.length === 0 ? (
        <div className="m-auto max-w-md text-center text-sm text-muted-foreground">
          <h3 className="mb-2 text-base font-semibold">开始一个新对话</h3>
          <p>在上方输入框中提问,后端会按 token 流式回显。</p>
        </div>
      ) : (
        messages.map((m: Message) => (
          <article
            key={m.message_id}
            className={cn(
              "max-w-2xl",
              m.role === "user" ? "ml-auto" : "mr-auto",
            )}
            data-testid={`message-${m.role}`}
          >
            <div
              className={cn(
                m.role === "user"
                  ? "chat-bubble-user"
                  : "chat-bubble-assistant",
              )}
            >
              {m.content || (
                <span className="text-muted-foreground">…</span>
              )}
            </div>
            <p className="mt-1 px-1 text-xs text-muted-foreground">
              {m.status === "streaming" ? "生成中…" : m.role === "user" ? "你" : "助手"}
            </p>
          </article>
        ))
      )}
    </section>
  );
}
