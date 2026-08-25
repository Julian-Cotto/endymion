import type { BootstrapResponse } from "../contracts/bootstrapResponse";
import { loadBootstrapResponse } from "../bootstrap/loadBootstrapResponse";
import { normalizeRegistryRuntimeResponse } from "./normalizeRegistryRuntimeResponse";
import { loadRegistryRuntimeResponse } from "./loadRegistryRuntimeResponse";
import {
  getBootstrapUrl,
  getRegistryRuntimeUrl,
  getRuntimeSourceMode,
} from "./runtimeClientConfig";

export interface LoadRuntimeFeaturesOptions {
  bootstrapUrl?: string;
  registryRuntimeUrl?: string;
  signal?: AbortSignal;
}

export async function loadRuntimeFeatures(
  options: LoadRuntimeFeaturesOptions = {},
): Promise<BootstrapResponse> {
  const mode = getRuntimeSourceMode();

  if (mode === "registry") {
    const runtimeResponse = await loadRegistryRuntimeResponse(
      options.registryRuntimeUrl ?? getRegistryRuntimeUrl(),
      { signal: options.signal },
    );

    return normalizeRegistryRuntimeResponse(runtimeResponse);
  }

  return loadBootstrapResponse(options.bootstrapUrl ?? getBootstrapUrl(), {
    signal: options.signal,
  });
}