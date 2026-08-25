import { useEffect, useMemo, useRef, useState } from "react";

import { useShellSession } from "../hooks/useShellSession";
import { bootstrapFeature } from "../../platform/bootstrap/bootstrapFeature";
import type {
  BootstrapFeature,
  BootstrapResponse,
} from "../../platform/contracts/bootstrapResponse";
import type {
  FeatureManifest,
  FeatureManifestAuth,
} from "../../platform/contracts/featureManifest";
import type {
  ShellNavigateOptions,
  ShellSubPathHandler,
} from "../../platform/contracts/shellFeatureAuth";
import { setShellSessionSnapshot } from "../../platform/session/shellSessionStore";

interface FeatureHostProps {
  feature: BootstrapFeature;
  runtime: BootstrapResponse;
  subPath?: string;
  onNavigateSubPath?: (
    subPath: string,
    options?: ShellNavigateOptions,
  ) => void;
  onSubscribeSubPath?: (handler: ShellSubPathHandler) => () => void;
}

function normalizeManifestAuth(
  auth: BootstrapFeature["auth"] | undefined,
): FeatureManifestAuth {
  return {
    required: auth?.required ?? false,
    mode: auth?.mode ?? "none",
    shellAuthRequired: auth?.shellAuthRequired ?? false,
    tokenForwarding: auth?.tokenForwarding ?? false,
    tokenStrategy: auth?.tokenStrategy ?? "none",
    allowedDevModes: auth?.allowedDevModes ?? ["none", "mock"],
    roles: auth?.roles ?? [],
  };
}

function asCleanup(value: unknown): (() => void) | undefined {
  return typeof value === "function" ? (value as () => void) : undefined;
}

function runCleanup(cleanup: (() => void) | undefined): void {
  if (!cleanup) return;

  try {
    cleanup();
  } catch (error) {
    console.warn("Feature cleanup failed", error);
  }
}

export default function FeatureHost({
  feature,
  runtime,
  subPath,
  onNavigateSubPath,
  onSubscribeSubPath,
}: FeatureHostProps) {
  const [container, setContainer] = useState<HTMLDivElement | null>(null);
  const activeCleanupRef = useRef<(() => void) | undefined>(undefined);
  const loadIdRef = useRef(0);

  // Stable refs so changing the subPath after mount does not re-bootstrap the
  // feature. The feature reads the current subPath via its registered
  // onSubPathChange handler.
  const subPathRef = useRef<string>(subPath ?? "");
  const navigateRef = useRef<FeatureHostProps["onNavigateSubPath"]>(
    onNavigateSubPath,
  );
  const subscribeRef = useRef<FeatureHostProps["onSubscribeSubPath"]>(
    onSubscribeSubPath,
  );

  useEffect(() => {
    subPathRef.current = subPath ?? "";
  }, [subPath]);

  useEffect(() => {
    navigateRef.current = onNavigateSubPath;
  }, [onNavigateSubPath]);

  useEffect(() => {
    subscribeRef.current = onSubscribeSubPath;
  }, [onSubscribeSubPath]);

  const session = useShellSession();
  const [error, setError] = useState<string | null>(null);

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

  const runtimeKey = useMemo(
    () =>
      JSON.stringify({
        environment: runtime.environment,
        permissions: runtime.permissions,
        flags: runtime.flags,
      }),
    [runtime.environment, runtime.permissions, runtime.flags],
  );

  useEffect(() => {
    setShellSessionSnapshot(session);
    return () => setShellSessionSnapshot(null);
  }, [sessionKey, session]);

  useEffect(() => {
    if (container === null) {
      return;
    }

    const mountContainer: HTMLDivElement = container;

    let cancelled = false;
    const loadId = loadIdRef.current + 1;
    loadIdRef.current = loadId;

    async function load(): Promise<void> {
      try {
        setError(null);

        runCleanup(activeCleanupRef.current);
        activeCleanupRef.current = undefined;
        mountContainer.replaceChildren();

        setShellSessionSnapshot(session);

        const manifest: FeatureManifest = {
          featureKey: feature.featureKey,
          displayName: feature.displayName,
          basePath: feature.route,
          version: feature.version,
          environment: runtime.environment,
          frontend: {
            enabled: feature.frontend.enabled ?? true,
            entryUrl: feature.frontend.entryUrl,
            mountFunction: feature.frontend.mountFunction || "mount",
          },
          backend: {
            enabled: feature.backend.enabled ?? true,
            baseUrl: feature.backend.apiBaseUrl,
            healthEndpoint: feature.backend.healthEndpoint,
          },
          auth: normalizeManifestAuth(feature.auth),
        };

        const cleanup = await bootstrapFeature({
          manifest,
          container: mountContainer,
          session,
          runtime: {
            version: "v1",
            environment: runtime.environment,
            featureKey: feature.featureKey,
            route: feature.route,
            displayName: feature.displayName,
            backend: {
              baseUrl: feature.backend.apiBaseUrl,
              enabled: feature.backend.enabled ?? true,
              healthEndpoint: feature.backend.healthEndpoint,
            },
            flags: runtime.flags,
            permissions: runtime.permissions,
            subPath: subPathRef.current,
            navigate: navigateRef.current
              ? (next, options) => navigateRef.current?.(next, options)
              : undefined,
            onSubPathChange: subscribeRef.current
              ? (handler) =>
                  subscribeRef.current?.(handler) ?? (() => undefined)
              : undefined,
          },
        });

        const cleanupFn = asCleanup(cleanup);

        if (cancelled || loadId !== loadIdRef.current) {
          runCleanup(cleanupFn);
          mountContainer.replaceChildren();
          return;
        }

        activeCleanupRef.current = cleanupFn;
      } catch (err) {
        if (!cancelled && loadId === loadIdRef.current) {
          const message =
            err instanceof Error ? err.message : "Failed to load feature.";
          setError(message);
          console.error("Failed to bootstrap feature", err);
        }
      }
    }

    void load();

    return () => {
      cancelled = true;
      runCleanup(activeCleanupRef.current);
      activeCleanupRef.current = undefined;
      mountContainer.replaceChildren();
    };
  }, [container, feature, runtime.environment, runtimeKey, sessionKey, session]);

  return (
    <>
      {error ? (
        <div>
          <h2>Feature load failed</h2>
          <p>{error}</p>
        </div>
      ) : null}

      <div ref={setContainer} style={{ display: error ? "none" : undefined }} />
    </>
  );
}