import { loadFeatureManifest } from "../registry/loadFeatureManifest";
import {
  clearFeatureShellAuth,
  injectFeatureShellAuth,
} from "../auth/injectFeatureShellAuth";
import {
  clearFeatureShellRuntime,
  injectFeatureShellRuntime,
} from "../auth/injectFeatureShellRuntime";
import { resolveShellFeatureAuth } from "../auth/resolveShellFeatureAuth";
import type { ShellUserSession } from "../auth/sessionTypes";
import type { FeatureManifest } from "../contracts/featureManifest";
import type { ShellFeatureRuntimeContractV1 } from "../contracts/shellFeatureAuth";

export interface BootstrapFeatureParams {
  manifest?: FeatureManifest;
  manifestUrl?: string;
  container: HTMLElement;
  session: ShellUserSession;
  runtime?: ShellFeatureRuntimeContractV1;
}

export type FeatureModule = Record<string, unknown>;

type RemoteModule = FeatureModule;

async function loadRemoteModule(entryUrl: string): Promise<RemoteModule> {
  if (globalThis.__dynamicImportForTest__) {
    return globalThis.__dynamicImportForTest__(entryUrl);
  }

  return import(/* @vite-ignore */ entryUrl);
}

function buildFallbackRuntime(
  resolvedManifest: FeatureManifest,
): ShellFeatureRuntimeContractV1 {
  return {
    version: "v1",
    environment: resolvedManifest.environment,
    featureKey: resolvedManifest.featureKey,
    route: resolvedManifest.basePath,
    displayName: resolvedManifest.displayName,
    backend: {
      baseUrl: resolvedManifest.backend?.baseUrl,
      enabled: resolvedManifest.backend?.enabled,
      healthEndpoint: resolvedManifest.backend?.healthEndpoint,
    },
    flags: {},
    permissions: [],
  };
}

export async function bootstrapFeature({
  manifest,
  manifestUrl,
  container,
  session,
  runtime,
}: BootstrapFeatureParams): Promise<unknown> {
  const resolvedManifest =
    manifest ??
    (manifestUrl ? await loadFeatureManifest(manifestUrl) : undefined);

  if (!resolvedManifest) {
    throw new Error("bootstrapFeature requires either manifest or manifestUrl.");
  }

  const shellAuth = resolveShellFeatureAuth(resolvedManifest, session);

  clearFeatureShellAuth();

  if (shellAuth) {
    const { version: _version, ...authForWindow } = shellAuth;
    injectFeatureShellAuth(authForWindow);
  }

  const resolvedRuntime = runtime ?? buildFallbackRuntime(resolvedManifest);

  clearFeatureShellRuntime();
  injectFeatureShellRuntime(resolvedRuntime);

  const entryUrl = resolvedManifest.frontend?.entryUrl;

  if (!entryUrl) {
    throw new Error(
      `Feature '${resolvedManifest.featureKey}' is missing frontend.entryUrl.`,
    );
  }

  const mountFunctionName = resolvedManifest.frontend?.mountFunction || "mount";

  const mod = await loadRemoteModule(entryUrl);
  const mountFn = mod[mountFunctionName];

  if (typeof mountFn !== "function") {
    throw new Error(
      `Remote module for feature '${resolvedManifest.featureKey}' does not export mount function '${mountFunctionName}'.`,
    );
  }

  return (mountFn as (container: HTMLElement, context?: unknown) => unknown)(
    container,
    {
      manifest: resolvedManifest,
      session,
      runtime: resolvedRuntime,
    },
  );
}