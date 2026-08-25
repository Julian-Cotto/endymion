export async function getFeatureRegistryRecord() {
  return {
    featureKey: "lead-locator",
    basePath: "/leads",
    apiBasePath: "/api/leads"
  };
}