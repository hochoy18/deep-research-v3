/**
 * research_frontend/postcss.config.mjs
 *
 * Per ADR-0007, the v4 pipeline uses only the official `@tailwindcss/postcss`
 * plugin — no `autoprefixer`, no `postcss-nested`. The `lightningcss` engine
 * handles prefixing + nesting natively.
 */

const config = {
  plugins: {
    "@tailwindcss/postcss": {},
  },
};

export default config;
