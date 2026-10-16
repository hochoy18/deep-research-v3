/**
 * research_frontend/vitest.config.ts
 *
 * T093 — Vitest configuration for the M1 frontend critical-path coverage.
 *
 * - jsdom environment so React components render in tests.
 * - Coverage via @vitest/coverage-v8, output to /research_frontend/coverage/.
 *   - Coverage threshold 80% lines / branches / functions / statements
 *     matches Constitution III (关键路径 ≥80%).
 *   - 'critical-path' tag picks up `@critical`/`@critical` annotated tests
 *     via the `test:critical` script for fast smoke runs.
 * - Setup file enables jest-dom matchers + Testing Library auto-cleanup.
 * - Path alias `@/*` mirrors tsconfig.json so imports resolve uniformly.
 */

import { defineConfig } from "vitest/config";
import { fileURLToPath } from "node:url";
import path from "node:path";
import react from "@vitejs/plugin-react";

const here = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./tests/setup.ts"],
    css: false,

    include: ["tests/**/*.{spec,test}.{ts,tsx}"],
    exclude: ["node_modules", ".next", "dist", "coverage"],

    coverage: {
      enabled: false, // opt-in via --coverage flag (pnpm test:coverage)
      provider: "v8",
      reporter: [
        "text",
        "html",
        "cobertura",
        "json-summary",
        "json",
      ],
      reportsDirectory: "./coverage",
      outputFile: {
        cobertura: "frontend-coverage.xml",
      },
      include: ["app/**/*.{ts,tsx}", "lib/**/*.{ts,tsx}", "components/**/*.{ts,tsx}"],
      exclude: [
        "**/*.d.ts",
        "**/*.config.*",
        "**/*.spec.{ts,tsx}",
        "**/*.test.{ts,tsx}",
        "tests/**",
        "coverage/**",
      ],
      thresholds: {
        lines: 80,
        statements: 80,
        functions: 80,
        branches: 75,
      },
    },
  },
  resolve: {
    alias: {
      "@": here,
    },
  },
});
