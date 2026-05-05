import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

import App from "../App";
import { FeatureAuthProvider } from "../platform/authProvider";

declare global {
  interface Window {
    __FEATURE_SHELL_AUTH__?: {
      version: "v1" | string;
      isAuthenticated?: boolean;
      userId?: string;
      userName?: string;
      email?: string;
      roles?: string[];
      accessToken?: string;
    };
  }
}

vi.mock("../services/apiClient", () => ({
  apiFetch: vi.fn(async () => ({
    json: async () => ({
      feature_key: "asset-inventory",
      authenticated: true,
      user: "Test User",
      items: [
        {
          id: "1",
          title: "Test item",
          description: "active",
        },
      ],
    }),
  })),
}));

afterEach(() => {
  delete window.__FEATURE_SHELL_AUTH__;
});

describe("App", () => {
  it("renders feature title and data", async () => {
    window.__FEATURE_SHELL_AUTH__ = {
      version: "v1",
      isAuthenticated: true,
      userId: "u1",
      userName: "Test User",
      email: "test@example.com",
      roles: ["developer"],
      accessToken: "token-123",
    };

    render(
      <FeatureAuthProvider>
        <App />
      </FeatureAuthProvider>
    );

    expect(screen.getByText("IT Asset Inventory")).toBeInTheDocument();

    await waitFor(() =>
      expect(screen.getByRole("listitem")).toHaveTextContent("Test item — active")
    );
  });
});

import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

import App from "../App";
import { FeatureAuthProvider } from "../platform/authProvider";

declare global {
  interface Window {
    __FEATURE_SHELL_AUTH__?: {
      version: "v1" | string;
      isAuthenticated?: boolean;
      userId?: string;
      userName?: string;
      email?: string;
      roles?: string[];
      accessToken?: string;
    };
  }
}

vi.mock("../services/apiClient", () => ({
  apiFetch: vi.fn(async () => ({
    json: async () => ({
      feature_key: "asset-inventory",
      authenticated: true,
      user: "Test User",
      items: [
        {
          id: "1",
          title: "Test item",
          description: "active",
        },
      ],
    }),
  })),
}));

afterEach(() => {
  delete window.__FEATURE_SHELL_AUTH__;
});

describe("App", () => {
  it("renders feature title and data", async () => {
    window.__FEATURE_SHELL_AUTH__ = {
      version: "v1",
      isAuthenticated: true,
      userId: "u1",
      userName: "Test User",
      email: "test@example.com",
      roles: ["developer"],
      accessToken: "token-123",
    };

    render(
      <FeatureAuthProvider>
        <App />
      </FeatureAuthProvider>
    );

    expect(screen.getByText("IT Asset Inventory")).toBeInTheDocument();

    await waitFor(() =>
      expect(screen.getByRole("listitem")).toHaveTextContent("Test item — active")
    );
  });

  it("shows auth-required message when shell auth is missing in entra mode", () => {
    render(
      <FeatureAuthProvider>
        <App />
      </FeatureAuthProvider>
    );

    expect(screen.getByText("IT Asset Inventory")).toBeInTheDocument();
    expect(
      screen.getByText("This feature requires shell authentication.")
    ).toBeInTheDocument();
  });
});