import { useEffect, useMemo, useRef, useState } from "react";
import {
  InteractionRequiredAuthError,
  InteractionStatus,
  type AccountInfo,
} from "@azure/msal-browser";
import { useMsal } from "@azure/msal-react";

import { AppShell } from "./layouts/AppShell";
import FeatureHost from "./pages/FeatureHost";
import { HomePage } from "./pages/HomePage";
import { ShellAuthProvider } from "./providers/ShellAuthProvider";
import { ThemeProvider } from "./providers/ThemeProvider";
import type { ShellUserSession } from "../platform/auth/sessionTypes";
import {
  buildSilentTokenRequest,
  entraApiScopes,
  getShellAuthMode,
  loginRequest,
} from "../platform/auth/msalConfig";
import type {
  BootstrapFeature,
  BootstrapResponse,
} from "../platform/contracts/bootstrapResponse";
import { loadRuntimeFeatures } from "../platform/runtime/loadRuntimeFeatures";
import { getBootstrapUrl } from "../platform/runtime/runtimeClientConfig";
import { setShellSessionSnapshot } from "../platform/session/shellSessionStore";
import type {
  ShellNavigateOptions,
  ShellSubPathHandler,
} from "../platform/contracts/shellFeatureAuth";

const LAST_FEATURE_ROUTE_KEY = "app-platform-shell:last-feature-route";

function stripTrailingSlash(path: string): string {
  return path.length > 1 && path.endsWith("/") ? path.slice(0, -1) : path;
}

function normalizeSubPath(subPath: string): string {
  if (!subPath || subPath === "/") return "";
  return subPath.startsWith("/") ? subPath : "/" + subPath;
}

interface FeatureRouteMatch {
  feature: BootstrapFeature;
  subPath: string;
}

function matchFeatureByPath(
  features: BootstrapFeature[],
  pathname: string,
): FeatureRouteMatch | null {
  const path = stripTrailingSlash(pathname) || "/";

  let best: BootstrapFeature | null = null;

  for (const feature of features) {
    const route = stripTrailingSlash(feature.route);
    if (path === route || path.startsWith(route + "/")) {
      if (
        !best ||
        stripTrailingSlash(best.route).length < route.length
      ) {
        best = feature;
      }
    }
  }

  if (!best) {
    return null;
  }

  const route = stripTrailingSlash(best.route);
  const subPath = path === route ? "" : path.slice(route.length);

  return { feature: best, subPath };
}

function rememberRoute(route: string): void {
  localStorage.setItem(LAST_FEATURE_ROUTE_KEY, route);
}

function parseRoles(raw: string | undefined): string[] {
  return (raw ?? "")
    .split(",")
    .map((role) => role.trim())
    .filter(Boolean);
}

function sortFeatures(features: BootstrapFeature[]): BootstrapFeature[] {
  return [...features].sort((left, right) => {
    const leftOrder = left.nav.order ?? 9999;
    const rightOrder = right.nav.order ?? 9999;

    if (leftOrder !== rightOrder) {
      return leftOrder - rightOrder;
    }

    return left.nav.label.localeCompare(right.nav.label);
  });
}

function getDefaultFeature(runtime: BootstrapResponse | null): BootstrapFeature | null {
  if (!runtime || runtime.features.length === 0) {
    return null;
  }

  return sortFeatures(runtime.features)[0];
}

function buildMockSession(): ShellUserSession {
  return {
    isAuthenticated: true,
    userId: import.meta.env.VITE_MOCK_USER_ID ?? "dev-user-1",
    userName: import.meta.env.VITE_MOCK_USER_NAME ?? "Local Developer",
    email: import.meta.env.VITE_MOCK_EMAIL ?? "dev@local",
    roles: parseRoles(import.meta.env.VITE_MOCK_ROLES),
    accessToken: import.meta.env.VITE_MOCK_ACCESS_TOKEN ?? "dev-token",
  };
}

function buildSessionFromAccount(account: AccountInfo, accessToken: string): ShellUserSession {
  return {
    isAuthenticated: true,
    userId: account.localAccountId || account.homeAccountId,
    userName: account.name ?? account.username,
    email: account.username,
    roles: [],
    accessToken,
  };
}

function ShellFrame({
  session,
  onLogout,
}: {
  session: ShellUserSession;
  onLogout?: () => void;
  tokenStatus?: string;
}) {
  const bootstrapUrl = getBootstrapUrl();

  const [runtime, setRuntime] = useState<BootstrapResponse | null>(null);
  const [runtimeError, setRuntimeError] = useState<string | null>(null);
  const [selectedFeatureKey, setSelectedFeatureKey] = useState<string | null>(
    null,
  );
  const [currentSubPath, setCurrentSubPath] = useState<string>("");

  const subscribersRef = useRef<Map<string, Set<ShellSubPathHandler>>>(
    new Map(),
  );
  const runtimeRef = useRef<BootstrapResponse | null>(null);

  useEffect(() => {
    runtimeRef.current = runtime;
  }, [runtime]);

  const sessionKey = useMemo(
    () =>
      [
        session.isAuthenticated ? "authenticated" : "anonymous",
        session.userId ?? "",
        session.email ?? "",
        session.accessToken ?? "",
      ].join("|"),
    [session.isAuthenticated, session.userId, session.email, session.accessToken],
  );

  function notifySubPathSubscribers(featureKey: string, subPath: string): void {
    const set = subscribersRef.current.get(featureKey);
    if (!set) return;
    for (const handler of set) {
      try {
        handler(subPath);
      } catch (error) {
        console.warn("Sub-path handler failed", error);
      }
    }
  }

  useEffect(() => {
    function handlePopState(): void {
      const features = runtimeRef.current?.features ?? [];
      const match = matchFeatureByPath(features, window.location.pathname);

      if (match) {
        setSelectedFeatureKey(match.feature.featureKey);
        setCurrentSubPath(match.subPath);
        rememberRoute(match.feature.route);
        notifySubPathSubscribers(match.feature.featureKey, match.subPath);
        return;
      }

      setSelectedFeatureKey(null);
      setCurrentSubPath("");
    }

    window.addEventListener("popstate", handlePopState);

    return () => {
      window.removeEventListener("popstate", handlePopState);
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    const abortController = new AbortController();

    async function loadRuntime(): Promise<void> {
      try {
        setRuntimeError(null);
        setShellSessionSnapshot(session);

        const response = await loadRuntimeFeatures({
          bootstrapUrl,
          signal: abortController.signal,
        });

        if (cancelled) {
          return;
        }

        setRuntime(response);

        const match = matchFeatureByPath(
          response.features,
          window.location.pathname,
        );

        if (match) {
          setSelectedFeatureKey(match.feature.featureKey);
          setCurrentSubPath(match.subPath);
          rememberRoute(match.feature.route);
          return;
        }

        const rememberedRoute = localStorage.getItem(LAST_FEATURE_ROUTE_KEY);
        const rememberedFeature =
          rememberedRoute &&
          response.features.find((feature) => feature.route === rememberedRoute);

        const defaultFeature = rememberedFeature || getDefaultFeature(response);

        if (defaultFeature) {
          setSelectedFeatureKey(defaultFeature.featureKey);
          setCurrentSubPath("");
          rememberRoute(defaultFeature.route);
          window.history.replaceState(null, "", defaultFeature.route);
          return;
        }

        setSelectedFeatureKey(null);
        setCurrentSubPath("");
      } catch (error) {
        if (cancelled || (error instanceof DOMException && error.name === "AbortError")) {
          return;
        }

        setRuntimeError(error instanceof Error ? error.message : "Failed to load runtime.");
      }
    }

    void loadRuntime();

    return () => {
      cancelled = true;
      abortController.abort();
      setShellSessionSnapshot(null);
    };
  }, [bootstrapUrl, sessionKey]);

  const sortedFeatures = runtime ? sortFeatures(runtime.features) : [];
  const selectedFeature =
    selectedFeatureKey && runtime
      ? runtime.features.find((feature) => feature.featureKey === selectedFeatureKey)
      : null;

  function navigateToFeature(feature: BootstrapFeature): void {
    rememberRoute(feature.route);
    window.history.pushState(null, "", feature.route);
    setSelectedFeatureKey(feature.featureKey);
    setCurrentSubPath("");
  }

  function goHome(): void {
    setSelectedFeatureKey(null);
    setCurrentSubPath("");
    window.history.pushState(null, "", "/");
    localStorage.removeItem(LAST_FEATURE_ROUTE_KEY);
  }

  function navigateSubPathForFeature(
    feature: BootstrapFeature,
    subPath: string,
    options?: ShellNavigateOptions,
  ): void {
    const normalized = normalizeSubPath(subPath);
    const route = stripTrailingSlash(feature.route);
    const fullPath = (route + normalized) || "/";

    if (options?.replace) {
      window.history.replaceState(null, "", fullPath);
    } else {
      window.history.pushState(null, "", fullPath);
    }

    if (feature.featureKey === selectedFeatureKey) {
      setCurrentSubPath(normalized);
    }
  }

  function subscribeSubPath(
    featureKey: string,
    handler: ShellSubPathHandler,
  ): () => void {
    let set = subscribersRef.current.get(featureKey);
    if (!set) {
      set = new Set();
      subscribersRef.current.set(featureKey, set);
    }
    set.add(handler);

    return () => {
      const current = subscribersRef.current.get(featureKey);
      current?.delete(handler);
    };
  }

  return (
    <ShellAuthProvider session={session}>
      <AppShell
        session={session}
        features={sortedFeatures}
        selectedFeature={selectedFeature ?? null}
        selectedFeatureKey={selectedFeatureKey}
        onSelectFeature={navigateToFeature}
        onGoHome={goHome}
        onLogout={onLogout}
      >
        {runtimeError ? (
          <div className="alert alert-error mb-6">
            <strong>Runtime load failed</strong>
            <pre className="text-mono whitespace-pre-wrap mt-1">{runtimeError}</pre>
          </div>
        ) : null}

        {!runtime && !runtimeError ? (
          <p className="text-muted">Loading runtime features...</p>
        ) : null}

        {runtime && !selectedFeature ? (
          <HomePage
            runtime={runtime}
            session={session}
            onLaunchFeature={navigateToFeature}
          />
        ) : null}

        {selectedFeature && runtime ? (
          <FeatureHost
            feature={selectedFeature}
            runtime={runtime}
            subPath={currentSubPath}
            onNavigateSubPath={(subPath, options) =>
              navigateSubPathForFeature(selectedFeature, subPath, options)
            }
            onSubscribeSubPath={(handler) =>
              subscribeSubPath(selectedFeature.featureKey, handler)
            }
          />
        ) : null}
      </AppShell>
    </ShellAuthProvider>
  );
}

function MockShellApp() {
  const session = useMemo(() => buildMockSession(), []);

  return <ShellFrame session={session} tokenStatus="Mock token active" />;
}

function EntraShellApp() {
  const { instance, accounts, inProgress } = useMsal();
  const [session, setSession] = useState<ShellUserSession | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tokenAcquiredAt, setTokenAcquiredAt] = useState<Date | null>(null);

  const activeAccount = instance.getActiveAccount();
  const account = activeAccount ?? accounts[0] ?? null;
  const accountKey = account?.homeAccountId ?? account?.localAccountId ?? null;

  useEffect(() => {
    if (inProgress !== InteractionStatus.None) {
      return;
    }

    if (!account) {
      void instance.loginRedirect(loginRequest);
    }
  }, [accountKey, account, inProgress, instance]);

  useEffect(() => {
    if (inProgress !== InteractionStatus.None || !account) {
      return;
    }

    instance.setActiveAccount(account);

    let cancelled = false;

    async function acquireToken(): Promise<void> {
      try {
        if (entraApiScopes.length === 0) {
          throw new Error("VITE_ENTRA_SCOPES is empty.");
        }

        const result = await instance.acquireTokenSilent(buildSilentTokenRequest(account));

        if (!cancelled) {
          setSession(buildSessionFromAccount(account, result.accessToken));
          setTokenAcquiredAt(new Date());
          setError(null);
        }
      } catch (err) {
        if (err instanceof InteractionRequiredAuthError) {
          await instance.acquireTokenRedirect(buildSilentTokenRequest(account));
          return;
        }

        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Token error");
        }
      }
    }

    void acquireToken();

    return () => {
      cancelled = true;
    };
  }, [accountKey, inProgress, instance]);

  function logout(): void {
    const confirmed = window.confirm("Sign out of the App Platform Shell?");
    if (!confirmed) {
      return;
    }

    localStorage.removeItem(LAST_FEATURE_ROUTE_KEY);
    void instance.logoutRedirect();
  }

  if (error) {
    return (
      <div style={{ padding: 16 }}>
        <h1>App Platform Shell</h1>
        <h2>Authentication failed</h2>
        <pre>{error}</pre>
      </div>
    );
  }

  if (!session) {
    return (
      <div style={{ padding: 16 }}>
        <h1>App Platform Shell</h1>
        <p>Signing in...</p>
      </div>
    );
  }

  const tokenStatus = tokenAcquiredAt
    ? `Token refreshed at ${tokenAcquiredAt.toLocaleTimeString()}`
    : "Token pending";

  return <ShellFrame session={session} onLogout={logout} tokenStatus={tokenStatus} />;
}

export default function App() {
  return (
    <ThemeProvider>
      {getShellAuthMode() === "entra" ? <EntraShellApp /> : <MockShellApp />}
    </ThemeProvider>
  );
}