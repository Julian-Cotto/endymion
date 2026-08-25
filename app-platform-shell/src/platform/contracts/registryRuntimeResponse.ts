export interface RegistryRuntimeUser {
  id: string;
  displayName: string;
  email: string;
}

export interface RegistryRuntimeMetadata {
  source?: string;
  generatedBy?: string;
  generatedAtUtc?: string;
}

export interface RegistryRuntimeFeatureFrontend {
  enabled?: boolean;
  type?: string;
  entryUrl: string;
  mountFunction?: string;
  integrity?: string | null;
  basePath?: string;
}

export interface RegistryRuntimeFeatureBackend {
  enabled?: boolean;
  apiBaseUrl: string;
  healthEndpoint?: string | null;
}

export interface RegistryRuntimeFeatureNav {
  label: string;
  icon: string;
  group?: string | null;
  order?: number | null;
}

export interface RegistryRuntimeFeatureAuthorization {
  requiredPermissions: string[];
  requiredFlags: string[];
}

export interface RegistryRuntimeFeatureAuth {
  required?: boolean;
  mode?: "entra" | "mock" | "none";
  shellAuthRequired?: boolean;
  tokenForwarding?: boolean;
  tokenStrategy?: "forwarded-bearer" | "shell-session" | "none" | string | null;
  allowedDevModes?: string[];
  roles?: string[];
}

export interface RegistryRuntimeFeatureCompatibility {
  shellContractMin: string;
  shellContractMax: string;
}

export interface RegistryRuntimeFeatureMetadata {
  ownerTeam: string;
  commitSha?: string | null;
  buildId?: string | null;
  releaseDate?: string | null;
}

export interface RegistryRuntimeFeature {
  manifestVersion?: string;
  featureKey: string;
  displayName: string;
  version: string;
  environment: string;
  route: string;
  frontend: RegistryRuntimeFeatureFrontend;
  backend: RegistryRuntimeFeatureBackend;
  nav: RegistryRuntimeFeatureNav;
  authorization: RegistryRuntimeFeatureAuthorization;
  auth?: RegistryRuntimeFeatureAuth;
  compatibility?: RegistryRuntimeFeatureCompatibility;
  metadata?: RegistryRuntimeFeatureMetadata;
}

export interface RegistryRuntimeResponseV1 {
  environment: string;
  user?: RegistryRuntimeUser;
  permissions?: string[];
  flags?: Record<string, boolean>;
  features: RegistryRuntimeFeature[];
  metadata?: RegistryRuntimeMetadata;
}