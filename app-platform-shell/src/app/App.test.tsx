import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import App from "./App";
import { loadRuntimeFeatures } from "../platform/runtime/loadRuntimeFeatures";
import type {
  BootstrapFeature,
  BootstrapResponse,
} from "../platform/contracts/bootstrapResponse";

vi.mock("../platform/auth/msalConfig", async () => {
  const actual = await vi.importActual<typeof import("../platform/auth/msalConfig")>(
    "../platform/auth/msalConfig",
  );

  return {
    ...actual,
    getShellAuthMode: () => "mock",
  };
});

vi.mock("../platform/runtime/loadRuntimeFeatures", () => ({
  loadRuntimeFeatures: vi.fn(),
}));

vi.mock("./pages/FeatureHost", () => ({
  default: ({
    feature,
    runtime,
  }: {
    feature: BootstrapFeature;
    runtime: BootstrapResponse;
  }) => (
    <div data-testid="feature-host">
      FeatureHost: {feature.featureKey} / {runtime.environment}
    </div>
  ),
}));

const ordersFeature: BootstrapFeature = {
  featureKey: "orders",
  displayName: "Orders",
  route: "/orders",
  version: "1.0.0",
  nav: {
    label: "Orders",
    icon: "package",
    order: 20,
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

const catalogFeature: BootstrapFeature = {
  featureKey: "catalog",
  displayName: "Catalog",
  route: "/catalog",
  version: "1.0.0",
  nav: {
    label: "Catalog",
    icon: "box",
    order: 10,
  },
  frontend: {
    enabled: true,
    entryUrl: "http://localhost:3300/src/bootstrap-entry.tsx",
    mountFunction: "mount",
  },
  backend: {
    enabled: true,
    apiBaseUrl: "http://localhost:8200/api/catalog",
    healthEndpoint: "/health",
  },
  authorization: {
    requiredPermissions: ["catalog.view"],
    requiredFlags: ["catalog.enabled"],
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
  environment: "local",
  user: {
    id: "local-dev",
    displayName: "Local Developer",
    email: "dev@local",
  },
  permissions: ["orders.view", "catalog.view"],
  flags: {
    "orders.enabled": true,
    "catalog.enabled": true,
  },
  features: [ordersFeature, catalogFeature],
  metadata: {
    source: "bootstrap-service-registry",
    generatedBy: "shell-bootstrap-api",
    generatedAtUtc: "2026-05-04T00:00:00Z",
  },
};

describe("App", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    window.history.replaceState(null, "", "/");
    vi.mocked(loadRuntimeFeatures).mockResolvedValue(runtime);
  });

  it("loads runtime once and renders the default feature", async () => {
    render(<App />);

    await waitFor(() => {
      expect(loadRuntimeFeatures).toHaveBeenCalledTimes(1);
    });

    expect(await screen.findByTestId("feature-host")).toHaveTextContent(
      "FeatureHost: catalog / local",
    );
  });

  it("passes selected feature and existing runtime to FeatureHost when navigating", async () => {
    const user = userEvent.setup();

    render(<App />);

    expect(await screen.findByTestId("feature-host")).toHaveTextContent(
      "FeatureHost: catalog / local",
    );

    await user.click(screen.getByRole("button", { name: "Orders" }));

    expect(await screen.findByTestId("feature-host")).toHaveTextContent(
      "FeatureHost: orders / local",
    );

    expect(loadRuntimeFeatures).toHaveBeenCalledTimes(1);
  });

  it("uses current route when it matches an available feature", async () => {
    window.history.replaceState(null, "", "/orders");

    render(<App />);

    expect(await screen.findByTestId("feature-host")).toHaveTextContent(
      "FeatureHost: orders / local",
    );

    expect(loadRuntimeFeatures).toHaveBeenCalledTimes(1);
  });

  it("shows empty-state message when runtime has no features", async () => {
    vi.mocked(loadRuntimeFeatures).mockResolvedValueOnce({
      ...runtime,
      features: [],
      permissions: [],
      flags: {},
    });

    render(<App />);

    expect(
      await screen.findByText("No features are available for this user/environment."),
    ).toBeInTheDocument();
  });

  it("shows runtime load error", async () => {
    vi.mocked(loadRuntimeFeatures).mockRejectedValueOnce(new Error("Bootstrap failed"));

    render(<App />);

    expect(await screen.findByText("Runtime load failed")).toBeInTheDocument();
    expect(await screen.findByText("Bootstrap failed")).toBeInTheDocument();
  });
});