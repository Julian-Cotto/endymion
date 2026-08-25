import type { RegistryRuntimeResponseV1 } from "../contracts/registryRuntimeResponse";
import { buildRuntimeRequestHeaders } from "./runtimeRequestAuth";

export interface LoadRegistryRuntimeResponseOptions {
  signal?: AbortSignal;
}

export async function loadRegistryRuntimeResponse(
  runtimeUrl: string,
  options: LoadRegistryRuntimeResponseOptions = {},
): Promise<RegistryRuntimeResponseV1> {
  const response = await fetch(runtimeUrl, {
    method: "GET",
    headers: buildRuntimeRequestHeaders(),
    signal: options.signal,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(
      `Registry runtime request failed: ${response.status} ${response.statusText}${text ? ` - ${text}` : ""}`,
    );
  }

  return (await response.json()) as RegistryRuntimeResponseV1;
}