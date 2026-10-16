/**
 * research_frontend/tests/setup.ts
 *
 * Global Vitest setup file. Registered through `vitest.config.ts.setupFiles`.
 * Adds jest-dom matchers (toBeInTheDocument / toHaveTextContent / etc.) and
 * auto-cleans up the DOM after each test so cases cannot leak nodes into
 * subsequent suites.
 */

import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

afterEach(() => {
  cleanup();
});
