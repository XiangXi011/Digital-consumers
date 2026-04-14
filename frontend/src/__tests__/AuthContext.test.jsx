import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, act, waitFor } from "@testing-library/react";
import { AuthProvider, useAuth } from "../contexts/AuthContext.jsx";

// ── Helpers ──────────────────────────────────────────────────────────────────

function TestConsumer() {
  const { user, token, loading, login, register, logout } = useAuth();
  return (
    <div>
      <span data-testid="loading">{String(loading)}</span>
      <span data-testid="user">{user ? user.email : "none"}</span>
      <span data-testid="token">{token || "none"}</span>
      <button onClick={() => login("a@b.com", "pw")}>login</button>
      <button onClick={() => register("a@b.com", "pw", "A")}>register</button>
      <button onClick={logout}>logout</button>
    </div>
  );
}

const TOKEN_KEY = "access_token";
const REFRESH_KEY = "refresh_token";

// ── Tests ────────────────────────────────────────────────────────────────────

describe("AuthContext", () => {
  let fetchSpy;

  beforeEach(() => {
    localStorage.clear();
    fetchSpy = vi.spyOn(global, "fetch");
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("starts loading then resolves to unauthenticated when no token", async () => {
    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    // AuthProvider synchronously detects no token in useEffect, so loading resolves quickly
    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("false");
    });
    expect(screen.getByTestId("user").textContent).toBe("none");
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("validates existing token on mount via /api/auth/me", async () => {
    localStorage.setItem(TOKEN_KEY, "existing-token");

    fetchSpy.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ email: "user@test.com", role: "editor" }),
    });

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("user").textContent).toBe("user@test.com");
    });
    expect(fetchSpy).toHaveBeenCalledWith(
      "/api/auth/me",
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer existing-token" }),
      })
    );
  });

  it("attempts refresh when /api/auth/me returns 401", async () => {
    localStorage.setItem(TOKEN_KEY, "bad-token");
    localStorage.setItem(REFRESH_KEY, "refresh-token");

    // 1st call: /api/auth/me fails
    fetchSpy.mockResolvedValueOnce({ ok: false });
    // 2nd call: /api/auth/refresh succeeds
    fetchSpy.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ access_token: "new-access", refresh_token: "new-refresh" }),
    });
    // 3rd call: retry /api/auth/me with new token
    fetchSpy.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ email: "refreshed@test.com", role: "viewer" }),
    });

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("user").textContent).toBe("refreshed@test.com");
    });
    expect(localStorage.getItem(TOKEN_KEY)).toBe("new-access");
    expect(localStorage.getItem(REFRESH_KEY)).toBe("new-refresh");
  });

  it("logs out when refresh also fails", async () => {
    localStorage.setItem(TOKEN_KEY, "bad-token");
    localStorage.setItem(REFRESH_KEY, "bad-refresh");

    // /api/auth/me fails
    fetchSpy.mockResolvedValueOnce({ ok: false });
    // /api/auth/refresh fails
    fetchSpy.mockResolvedValueOnce({ ok: false });

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("user").textContent).toBe("none");
    });
    expect(localStorage.getItem(TOKEN_KEY)).toBeNull();
    expect(localStorage.getItem(REFRESH_KEY)).toBeNull();
  });

  it("login stores tokens and updates user", async () => {
    fetchSpy.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        access_token: "acc",
        refresh_token: "ref",
        user: { email: "new@test.com" },
      }),
    });

    // After login sets token, AuthProvider useEffect fires /api/auth/me
    fetchSpy.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ email: "new@test.com", role: "editor" }),
    });

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    // Wait for initial loading to finish
    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("false");
    });

    await act(async () => {
      fireEvent.click(screen.getByText("login"));
    });

    expect(localStorage.getItem(TOKEN_KEY)).toBe("acc");
    expect(localStorage.getItem(REFRESH_KEY)).toBe("ref");
  });

  it("logout clears tokens and user", async () => {
    localStorage.setItem(TOKEN_KEY, "tok");
    fetchSpy.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ email: "u@t.com", role: "viewer" }),
    });

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("user").textContent).toBe("u@t.com");
    });

    await act(async () => {
      fireEvent.click(screen.getByText("logout"));
    });

    expect(screen.getByTestId("user").textContent).toBe("none");
    expect(localStorage.getItem(TOKEN_KEY)).toBeNull();
  });
});
