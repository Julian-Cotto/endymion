/// <reference types="vite/client" />

declare global {
  interface Window {
    __FEATURE_SHELL_AUTH__?: {
      isAuthenticated: boolean;
      authMode: "none" | "mock" | "entra";
      accessToken?: string;
      userId?: string;
      userName?: string;
      email?: string;
      roles?: string[];
    };

    __FEATURE_SHELL_RUNTIME__?: {
      version: "v1";
      environment: string;
      featureKey: string;
      route: string;
      displayName: string;
      backend?: {
        baseUrl?: string;
        enabled?: boolean;
        healthEndpoint?: string;
      };
      flags: Record<string, boolean>;
      permissions: string[];
    };
  }

  // Used in tests to mock dynamic import
  // eslint-disable-next-line no-var
  var __dynamicImportForTest__:
    | ((url: string) => Promise<Record<string, unknown>>)
    | undefined;
}

export {};