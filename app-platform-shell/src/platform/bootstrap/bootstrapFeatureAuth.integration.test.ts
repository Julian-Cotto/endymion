import { describe, expect, it } from "vitest";

import { resolveShellFeatureAuth } from "../auth/resolveShellFeatureAuth";

describe("shell → feature auth integration", () => {
  it("injects entra auth contract for a token-forwarding feature", () => {
    const manifest = {
      featureKey: "orders",
      displayName: "Orders",
      version: "1.0.0",
      auth: {
        required: true,
        mode: "entra",
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

    const shellAuth = resolveShellFeatureAuth(manifest as never, session as never);

    expect(shellAuth).toEqual({
      version: "v1",
      authMode: "entra",
      isAuthenticated: true,
      userId: "u1",
      userName: "Boris",
      email: "boris@example.com",
      roles: ["orders.view"],
      accessToken: "token-123",
    });
  });

  it("returns unauthenticated contract when entra token forwarding is required but token is missing", () => {
    const manifest = {
      featureKey: "orders",
      displayName: "Orders",
      version: "1.0.0",
      auth: {
        required: true,
        mode: "entra",
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
    };

    const shellAuth = resolveShellFeatureAuth(manifest as never, session as never);

    expect(shellAuth).toEqual({
      version: "v1",
      authMode: "entra",
      isAuthenticated: false,
      userId: "u1",
      userName: "Boris",
      email: "boris@example.com",
      roles: ["orders.view"],
    });
  });
});