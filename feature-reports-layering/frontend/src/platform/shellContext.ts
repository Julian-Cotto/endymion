import type { ShellFeatureAuthContract } from "./authTypes";

export interface ShellFeatureRuntimeBackendContractV1 {
  baseUrl?: string;
  enabled?: boolean;
  healthEndpoint?: string;
}

export interface ShellFeatureRuntimeContractV1 {
  version: "v1";
  environment?: string;
  featureKey: string;
  route?: string;
  displayName?: string;
  backend?: ShellFeatureRuntimeBackendContractV1;
  flags?: Record<string, boolean>;
  permissions?: string[];
}

export interface ShellFeatureManifestContract {
  featureKey?: string;
  displayName?: string;
  basePath?: string;
  version?: string;
  environment?: string;
  frontend?: {
    enabled?: boolean;
    entryUrl?: string;
    mountFunction?: string;
  };
  backend?: {
    enabled?: boolean;
    baseUrl?: string;
    healthEndpoint?: string;
  };
  auth?: {
    required?: boolean;
    mode?: string;
    shellAuthRequired?: boolean;
    tokenForwarding?: boolean;
    tokenStrategy?: string;
    allowedDevModes?: string[];
    roles?: string[];
  };
}

export interface ShellUserSessionContract {
  isAuthenticated?: boolean;
  userId?: string;
  userName?: string;
  email?: string;
  roles?: string[];
  accessToken?: string;
}

export interface ShellMountContext {
  manifest?: ShellFeatureManifestContract;
  session?: ShellUserSessionContract;
  runtime?: ShellFeatureRuntimeContractV1;
}

declare global {
  interface Window {
    __FEATURE_SHELL_AUTH__?: ShellFeatureAuthContract;
    __FEATURE_SHELL_RUNTIME__?: ShellFeatureRuntimeContractV1;
    __FEATURE_MOUNT_CONTEXT__?: ShellMountContext;
  }
}

export function getShellAuthContext(): ShellFeatureAuthContract | undefined {
  if (typeof window === "undefined") {
    return undefined;
  }

  return window.__FEATURE_SHELL_AUTH__;
}

export function getShellRuntimeContext():
  | ShellFeatureRuntimeContractV1
  | undefined {
  if (typeof window === "undefined") {
    return undefined;
  }

  return window.__FEATURE_SHELL_RUNTIME__;
}

export function setShellRuntimeContext(
  runtime?: ShellFeatureRuntimeContractV1,
): void {
  if (typeof window === "undefined") {
    return;
  }

  if (runtime) {
    window.__FEATURE_SHELL_RUNTIME__ = runtime;
    return;
  }

  delete window.__FEATURE_SHELL_RUNTIME__;
}

export function getFeatureMountContext(): ShellMountContext | undefined {
  if (typeof window === "undefined") {
    return undefined;
  }

  return window.__FEATURE_MOUNT_CONTEXT__;
}

export function setFeatureMountContext(
  context?: ShellMountContext,
): void {
  if (typeof window === "undefined") {
    return;
  }

  if (context) {
    window.__FEATURE_MOUNT_CONTEXT__ = context;
    return;
  }

  delete window.__FEATURE_MOUNT_CONTEXT__;
}