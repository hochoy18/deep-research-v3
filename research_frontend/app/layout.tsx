/**
 * research_frontend/app/layout.tsx
 *
 * Root layout for the Deep Research Agent M1 frontend (T033).
 *
 * Mandatory from spec FR-002 + constitution V/VI:
 *   - Server Component (no "use client" here).
 *   - Mounts global ErrorBoundary (`app/error.tsx`) + 404 (`app/not-found.tsx`)
 *     automatically via App Router conventions.
 *   - Loads Geist Sans + Geist Mono via next/font, exposed as CSS variables
 *     (--font-sans / --font-mono) consumed in `app/globals.css`.
 *   - Locale-tagged <html lang=\"zh-CN\"> because the chat UI is targeted at
 *     a CJK audience (DEEP-RESEARCH-M1 §3 locale requirement).
 *   - Metadata.title / description wired so PR-007 (default tab label) works
 *     in dev / build.
 */

import type { Metadata } from "next";
import "./globals.css";
import { fontSans, fontMono } from "@/lib/font";

export const metadata: Metadata = {
  title: "Deep Research Agent",
  description: "hochoy Deep Research — M1 mock chat frontend (Next.js 16)",
  robots: { index: false, follow: false },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}): React.JSX.Element {
  return (
    <html
      lang="zh-CN"
      className={`${fontSans.variable} ${fontMono.variable}`}
      suppressHydrationWarning
    >
      <body className="min-h-screen bg-background font-sans text-foreground antialiased">
        {children}
      </body>
    </html>
  );
}
