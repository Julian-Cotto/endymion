import { describe, expect, it } from "vitest";

import type {
  ShellFeatureAuthContractV1,
  ShellFeatureRuntimeContractV1,
} from "./shellFeatureAuth";

describe("shell runtime/auth contract v1", () => {
  it("supports auth contract v1 shape", () => {
    const auth: ShellFeatureAuthContractV1 = {
      version: "v1",
      isAuthenticated: true,
      authMode: "mock",
      userId: "u1",
      userName: "Boris",
      email: "boris@example.com",
      roles: ["developer"],
      accessToken: "token-123",
    };

    expect(auth.version).toBe("v1");
    expect(auth.isAuthenticated).toBe(true);
    expect(auth.authMode).toBe("mock");
  });

  it("supports runtime contract v1 shape", () => {
    const runtime: ShellFeatureRuntimeContractV1 = {
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
      flags: {
        "orders.enabled": true,
      },
      permissions: ["orders.view"],
    };

    expect(runtime.version).toBe("v1");
    expect(runtime.featureKey).toBe("orders");
    expect(runtime.backend?.baseUrl).toBe("http://localhost:8100/api/orders");
  });
});