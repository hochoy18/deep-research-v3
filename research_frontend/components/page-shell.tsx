"use client";

/**
 * research_frontend/components/page-shell.tsx
 *
 * Client-side wrapper for app/page.tsx (T034). The Server Component
 * imports this module's named exports and slots them into the layout;
 * each export forwards to a \"use client\" component.
 *
 * Why the indirection:
 *   - Next.js 16 App Router allows named imports from a client module into
 *     a server module. We co-locate the three shell components here so
 *     page.tsx stays a pure layout file.
 *   - Components used here (ThreadList / ChatThread / MessageInput) are
 *     themselves \"use client\" and read from the Zustand store directly.
 */

import { ThreadList } from "@/components/thread-list";
import { ChatThread } from "@/components/chat-thread";
import { MessageInput } from "@/components/message-input";
import { selectCurrentThread, useChatStore } from "@/lib/store";

function ThreadListSidebar(): React.JSX.Element {
  return <ThreadList />;
}

function ChatArea(): React.JSX.Element {
  const current = useChatStore(selectCurrentThread);
  const isDisabled = current === null;
  return (
    <div className="flex h-full flex-1 flex-col overflow-hidden">
      <ChatThread />
      <MessageInput disabled={isDisabled} />
    </div>
  );
}

export const PageShell = {
  ThreadListSidebar,
  ChatArea,
} as const;
