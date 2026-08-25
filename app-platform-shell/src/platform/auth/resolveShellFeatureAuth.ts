import type { FeatureManifest } from "../contracts/featureManifest";
import type { ShellFeatureAuthContractV1 } from "../contracts/shellFeatureAuth";
import type { ShellUserSession } from "./sessionTypes";

export function resolveShellFeatureAuth(
  manifest: FeatureManifest,
  session: ShellUserSession,
): ShellFeatureAuthContractV1 | undefined {
  const auth = manifest.auth;

  if (!auth || !auth.shellAuthRequired) {
    return undefined;
  }

  if (auth.mode === "none") {
    return {
      version: "v1",
      authMode: "none",
      isAuthenticated: true,
      userId: "anonymous",
      userName: "anonymous",
      roles: [],
    };
  }

  if (auth.mode === "mock") {
    return {
      version: "v1",
      authMode: "mock",
      isAuthenticated: true,
      userId: session.userId ?? "dev-user",
      userName: session.userName ?? "Local Dev User",
      email: session.email ?? "dev@example.local",
      roles: session.roles ?? ["developer"],
      accessToken: session.accessToken,
    };
  }

  if (auth.mode === "entra") {
    if (!session.isAuthenticated) {
      return {
        version: "v1",
        authMode: "entra",
        isAuthenticated: false,
        roles: [],
      };
    }

    if (auth.tokenForwarding && !session.accessToken) {
      return {
        version: "v1",
        authMode: "entra",
        isAuthenticated: false,
        userId: session.userId,
        userName: session.userName,
        email: session.email,
        roles: session.roles ?? [],
      };
    }

    return {
      version: "v1",
      authMode: "entra",
      isAuthenticated: true,
      userId: session.userId,
      userName: session.userName,
      email: session.email,
      roles: session.roles ?? [],
      accessToken: auth.tokenForwarding ? session.accessToken : undefined,
    };
  }

  return undefined;
}