import { beforeEach, describe, expect, it, vi } from "vitest";

import { bootstrapFeature } from "./bootstrapFeature";
import type { FeatureManifest } from "../contracts/featureManifest";
import { loadFeatureManifest } from "../registry/loadFeatureManifest";
import {
  clearFeatureShellAuth,
  injectFeatureShellAuth,
} from "../auth/injectFeatureShellAuth";
import {
  clearFeatureShellRuntime,
  injectFeatureShellRuntime,
} from "../auth/injectFeatureShellRuntime";
import { resolveShellFeatureAuth } from "../auth/resolveShellFeatureAuth";

vi.mock("../registry/loadFeatureManifest", () => ({
  loadFeatureManifest: vi.fn(),
}));

vi.mock("../auth/injectFeatureShellAuth", () => ({
  clearFeatureShellAuth: vi.fn(),
  injectFeatureShellAuth: vi.fn(),
}));

vi.mock("../auth/injectFeatureShellRuntime", () => ({
  clearFeatureShellRuntime: vi.fn(),
  injectFeatureShellRuntime: vi.fn(),
}));

vi.mock("../auth/resolveShellFeatureAuth", () => ({
  resolveShellFeatureAuth: vi.fn(),
}));

const manifest: FeatureManifest = {
  featureKey: "orders",
  displayName: "Orders",
  basePath: "/orders",
  version: "1.0.0",
  environment: "local",
  frontend: {
    enabled: true,
    entryUrl: "/remote/orders/bootstrap.js",
    mountFunction: "mount",
  },
  backend: {
    enabled: true,
    baseUrl: "http://localhost:8100/api/orders",
    healthEndpoint: "/health",
  },
  auth: {
    required: true,
    mode: "mock",
    shellAuthRequired: true,
    tokenForwarding: true,
    tokenStrategy: "bearer",
    allowedDevModes: ["mock"],
    roles: [],
  },
};

const session = {
  isAuthenticated: true,
  userId: "u1",
  userName: "Boris",
  email: "boris@example.com",
  roles: ["orders.view"],
  accessToken: "token-123",
};

const runtime = {
  version: "v1" as const,
  environment: "local",
  featureKey: "orders",
  route: "/orders",
  displayName: "Orders",
  backend: {
    baseUrl: "http://localhost:8100/api/orders",
    enabled: true,
    healthEndpoint: "/health",
  },
  flags: {
    "orders.enabled": true,
  },
  permissions: ["orders.view"],
};

describe("bootstrapFeature", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    delete globalThis.__dynamicImportForTest__;
  });

  it("calls remote mount with container as first argument and manifest/session/runtime as second argument", async () => {
    const mount = vi.fn(async () => undefined);
    const container = document.createElement("div");

    vi.mocked(resolveShellFeatureAuth).mockReturnValue({
      version: "v1",
      isAuthenticated: true,
      authMode: "mock",
      accessToken: "token-123",
      userId: "u1",
      userName: "Boris",
      email: "boris@example.com",
      roles: ["orders.view"],
    });

    globalThis.__dynamicImportForTest__ = vi.fn(async () => ({
      mount,
    }));

    await bootstrapFeature({
      manifest,
      container,
      session,
      runtime,
    });

    expect(clearFeatureShellAuth).toHaveBeenCalledTimes(1);
    expect(injectFeatureShellAuth).toHaveBeenCalledTimes(1);
    expect(clearFeatureShellRuntime).toHaveBeenCalledTimes(1);
    expect(injectFeatureShellRuntime).toHaveBeenCalledWith(runtime);

    expect(mount).toHaveBeenCalledTimes(1);
    expect(mount).toHaveBeenCalledWith(
      container,
      expect.objectContaining({
        manifest,
        session,
        runtime,
      }),
    );
  });

  it("loads manifest from URL when manifestUrl is provided", async () => {
    const mount = vi.fn(async () => undefined);
    const container = document.createElement("div");

    vi.mocked(loadFeatureManifest).mockResolvedValue(manifest);
    vi.mocked(resolveShellFeatureAuth).mockReturnValue(undefined);

    globalThis.__dynamicImportForTest__ = vi.fn(async () => ({
      mount,
    }));

    await bootstrapFeature({
      manifestUrl: "http://localhost:9999/manifest.json",
      container,
      session,
    });

    expect(loadFeatureManifest).toHaveBeenCalledWith(
      "http://localhost:9999/manifest.json",
    );

    expect(clearFeatureShellAuth).toHaveBeenCalledTimes(1);
    expect(clearFeatureShellRuntime).toHaveBeenCalledTimes(1);

    expect(mount).toHaveBeenCalledWith(
      container,
      expect.objectContaining({
        manifest,
        session,
        runtime: expect.objectContaining({
          version: "v1",
          environment: "local",
          featureKey: "orders",
          route: "/orders",
          displayName: "Orders",
          backend: {
            baseUrl: "http://localhost:8100/api/orders",
            enabled: true,
            healthEndpoint: "/health",
          },
          flags: {},
          permissions: [],
        }),
      }),
    );
  });

  it("throws when neither manifest nor manifestUrl is provided", async () => {
    await expect(
      bootstrapFeature({
        container: document.createElement("div"),
        session,
      }),
    ).rejects.toThrow("bootstrapFeature requires either manifest or manifestUrl.");
  });

  it("throws when remote module does not export the configured mount function", async () => {
    vi.mocked(resolveShellFeatureAuth).mockReturnValue(undefined);

    globalThis.__dynamicImportForTest__ = vi.fn(async () => ({}));

    await expect(
      bootstrapFeature({
        manifest,
        container: document.createElement("div"),
        session,
        runtime,
      }),
    ).rejects.toThrow(
      "Remote module for feature 'orders' does not export mount function 'mount'.",
    );
  });

  it("clears shell auth before injecting resolved shell auth", async () => {
    const shellAuth = {
      version: "v1" as const,
      isAuthenticated: true,
      authMode: "mock" as const,
      accessToken: "token-123",
      userId: "u1",
      userName: "Boris",
      email: "boris@example.com",
      roles: ["orders.view"],
    };

    const mount = vi.fn(async () => undefined);

    vi.mocked(resolveShellFeatureAuth).mockReturnValue(shellAuth);

    globalThis.__dynamicImportForTest__ = vi.fn(async () => ({
      mount,
    }));

    await bootstrapFeature({
      manifest,
      container: document.createElement("div"),
      session,
      runtime,
    });

    expect(clearFeatureShellAuth).toHaveBeenCalledTimes(1);
    expect(injectFeatureShellAuth).toHaveBeenCalledWith({
      isAuthenticated: true,
      authMode: "mock",
      accessToken: "token-123",
      userId: "u1",
      userName: "Boris",
      email: "boris@example.com",
      roles: ["orders.view"],
    });
  });
});