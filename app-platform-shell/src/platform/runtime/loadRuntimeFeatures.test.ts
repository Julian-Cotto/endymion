import { beforeEach, describe, expect, it, vi } from "vitest";

import type { BootstrapResponse } from "../contracts/bootstrapResponse";
import type { RegistryRuntimeResponseV1 } from "../contracts/registryRuntimeResponse";
import { loadBootstrapResponse } from "../bootstrap/loadBootstrapResponse";
import { loadRegistryRuntimeResponse } from "./loadRegistryRuntimeResponse";
import { loadRuntimeFeatures } from "./loadRuntimeFeatures";

vi.mock("../bootstrap/loadBootstrapResponse", () => ({
  loadBootstrapResponse: vi.fn(),
}));

vi.mock("./loadRegistryRuntimeResponse", () => ({
  loadRegistryRuntimeResponse: vi.fn(),
}));

const bootstrapResponse: BootstrapResponse = {
  environment: "local",
  user: {
    id: "dev-user",
    displayName: "Dev User",
    email: "dev@example.local",
  },
  permissions: ["orders.view"],
  flags: {
    "orders.enabled": true,
  },
  features: [],
  metadata: {
    source: "bootstrap",
    generatedBy: "test",
    generatedAtUtc: "2026-04-29T00:00:00Z",
  },
};

const registryResponse: RegistryRuntimeResponseV1 = {
  environment: "local",
  features: [
    {
      manifestVersion: "1.0",
      featureKey: "orders",
      displayName: "Orders",
      version: "1.0.0",
      environment: "local",
      route: "/orders",

      frontend: {
        type: "module",
        entryUrl: "http://localhost:3200/src/bootstrap-entry.tsx",
        integrity: null,
        basePath: "/orders",
      },

      backend: {
        apiBaseUrl: "http://localhost:8100/api/orders",
      },

      nav: {
        label: "Orders",
        icon: "package",
        group: null,
        order: 10,
      },

      authorization: {
        requiredPermissions: ["orders.view"],
        requiredFlags: ["orders.enabled"],
      },

      compatibility: {
        shellContractMin: "v1",
        shellContractMax: "v1",
      },

      metadata: {
        ownerTeam: "platform",
        commitSha: null,
        buildId: null,
        releaseDate: null,
      },
    },
  ],
};

describe("loadRuntimeFeatures", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.unstubAllEnvs();
  });

  it("loads bootstrap response in bootstrap mode", async () => {
    vi.stubEnv("VITE_RUNTIME_SOURCE_MODE", "bootstrap");
    vi.stubEnv("VITE_BOOTSTRAP_URL", "http://localhost:8001/api/runtime/features");

    vi.mocked(loadBootstrapResponse).mockResolvedValue(bootstrapResponse);

    const result = await loadRuntimeFeatures();

    expect(loadBootstrapResponse).toHaveBeenCalledWith(
      "http://localhost:8001/api/runtime/features",
      { signal: undefined },
    );

    expect(result).toBe(bootstrapResponse);
  });

  it("loads registry response and normalizes it in registry mode", async () => {
    vi.stubEnv("VITE_RUNTIME_SOURCE_MODE", "registry");
    vi.stubEnv(
      "VITE_REGISTRY_RUNTIME_URL",
      "http://localhost:8010/api/runtime/features?environment=local",
    );

    vi.mocked(loadRegistryRuntimeResponse).mockResolvedValue(registryResponse);

    const result = await loadRuntimeFeatures();

    expect(loadRegistryRuntimeResponse).toHaveBeenCalledWith(
      "http://localhost:8010/api/runtime/features?environment=local",
      { signal: undefined },
    );

    expect(result.environment).toBe("local");
    expect(result.features).toHaveLength(1);
    expect(result.features[0].featureKey).toBe("orders");
    expect(result.features[0].frontend.entryUrl).toBe(
      "http://localhost:3200/src/bootstrap-entry.tsx",
    );
  });
});