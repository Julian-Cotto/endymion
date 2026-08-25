import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  clearShellSessionSnapshot,
  setShellSessionSnapshot,
} from "../session/shellSessionStore";
import { loadRegistryRuntimeResponse } from "./loadRegistryRuntimeResponse";

describe("loadRegistryRuntimeResponse", () => {
  beforeEach(() => {
    clearShellSessionSnapshot();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    clearShellSessionSnapshot();
  });

  it("calls fetch with Accept header only when there is no token", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({
        environment: "local",
        permissions: [],
        flags: {},
        features: [],
      }),
    } as never);

    await loadRegistryRuntimeResponse(
      "http://localhost:8001/api/runtime/features",
    );

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8001/api/runtime/features",
      expect.objectContaining({
        method: "GET",
        headers: {
          Accept: "application/json",
        },
      }),
    );
  });

  it("forwards bearer token when present", async () => {
    setShellSessionSnapshot({
      isAuthenticated: true,
      accessToken: "token-123",
    });

    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({
        environment: "local",
        permissions: [],
        flags: {},
        features: [],
      }),
    } as never);

    await loadRegistryRuntimeResponse(
      "http://localhost:8001/api/runtime/features",
    );

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8001/api/runtime/features",
      expect.objectContaining({
        method: "GET",
        headers: {
          Accept: "application/json",
          Authorization: "Bearer token-123",
        },
      }),
    );
  });
});