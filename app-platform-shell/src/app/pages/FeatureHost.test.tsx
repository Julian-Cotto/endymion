import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

import FeatureHost from "./FeatureHost";
import { useShellSession } from "../hooks/useShellSession";
import { bootstrapFeature } from "../../platform/bootstrap/bootstrapFeature";
import type { BootstrapFeature, BootstrapResponse } from "../../platform/contracts/bootstrapResponse";

vi.mock("../hooks/useShellSession", () => ({
  useShellSession: vi.fn(),
}));

vi.mock("../../platform/bootstrap/bootstrapFeature", () => ({
  bootstrapFeature: vi.fn(),
}));

const ordersFeature: BootstrapFeature = {
  featureKey: "orders",
  displayName: "Orders",
  route: "/orders",
  version: "1.0.0",
  nav: {
    label: "Orders",
    icon: "package",
  },
  frontend: {
    enabled: true,
    entryUrl: "http://localhost:3200/src/bootstrap-entry.tsx",
    mountFunction: "mount",
  },
  backend: {
    enabled: true,
    apiBaseUrl: "http://localhost:8100/api/orders",
    healthEndpoint: "/health",
  },
  authorization: {
    requiredPermissions: ["orders.view"],
    requiredFlags: ["orders.enabled"],
  },
  auth: {
    required: true,
    mode: "mock",
    shellAuthRequired: true,
    tokenForwarding: false,
    allowedDevModes: ["mock"],
    roles: [],
  },
};

const runtime: BootstrapResponse = {
  environment: "dev",
  user: {
    id: "u1",
    displayName: "Boris",
    email: "boris@example.com",
  },
  permissions: ["orders.view"],
  flags: {
    "orders.enabled": true,
  },
  features: [ordersFeature],
  metadata: {
    source: "bootstrap",
  },
};

describe("FeatureHost", () => {
  let consoleErrorSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    vi.clearAllMocks();
    consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    vi.mocked(useShellSession).mockReturnValue({
      isAuthenticated: true,
      userId: "u1",
      userName: "Boris",
      email: "boris@example.com",
      roles: ["orders.view"],
      accessToken: "token-123",
    } as never);
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
  });

  it("bootstraps the selected feature without loading runtime again", async () => {
    vi.mocked(bootstrapFeature).mockResolvedValue(undefined);

    render(<FeatureHost feature={ordersFeature} runtime={runtime} />);

    await waitFor(() => {
      expect(bootstrapFeature).toHaveBeenCalledTimes(1);
    });

    expect(bootstrapFeature).toHaveBeenCalledWith(
      expect.objectContaining({
        manifest: expect.objectContaining({
          featureKey: "orders",
          displayName: "Orders",
          basePath: "/orders",
          version: "1.0.0",
          environment: "dev",
          frontend: expect.objectContaining({
            enabled: true,
            entryUrl: "http://localhost:3200/src/bootstrap-entry.tsx",
            mountFunction: "mount",
          }),
          backend: expect.objectContaining({
            enabled: true,
            baseUrl: "http://localhost:8100/api/orders",
            healthEndpoint: "/health",
          }),
          auth: expect.objectContaining({
            required: true,
            mode: "mock",
            shellAuthRequired: true,
            tokenForwarding: false,
          }),
        }),
        session: expect.objectContaining({
          isAuthenticated: true,
          userId: "u1",
          roles: ["orders.view"],
        }),
        runtime: expect.objectContaining({
          version: "v1",
          environment: "dev",
          featureKey: "orders",
          route: "/orders",
          displayName: "Orders",
          backend: expect.objectContaining({
            baseUrl: "http://localhost:8100/api/orders",
            enabled: true,
            healthEndpoint: "/health",
          }),
          flags: {
            "orders.enabled": true,
          },
          permissions: ["orders.view"],
        }),
      }),
    );
  });

  it("renders an error message when feature bootstrap fails", async () => {
    vi.mocked(bootstrapFeature).mockRejectedValueOnce(new Error("Boom"));

    render(<FeatureHost feature={ordersFeature} runtime={runtime} />);

    expect(await screen.findByText("Feature load failed")).toBeInTheDocument();
    expect(await screen.findByText("Boom")).toBeInTheDocument();
  });

  it("runs cleanup when unmounted", async () => {
    const cleanup = vi.fn();

    vi.mocked(bootstrapFeature).mockResolvedValueOnce(cleanup);

    const rendered = render(<FeatureHost feature={ordersFeature} runtime={runtime} />);

    await waitFor(() => {
      expect(bootstrapFeature).toHaveBeenCalledTimes(1);
    });

    rendered.unmount();

    expect(cleanup).toHaveBeenCalledTimes(1);
  });
});