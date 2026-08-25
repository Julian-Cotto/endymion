import type { FeatureModule } from "./bootstrapFeature";

export async function loadFeatureModule(entryUrl: string): Promise<FeatureModule> {
  return (await import(/* @vite-ignore */ entryUrl)) as FeatureModule;
}

