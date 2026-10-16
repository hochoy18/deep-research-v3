/**
 * research_frontend/lib/cn.ts
 *
 * Tiny classname helper that merges clsx + tailwind-merge to deduplicate
 * conflicting Tailwind classes (e.g. \"p-2 p-4\" → \"p-4\").
 */

import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
