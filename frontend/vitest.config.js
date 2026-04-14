import { defineConfig } from "vitest/config";

export default defineConfig({
  esbuild: {
    jsx: "automatic",
    jsxImportSource: "react",
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["src/__tests__/setup.js"],
    include: ["src/**/*.{test,spec}.{js,jsx}"],
    coverage: {
      reporter: ["text", "lcov"],
    },
  },
});
