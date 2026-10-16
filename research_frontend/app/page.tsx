/**
 * research_frontend/app/page.tsx
 *
 * M1 main chat page (T034). Two-column layout:
 *   - Left  : <ThreadList /> (sidebar; thread titles + select)
 *   - Right : <ChatThread /> + <MessageInput /> (active conversation)
 *
 * The page is a thin Server Component that delegates to <PageShell /> —
 * a Client Component — because the UI state lives in a Zustand store
 * (lib/store.ts). Server Components are forbidden from importing
 * client-state libraries directly, hence the split.
 *
 * Future additions (M2+):
 *   - Wires up /threads fetch + StreamMessage pipeline (T061/T060).
 *   - Adds a breadcrumb header with the active thread title.
 */

import { PageShell } from "@/components/page-shell";

export default function HomePage(): React.JSX.Element {
  return (
    <main className="grid h-screen grid-cols-[var(--spacing-thread-sidebar)_1fr] overflow-hidden">
      <aside className="border-r border-border bg-background">
        <PageShell.ThreadListSidebar />
      </aside>
      <section className="flex h-full flex-col">
        <header className="border-b border-border px-6 py-3">
          <h1 className="text-base font-semibold">hochoy Deep Research</h1>
          <p className="text-xs text-muted-foreground">
            M1 — mock 对话流 / SSE 流式回显
          </p>
        </header>
        <PageShell.ChatArea />
      </section>
    </main>
  );
}
