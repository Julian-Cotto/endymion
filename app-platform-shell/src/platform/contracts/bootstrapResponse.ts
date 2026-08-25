export interface BootstrapUser {
    id: string;
    displayName: string;
    email?: string;
  }
  
  export interface BootstrapFeatureNav {
    label: string;
    icon: string;
    group?: string | null;
    order?: number | null;
  }
  
  export interface BootstrapFeatureFrontend {
    entryUrl: string;
    enabled?: boolean;
    mountFunction?: string;
  }
  
  export interface BootstrapFeatureBackend {
    apiBaseUrl: string;
    enabled?: boolean;
    healthEndpoint?: string;
  }
  
  export interface BootstrapFeatureAuthorization {
    requiredPermissions: string[];
    requiredFlags: string[];
  }
  
  export type BootstrapFeatureAuthMode = "none" | "mock" | "entra";
  
  export interface BootstrapFeatureAuth {
    required?: boolean;
    mode?: BootstrapFeatureAuthMode;
    shellAuthRequired?: boolean;
    tokenForwarding?: boolean;
    tokenStrategy?: string;
    allowedDevModes?: BootstrapFeatureAuthMode[];
    roles?: string[];
  }
  
  export interface BootstrapFeature {
    featureKey: string;
    displayName: string;
    route: string;
    version: string;
    nav: BootstrapFeatureNav;
    frontend: BootstrapFeatureFrontend;
    backend: BootstrapFeatureBackend;
    authorization: BootstrapFeatureAuthorization;
    auth?: BootstrapFeatureAuth;
  }
  
  export interface BootstrapMetadata {
    source: string;
    generatedBy?: string;
    generatedAtUtc?: string;
  }
  
  export interface BootstrapResponse {
    environment: string;
    user: BootstrapUser;
    permissions: string[];
    flags: Record<string, boolean>;
    features: BootstrapFeature[];
    metadata: BootstrapMetadata;
  }