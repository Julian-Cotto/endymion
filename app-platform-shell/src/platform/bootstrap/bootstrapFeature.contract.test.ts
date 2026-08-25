import { beforeEach, describe, expect, it, vi } from "vitest";

import { bootstrapFeature } from "./bootstrapFeature";
import type { FeatureManifest } from "../contracts/featureManifest";

describe("bootstrapFeature v1 mount contract", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    delete globalThis.__dynamicImportForTest__;
  });

  it("mounts feature with manifest, session, and runtime provided by the Shell", async () => {
    const mount = vi.fn(async () => undefined);

    globalThis.__dynamicImportForTest__ = vi.fn(async () => ({
      mount,
    }));

    const manifest: FeatureManifest = {
      featureKey: "orders",
      displayName: "Orders",
      basePath: "/orders",
      version: "1.0.0",
      environment: "local",
      frontend: {
        enabled: true,
        entryUrl: "http://localhost:3200/src/bootstrap-entry.tsx",
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
        tokenForwarding: false,
        tokenStrategy: "none",
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

    const container = document.createElement("div");

    await bootstrapFeature({
      manifest,
      container,
      session,
      runtime,
    });

    expect(mount).toHaveBeenCalledTimes(1);
    expect(mount).toHaveBeenCalledWith(
      container,
      expect.objectContaining({
        manifest: expect.objectContaining({
          featureKey: "orders",
          frontend: expect.objectContaining({
            entryUrl: "http://localhost:3200/src/bootstrap-entry.tsx",
          }),
        }),
        session: expect.objectContaining({
          userId: "u1",
          roles: ["orders.view"],
        }),
        runtime: expect.objectContaining({
          version: "v1",
          featureKey: "orders",
          route: "/orders",
          permissions: ["orders.view"],
          flags: {
            "orders.enabled": true,
          },
        }),
      }),
    );
  });
});