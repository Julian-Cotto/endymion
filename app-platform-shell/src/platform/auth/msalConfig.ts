import {
    BrowserCacheLocation,
    LogLevel,
    PublicClientApplication,
    type Configuration,
    type RedirectRequest,
    type SilentRequest,
  } from "@azure/msal-browser";
  
  function readEnv(name: string): string | undefined {
    const value = import.meta.env[name];
  
    if (typeof value !== "string") {
      return undefined;
    }
  
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : undefined;
  }
  
  function readApiScopes(): string[] {
    const raw = readEnv("VITE_ENTRA_SCOPES") ?? readEnv("VITE_ENTRA_SCOPE") ?? "";
  
    return raw
      .split(/[,\s]+/)
      .map((item) => item.trim())
      .filter((item) => item.length > 0);
  }
  
  export function getShellAuthMode(): "mock" | "entra" {
    const mode = (readEnv("VITE_AUTH_MODE") ?? "mock").toLowerCase();
    return mode === "entra" ? "entra" : "mock";
  }
  
  export const entraApiScopes = readApiScopes();
  
  export const msalConfig: Configuration = {
    auth: {
      clientId: readEnv("VITE_ENTRA_CLIENT_ID") ?? "",
      authority:
        readEnv("VITE_ENTRA_AUTHORITY") ??
        `https://login.microsoftonline.com/${readEnv("VITE_ENTRA_TENANT_ID") ?? "common"}`,
      redirectUri: readEnv("VITE_ENTRA_REDIRECT_URI") ?? window.location.origin,
      postLogoutRedirectUri:
        readEnv("VITE_ENTRA_POST_LOGOUT_REDIRECT_URI") ?? window.location.origin,
  
      // Important: keep MSAL on the redirect URI after login.
      // This avoids extra navigation while we are still processing redirect state.
      navigateToLoginRequestUrl: false,
    },
    cache: {
      cacheLocation: BrowserCacheLocation.LocalStorage,
      storeAuthStateInCookie: false,
    },
    system: {
      loggerOptions: {
        logLevel: LogLevel.Warning,
        piiLoggingEnabled: false,
      },
    },
  };
  
  export const msalInstance = new PublicClientApplication(msalConfig);
  
  // Login should request only identity scopes.
  // API scopes are requested separately when acquiring the API token.
  export const loginRequest: RedirectRequest = {
    scopes: ["openid", "profile", "email"],
  };
  
  export function buildSilentTokenRequest(account: SilentRequest["account"]): SilentRequest {
    return {
      scopes: entraApiScopes,
      account,
    };
  }