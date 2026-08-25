import { describe, expect, it } from "vitest";

import { resolveShellFeatureAuth } from "./resolveShellFeatureAuth";
import type { FeatureManifest } from "../contracts/featureManifest";
import type { ShellUserSession } from "./sessionTypes";

function buildManifest(
  overrides: Partial<FeatureManifest["auth"]> = {},
): FeatureManifest {
  return {
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
      tokenForwarding: true,
      tokenStrategy: "bearer",
      allowedDevModes: ["mock"],
      roles: [],
      ...overrides,
    },
  };
}

function buildSession(
  overrides: Partial<ShellUserSession> = {},
): ShellUserSession {
  return {
    isAuthenticated: true,
    userId: "u1",
    userName: "Boris",
    email: "boris@example.com",
    roles: ["orders.view"],
    accessToken: "token-123",
    ...overrides,
  };
}

describe("resolveShellFeatureAuth", () => {
  it("returns undefined when feature auth is not required", () => {
    const manifest = buildManifest({
      required: false,
      shellAuthRequired: false,
      tokenForwarding: false,
    });

    const result = resolveShellFeatureAuth(manifest, buildSession());

    expect(result).toBeUndefined();
  });

  it("returns mock auth contract without token forwarding", () => {
    const manifest = buildManifest({
      mode: "mock",
      tokenForwarding: false,
      tokenStrategy: "none",
    });

    const result = resolveShellFeatureAuth(manifest, buildSession());

    expect(result).toEqual({
      version: "v1",
      authMode: "mock",
      isAuthenticated: true,
      accessToken: "token-123",
      userId: "u1",
      userName: "Boris",
      email: "boris@example.com",
      roles: ["orders.view"],
    });
  });

  it("returns entra auth contract with forwarded bearer token", () => {
    const manifest = buildManifest({
      mode: "entra",
      tokenForwarding: true,
      tokenStrategy: "bearer",
    });

    const result = resolveShellFeatureAuth(manifest, buildSession());

    expect(result).toEqual({
      version: "v1",
      authMode: "entra",
      isAuthenticated: true,
      accessToken: "token-123",
      userId: "u1",
      userName: "Boris",
      email: "boris@example.com",
      roles: ["orders.view"],
    });
  });

  it("returns unauthenticated contract when token forwarding is required but token is missing", () => {
    const manifest = buildManifest({
      mode: "entra",
      tokenForwarding: true,
      tokenStrategy: "bearer",
    });

    const result = resolveShellFeatureAuth(
      manifest,
      buildSession({
        accessToken: undefined,
      }),
    );

    expect(result).toEqual({
      version: "v1",
      authMode: "entra",
      isAuthenticated: false,
      userId: "u1",
      userName: "Boris",
      email: "boris@example.com",
      roles: ["orders.view"],
    });
  });

  it("keeps permission-shaped roles unchanged", () => {
    const result = resolveShellFeatureAuth(
      buildManifest(),
      buildSession({
        roles: ["orders.view", "orders.edit", "catalog.view"],
      }),
    );

    expect(result?.roles).toEqual([
      "orders.view",
      "orders.edit",
      "catalog.view",
    ]);
  });
});