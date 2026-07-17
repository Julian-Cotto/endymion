import {
  getFeatureMountContext,
  getShellAuthContext,
} from "./shellContext";
import type { FeatureAuthContext } from "./authTypes";

function normalizeRoles(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return [...new Set(value.map((item) => String(item).trim()).filter(Boolean))];
}

export function resolveFeatureAuthContext(): FeatureAuthContext {
  const mountContext = getFeatureMountContext();
  const shellAuth = getShellAuthContext();

  const isAuthenticated = shellAuth?.isAuthenticated ?? false;

  if (!isAuthenticated) {
    throw new Error(
      "Shell authentication is required but no valid session was provided.",
    );
  }

  if (!shellAuth?.accessToken) {
    throw new Error("Access token is required but not provided by shell.");
  }

  return {
    isAuthenticated,
    authMode: "entra",
    accessToken: shellAuth.accessToken,
    userId: shellAuth.userId ?? mountContext?.session?.userId ?? null,
    userName: shellAuth.userName ?? mountContext?.session?.userName ?? null,
    email: shellAuth.email ?? mountContext?.session?.email ?? null,
    roles: normalizeRoles(
      shellAuth.roles ?? mountContext?.session?.roles ?? [],
    ),
  };
}