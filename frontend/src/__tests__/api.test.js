import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock localStorage
const localStorageMock = (() => {
  let store = {};
  return {
    getItem: (key) => store[key] || null,
    setItem: (key, value) => { store[key] = value; },
    removeItem: (key) => { delete store[key]; },
    clear: () => { store = {}; },
  };
})();
Object.defineProperty(global, "localStorage", { value: localStorageMock });

describe("API client", () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.restoreAllMocks();
  });

  it("exports api object with expected methods", async () => {
    const mod = await import("../lib/api.js");
    expect(mod.api).toBeDefined();
    expect(typeof mod.api.login).toBe("function");
    expect(typeof mod.api.register).toBe("function");
    expect(typeof mod.api.getMe).toBe("function");
  });

  it("exports project methods on api object", async () => {
    const mod = await import("../lib/api.js");
    expect(typeof mod.api.getProjects).toBe("function");
    expect(typeof mod.api.getProject).toBe("function");
    expect(typeof mod.api.createProject).toBe("function");
    expect(typeof mod.api.runProject).toBe("function");
  });

  it("exports report methods on api object", async () => {
    const mod = await import("../lib/api.js");
    expect(typeof mod.api.getReports).toBe("function");
    expect(typeof mod.api.getReport).toBe("function");
    expect(typeof mod.api.shareReport).toBe("function");
  });

  it("exports setOnUnauthorized function", async () => {
    const mod = await import("../lib/api.js");
    expect(typeof mod.setOnUnauthorized).toBe("function");
    const fn = vi.fn();
    mod.setOnUnauthorized(fn);
    // Verify no error thrown
    expect(true).toBe(true);
  });

  it("exports other utility methods on api object", async () => {
    const mod = await import("../lib/api.js");
    expect(typeof mod.api.uploadFile).toBe("function");
    expect(typeof mod.api.getSettings).toBe("function");
    expect(typeof mod.api.getDashboardStats).toBe("function");
    expect(typeof mod.api.healthCheck).toBe("function");
  });
});
