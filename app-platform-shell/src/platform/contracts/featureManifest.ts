export type FeatureAuthMode = "none" | "mock" | "entra";

export interface FeatureManifestAuth {
  required: boolean;
  mode: FeatureAuthMode;
  shellAuthRequired: boolean;
  tokenForwarding: boolean;
  tokenStrategy: string;
  allowedDevModes: FeatureAuthMode[];
  roles: string[];
}

export interface FeatureManifestFrontend {
  enabled?: boolean;
  entryStrategy?: string;
  entryUrl?: string;
  mountFunction?: string;
}

export interface FeatureManifestBackend {
  enabled?: boolean;
  baseUrl?: string;
  healthEndpoint?: string;
}

export interface FeatureManifest {
  featureKey: string;
  displayName: string;
  description?: string;
  basePath?: string;
  version: string;
  environment?: string;
  auth?: FeatureManifestAuth;
  frontend?: FeatureManifestFrontend;
  backend?: FeatureManifestBackend;
  registry?: Record<string, unknown>;
  events?: Record<string, unknown>;
  workers?: Record<string, unknown>;
}