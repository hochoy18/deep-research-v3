"use client";

/**
 * research_frontend/components/message-input.tsx
 *
 * M1 foundational scaffold. Will be replaced by T062 (Phase 4, US-2
 * Implementation) on this same branch. Renders a textarea + Send button
 * so the layout is observable end-to-end; the Enter-to-submit keyboard
 * handler lives in T062 + T086 (US4 unit test).
 *
 * Replacement contract (T062):
 *   - useState for the textarea value.
 *   - Enter sends (without Shift) per PR-005.
 *   - Disabled while streaming (button + textarea).
 *   - onSubmit handler calls streamMessage(...) from lib/api.ts and
 *     feeds events into useChatStore.appendStreamChunk / updateMessage.
 */

import { useState } from "react";
import { cn } from "@/lib/cn";

export interface MessageInputProps {
  onSend?: (value: string) => void;
  disabled?: boolean;
}

export function MessageInput({
  onSend,
  disabled,
}: MessageInputProps): React.JSX.Element {
  const [value, setValue] = useState("");

  const handleSubmit = (): void => {
    const trimmed = value.trim();
    if (trimmed === "" || disabled === true) {
      return;
    }
    onSend?.(trimmed);
    setValue("");
  };

  return (
    <form
      className="flex items-end gap-2 border-t border-border bg-background p-3"
      onSubmit={(e) => {
        e.preventDefault();
        handleSubmit();
      }}
      data-testid="message-input-form"
    >
      <textarea
        aria-label="消息输入"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
          }
        }}
        placeholder="输入你的问题…"
        rows={2}
        disabled={disabled}
        className={cn(
          "min-h-[2.5rem] flex-1 resize-none rounded-md border border-border",
          "bg-background px-3 py-2 text-sm",
          "focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100",
          "disabled:cursor-not-allowed disabled:opacity-50",
        )}
        data-testid="message-input-textarea"
      />
      <button
        type="submit"
        disabled={disabled === true || value.trim() === ""}
        className={cn(
          "rounded-md bg-brand-500 px-4 py-2 text-sm font-medium text-background",
          "transition-colors hover:bg-brand-600",
          "disabled:cursor-not-allowed disabled:opacity-50",
        )}
        data-testid="message-input-submit"
      >
        发送
      </button>
    </form>
  );
}
