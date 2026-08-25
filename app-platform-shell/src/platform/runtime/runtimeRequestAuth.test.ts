import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  clearShellSessionSnapshot,
  setShellSessionSnapshot,
} from "../session/shellSessionStore";
import { buildRuntimeRequestHeaders } from "./runtimeRequestAuth";

vi.mock("../auth/msalConfig", () => ({
  getShellAuthMode: vi.fn(() => "mock"),
}));

describe("buildRuntimeRequestHeaders", () => {
  beforeEach(() => {
    clearShellSessionSnapshot();
    vi.clearAllMocks();
  });

  afterEach(() => {
    clearShellSessionSnapshot();
  });

  it("returns Accept header when no session is present", () => {
    expect(buildRuntimeRequestHeaders()).toEqual({
      Accept: "application/json",
    });
  });

  it("includes Authorization header when access token is present", () => {
    setShellSessionSnapshot({
      isAuthenticated: true,
      accessToken: "token-123",
    });

    expect(buildRuntimeRequestHeaders()).toEqual({
      Accept: "application/json",
      Authorization: "Bearer token-123",
    });
  });

  it("includes debug identity headers in mock mode", () => {
    setShellSessionSnapshot({
      isAuthenticated: true,
      userId: "dev-user-1",
      userName: "Boris Moshkovich",
      email: "bmoshkovich@example.com",
      roles: ["orders.view", "catalog.view"],
      accessToken: "dev-token",
    });

    expect(buildRuntimeRequestHeaders()).toEqual({
      Accept: "application/json",
      Authorization: "Bearer dev-token",
      "X-Debug-User-Id": "dev-user-1",
      "X-Debug-User-Name": "Boris Moshkovich",
      "X-Debug-Email": "bmoshkovich@example.com",
      "X-Debug-Roles": "orders.view,catalog.view",
    });
  });

  it("trims and skips empty debug roles", () => {
    setShellSessionSnapshot({
      isAuthenticated: true,
      roles: [" orders.view ", "", "  ", "catalog.view"],
    });

    expect(buildRuntimeRequestHeaders()).toEqual({
      Accept: "application/json",
      "X-Debug-Roles": "orders.view,catalog.view",
    });
  });
});