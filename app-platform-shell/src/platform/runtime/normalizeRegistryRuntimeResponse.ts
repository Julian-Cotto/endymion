import type {
  BootstrapFeatureAuthMode,
  BootstrapResponse,
} from "../contracts/bootstrapResponse";
import type { RegistryRuntimeResponseV1 } from "../contracts/registryRuntimeResponse";

function optionalString(value: string | null | undefined): string | undefined {
  return value ?? undefined;
}

function normalizeAuthMode(value: string | undefined): BootstrapFeatureAuthMode | undefined {
  if (value === "entra" || value === "mock" || value === "none") {
    return value;
  }

  return undefined;
}

function normalizeAuthModes(values: string[] | undefined): BootstrapFeatureAuthMode[] | undefined {
  if (!values) {
    return undefined;
  }

  return values
    .map((value) => normalizeAuthMode(value))
    .filter((value): value is BootstrapFeatureAuthMode => value !== undefined);
}

export function normalizeRegistryRuntimeResponse(
  input: RegistryRuntimeResponseV1,
): BootstrapResponse {
  return {
    environment: input.environment,
    user: input.user ?? {
      id: "registry-user",
      displayName: "Registry User",
      email: "registry@example.local",
    },
    permissions: input.permissions ?? [],
    flags: input.flags ?? {},
    features: (input.features ?? []).map((feature) => ({
      featureKey: feature.featureKey,
      displayName: feature.displayName,
      route: feature.route,
      version: feature.version,
      nav: feature.nav,
      frontend: {
        enabled: feature.frontend?.enabled ?? true,
        entryUrl: feature.frontend.entryUrl,
        mountFunction: feature.frontend.mountFunction ?? "mount",
      },
      backend: {
        enabled: feature.backend?.enabled ?? true,
        apiBaseUrl: feature.backend.apiBaseUrl,
        healthEndpoint: optionalString(feature.backend.healthEndpoint),
      },
      authorization: {
        requiredPermissions: feature.authorization?.requiredPermissions ?? [],
        requiredFlags: feature.authorization?.requiredFlags ?? [],
      },
      auth: {
        required: feature.auth?.required,
        mode: normalizeAuthMode(feature.auth?.mode),
        shellAuthRequired: feature.auth?.shellAuthRequired,
        tokenForwarding: feature.auth?.tokenForwarding,
        tokenStrategy: feature.auth?.tokenStrategy ?? undefined,
        allowedDevModes: normalizeAuthModes(feature.auth?.allowedDevModes),
        roles: feature.auth?.roles,
      },
    })),
    metadata: {
      source: input.metadata?.source ?? "registry",
      generatedBy: input.metadata?.generatedBy,
      generatedAtUtc: input.metadata?.generatedAtUtc,
    },
  };
}