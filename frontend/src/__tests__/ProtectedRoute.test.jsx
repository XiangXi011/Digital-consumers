import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

// Mock the AuthContext module
vi.mock("../contexts/AuthContext.jsx", () => ({
  useAuth: vi.fn(),
}));

import { useAuth } from "../contexts/AuthContext.jsx";
import ProtectedRoute from "../components/ProtectedRoute.jsx";

function renderWithRouter(ui, { initialEntries = ["/protected"] } = {}) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <Routes>
        <Route path="/login" element={<div>Login Page</div>} />
        <Route path="/protected" element={ui} />
      </Routes>
    </MemoryRouter>
  );
}

describe("ProtectedRoute", () => {
  it("shows spinner while loading", () => {
    useAuth.mockReturnValue({ user: null, loading: true });

    renderWithRouter(
      <ProtectedRoute>
        <div>Secret</div>
      </ProtectedRoute>
    );

    // Spinner: animate-spin class on a div
    expect(document.querySelector(".animate-spin")).toBeDefined();
    expect(screen.queryByText("Secret")).toBeNull();
  });

  it("redirects to /login when not authenticated", () => {
    useAuth.mockReturnValue({ user: null, loading: false });

    renderWithRouter(
      <ProtectedRoute>
        <div>Secret</div>
      </ProtectedRoute>
    );

    expect(screen.getByText("Login Page")).toBeDefined();
    expect(screen.queryByText("Secret")).toBeNull();
  });

  it("renders children when authenticated", () => {
    useAuth.mockReturnValue({
      user: { email: "a@b.com", role: "editor" },
      loading: false,
    });

    renderWithRouter(
      <ProtectedRoute>
        <div>Secret Content</div>
      </ProtectedRoute>
    );

    expect(screen.getByText("Secret Content")).toBeDefined();
  });
});
