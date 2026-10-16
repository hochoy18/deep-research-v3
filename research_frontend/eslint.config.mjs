// research_frontend/eslint.config.mjs — M1 flat config (eslint 9 + typescript-eslint)
//
// M1 Converge-Gate #9 lint workaround:
// - `next lint` removed in Next.js 16 → use `eslint .` + flat config
// - `next/core-web-vitals` triggers TS 7 / circular-ref issues with
//   typescript-eslint + FlatCompat, so we use a minimal config here.
// - TypeScript rules delegated to `tsc --noEmit` + vitest type-check.
// - Replace with `next/core-web-vitals` once typescript-eslint adds
//   TS 7 support (see github.com/typescript-eslint/typescript-eslint#10940).
import tsParser from "@typescript-eslint/parser";

export default [
  {
    ignores: [
      "node_modules/**",
      ".next/**",
      "coverage/**",
      "dist/**",
      "*.config.*",
      "next-env.d.ts",
    ],
  },
  {
    files: ["**/*.{ts,tsx,js,jsx}"],
    languageOptions: {
      parser: tsParser,
      ecmaVersion: "latest",
      sourceType: "module",
      parserOptions: {
        ecmaFeatures: { jsx: true },
      },
      globals: {
        // Browser
        window: "readonly",
        document: "readonly",
        console: "readonly",
        // Node test env
        process: "readonly",
        // Vitest globals (vitest.config.ts: globals: true)
        describe: "readonly",
        it: "readonly",
        test: "readonly",
        expect: "readonly",
        beforeEach: "readonly",
        afterEach: "readonly",
        beforeAll: "readonly",
        afterAll: "readonly",
        vi: "readonly",
        render: "readonly",
        screen: "readonly",
      },
    },
    rules: {
      "no-undef": "off", // typescript-eslint handles this better
      "no-unused-vars": "off", // TS 5.7 has its own
      "no-console": ["warn", { allow: ["warn", "error"] }],
      "prefer-const": "error",
      "no-var": "error",
    },
  },
];
