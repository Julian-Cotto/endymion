export interface RegistryFeatureRecord {
    featureKey: string;
    version: string;
    environment?: string;
    auth?: Record<string, unknown>;
    manifest?: Record<string, unknown>;
  }
  
  export async function loadRegistryFeature(
    registryBaseUrl: string,
    featureKey: string
  ): Promise<RegistryFeatureRecord> {
    const response = await fetch(`${registryBaseUrl}/api/features/${featureKey}`);
  
    if (!response.ok) {
      throw new Error(`Failed to load registry feature ${featureKey}: ${response.status}`);
    }
  
    return (await response.json()) as RegistryFeatureRecord;
  }