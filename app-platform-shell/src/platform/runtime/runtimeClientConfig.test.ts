import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  getBootstrapUrl,
  getRegistryRuntimeUrl,
  getRuntimeSourceMode,
} from "./runtimeClientConfig";

describe("runtimeClientConfig", () => {
  const originalRuntimeSourceMode = import.meta.env.VITE_RUNTIME_SOURCE_MODE;
  const originalRegistryRuntimeUrl = import.meta.env.VITE_REGISTRY_RUNTIME_URL;
  const originalBootstrapUrl = import.meta.env.VITE_BOOTSTRAP_URL;

  beforeEach(() => {
    vi.unstubAllEnvs();

    vi.stubEnv(
      "VITE_RUNTIME_SOURCE_MODE",
      originalRuntimeSourceMode ?? "",
    );
    vi.stubEnv(
      "VITE_REGISTRY_RUNTIME_URL",
      originalRegistryRuntimeUrl ?? "",
    );
    vi.stubEnv(
      "VITE_BOOTSTRAP_URL",
      originalBootstrapUrl ?? "",
    );
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("returns bootstrap mode when explicitly configured", () => {
    vi.stubEnv("VITE_RUNTIME_SOURCE_MODE", "bootstrap");
    expect(getRuntimeSourceMode()).toBe("bootstrap");
  });

  it("returns registry mode when configured", () => {
    vi.stubEnv("VITE_RUNTIME_SOURCE_MODE", "registry");
    expect(getRuntimeSourceMode()).toBe("registry");
  });

  it("falls back to bootstrap mode for unknown values", () => {
    vi.stubEnv("VITE_RUNTIME_SOURCE_MODE", "something-else");
    expect(getRuntimeSourceMode()).toBe("bootstrap");
  });

  it("returns configured registry runtime URL", () => {
    vi.stubEnv(
      "VITE_REGISTRY_RUNTIME_URL",
      "http://localhost:8001/api/runtime/features",
    );

    expect(getRegistryRuntimeUrl()).toBe(
      "http://localhost:8001/api/runtime/features",
    );
  });

  it("returns configured bootstrap URL", () => {
    vi.stubEnv(
      "VITE_BOOTSTRAP_URL",
      "http://localhost:8001/api/shell/bootstrap",
    );

    expect(getBootstrapUrl()).toBe(
      "http://localhost:8001/api/shell/bootstrap",
    );
  });
});