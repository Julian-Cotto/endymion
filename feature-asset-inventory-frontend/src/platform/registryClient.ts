export async function getFeatureRegistryRecord() {
  return {
    featureKey: "asset-inventory",
    basePath: "/inventory/it",
    apiBasePath: "/api/inventory/it"
  };
}