import type { ShellFeatureAuthContractV1 } from "../contracts/shellFeatureAuth";

export function injectFeatureShellAuth(
  auth: Omit<ShellFeatureAuthContractV1, "version">
): void {
  window.__FEATURE_SHELL_AUTH__ = {
    version: "v1",
    authMode: auth.authMode,
    isAuthenticated: auth.isAuthenticated,
    userId: auth.userId,
    userName: auth.userName,
    email: auth.email,
    roles: auth.roles ?? [],
    accessToken: auth.accessToken,
  };
}

export function clearFeatureShellAuth(): void {
  delete window.__FEATURE_SHELL_AUTH__;
}