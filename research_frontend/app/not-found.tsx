/**
 * research_frontend/app/not-found.tsx
 *
 * 404 page. Pairs with error.tsx to give the app a friendly offline
 * experience when users hit missing thread ids (the [thread_id] segment
 * 404s land here).
 */

import Link from "next/link";

export default function NotFound(): React.JSX.Element {
  return (
    <main className="grid min-h-screen place-items-center bg-background p-8">
      <div className="max-w-md text-center">
        <h1 className="mb-2 text-3xl font-bold">404</h1>
        <p className="mb-4 text-sm text-muted-foreground">
          找不到这个会话。
        </p>
        <Link
          href="/"
          className="text-sm text-brand-600 underline-offset-4 hover:underline"
        >
          返回主页
        </Link>
      </div>
    </main>
  );
}
