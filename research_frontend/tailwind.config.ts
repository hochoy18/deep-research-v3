/**
 * research_frontend/tailwind.config.ts
 *
 * Per ADR-0007 (docs/adr/0007-tailwind-v4-css-first.md), M1 uses Tailwind v4
 * CSS-first configuration. **The single source of truth for design tokens
 * (colors, spacing, typography, dark variants) is `app/globals.css`**, NOT
 * this file.
 *
 * This file exists for the shadcn-style content glob + plugin registration
 * that Tailwind v4 still needs at the JS layer. All token literals live in
 * `@theme { ... }` inside globals.css.
 *
 * @see app/globals.css — design tokens (oklch palette, semantic vars)
 * @see postcss.config.mjs — @tailwindcss/postcss v4 plugin only
 */

// Tailwind v4 recommends exports NONE here; the CSS-first mode reads
// `@theme { ... }` from app/globals.css. We keep a placeholder so tooling
// (e.g. Prettier Tailwind IntelliSense) can discover content paths.
export default {
  // Reserved for future v4 plugin registration (e.g. @tailwindcss/forms
  // once it ships a stable v4 build). Adding plugins here MUST come with
  // an ADR update — see docs/adr/0007-tailwind-v4-css-first.md §Consequences.
};
