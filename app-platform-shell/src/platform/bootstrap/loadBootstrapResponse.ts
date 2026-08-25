import type { BootstrapResponse } from "../contracts/bootstrapResponse";
import { assertBootstrapResponse } from "../contracts/assertBootstrapResponse";
import { buildRuntimeRequestHeaders } from "../runtime/runtimeRequestAuth";

export interface LoadBootstrapResponseOptions {
  signal?: AbortSignal;
}

export async function loadBootstrapResponse(
  bootstrapUrl: string,
  options: LoadBootstrapResponseOptions = {},
): Promise<BootstrapResponse> {
  const response = await fetch(bootstrapUrl, {
    method: "GET",
    headers: buildRuntimeRequestHeaders(),
    signal: options.signal,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(
      `Bootstrap request failed: ${response.status} ${response.statusText}${text ? ` - ${text}` : ""}`,
    );
  }

  const payload: unknown = await response.json();
  assertBootstrapResponse(payload);

  return payload;
}