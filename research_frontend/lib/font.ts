/**
 * research_frontend/lib/font.ts
 *
 * Centralised font configuration so layout/page can share the same family
 * without each importing next/font/google directly. Using Geist Sans + Geist
 * Mono (the Next.js 16 default; great CJK fallback via the CSS @font-face
 * rules emitted by next/font).
 *
 * Why a separate file: layout.tsx must stay as a Server Component with
 * minimal synchronous imports; the font loader is best split out so it can
 * be cached and stubbed in unit tests (vitest jsdom).
 */

import { Geist, Geist_Mono } from "next/font/google";

export const fontSans = Geist({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-sans",
});

export const fontMono = Geist_Mono({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-mono",
});
