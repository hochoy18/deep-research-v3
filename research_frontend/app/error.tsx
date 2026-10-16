/**
 * research_frontend/app/error.tsx
 *
 * Root-level ErrorBoundary — Next.js App Router will automatically wrap the
 * entire route tree with this component when a child throws. It MUST be a
 * Client Component (App Router requirement: error.tsx must include
 * \"use client\").
 *
 * M1 behaviour: show a user-friendly retry card. We avoid leaking the
 * real error message in production (constitution I — minimal disclosure);
 * the full error is logged to the server via `console.error` which the
 * observability hook picks up.
 */

"use client";

import { useEffect } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}): React.JSX.Element {
  useEffect(() => {
    // Server-side observability: in M2+ this routes to Langfuse through
    // the same channel as backend errors. For M1 we keep console.error.
    console.error("[frontend] unhandled error", error);
  }, [error]);

  return (
    <main className="grid min-h-screen place-items-center bg-background p-8">
      <div className="max-w-md rounded-lg border border-border bg-background p-6 text-center shadow-sm">
        <h1 className="mb-2 text-lg font-semibold">出错了 / Something went wrong</h1>
        <p className="mb-4 text-sm text-muted-foreground">
          客户端遇到了未预期的错误。请稍后重试,或刷新页面。
        </p>
        <button
          type="button"
          onClick={() => reset()}
          className="rounded-md bg-brand-500 px-4 py-2 text-sm text-background hover:bg-brand-600"
        >
          重试
        </button>
      </div>
    </main>
  );
}
