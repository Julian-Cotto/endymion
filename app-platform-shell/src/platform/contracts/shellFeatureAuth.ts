export interface ShellFeatureAuthContractV1 {
  version: "v1";
  isAuthenticated: boolean;
  authMode: "none" | "mock" | "entra";
  userId?: string;
  userName?: string;
  email?: string;
  roles?: string[];
  accessToken?: string;
}

export interface ShellFeatureBackendContractV1 {
  baseUrl?: string;
  healthEndpoint?: string;
  enabled?: boolean;
}

export interface ShellNavigateOptions {
  replace?: boolean;
}

export type ShellSubPathHandler = (subPath: string) => void;

export interface ShellFeatureRuntimeContractV1 {
  version: "v1";
  environment?: string;
  featureKey: string;
  route?: string;
  displayName?: string;
  backend?: ShellFeatureBackendContractV1;
  flags?: Record<string, boolean>;
  permissions?: string[];
  /** Path under the feature's basePath at mount time. Always starts with "/"
   *  (or is "" when at the feature's root). */
  subPath?: string;
  /** Push a new subPath into the browser URL. MFE calls this for in-app
   *  navigation. */
  navigate?: (subPath: string, options?: ShellNavigateOptions) => void;
  /** Subscribe to subPath changes driven by the shell (browser back/forward,
   *  external links). Returns an unsubscribe function. */
  onSubPathChange?: (handler: ShellSubPathHandler) => () => void;
}

declare global {
  interface Window {
    __FEATURE_SHELL_AUTH__?: ShellFeatureAuthContractV1;
    __FEATURE_SHELL_RUNTIME__?: ShellFeatureRuntimeContractV1;
  }
}