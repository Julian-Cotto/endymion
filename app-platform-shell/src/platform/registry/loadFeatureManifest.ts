import type { FeatureManifest } from "../contracts/featureManifest";

export async function loadFeatureManifest(url: string): Promise<FeatureManifest> {
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Failed to load feature manifest from ${url}: ${response.status}`);
  }

  return (await response.json()) as FeatureManifest;
}