import type { BootstrapFeature, BootstrapResponse } from "./bootstrapResponse";

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function isBooleanRecord(value: unknown): value is Record<string, boolean> {
  return (
    isObject(value) &&
    Object.values(value).every((item) => typeof item === "boolean")
  );
}

function assertFeature(feature: unknown): asserts feature is BootstrapFeature {
  if (!isObject(feature)) {
    throw new Error("Bootstrap feature entry must be an object.");
  }

  if (typeof feature.featureKey !== "string" || !feature.featureKey) {
    throw new Error("Bootstrap feature.featureKey must be a non-empty string.");
  }

  if (typeof feature.displayName !== "string" || !feature.displayName) {
    throw new Error("Bootstrap feature.displayName must be a non-empty string.");
  }

  if (typeof feature.route !== "string" || !feature.route.startsWith("/")) {
    throw new Error(`Bootstrap feature '${String(feature.featureKey ?? "unknown")}' has invalid route.`);
  }

  if (typeof feature.version !== "string" || !feature.version) {
    throw new Error(`Bootstrap feature '${String(feature.featureKey ?? "unknown")}' has invalid version.`);
  }

  if (!isObject(feature.nav) || typeof feature.nav.label !== "string" || typeof feature.nav.icon !== "string") {
    throw new Error(`Bootstrap feature '${String(feature.featureKey ?? "unknown")}' has invalid nav.`);
  }

  if (!isObject(feature.frontend) || typeof feature.frontend.entryUrl !== "string" || !feature.frontend.entryUrl) {
    throw new Error(`Bootstrap feature '${String(feature.featureKey ?? "unknown")}' has invalid frontend.entryUrl.`);
  }

  if (!isObject(feature.backend) || typeof feature.backend.apiBaseUrl !== "string" || !feature.backend.apiBaseUrl) {
    throw new Error(`Bootstrap feature '${String(feature.featureKey ?? "unknown")}' has invalid backend.apiBaseUrl.`);
  }

  if (
    !isObject(feature.authorization) ||
    !isStringArray(feature.authorization.requiredPermissions) ||
    !isStringArray(feature.authorization.requiredFlags)
  ) {
    throw new Error(`Bootstrap feature '${String(feature.featureKey ?? "unknown")}' has invalid authorization.`);
  }
}

export function assertBootstrapResponse(value: unknown): asserts value is BootstrapResponse {
  if (!isObject(value)) {
    throw new Error("Bootstrap response must be an object.");
  }

  if (typeof value.environment !== "string" || !value.environment) {
    throw new Error("Bootstrap response.environment must be a non-empty string.");
  }

  if (!isObject(value.user) || typeof value.user.id !== "string" || typeof value.user.displayName !== "string") {
    throw new Error("Bootstrap response.user is invalid.");
  }

  if (!isStringArray(value.permissions)) {
    throw new Error("Bootstrap response.permissions must be a string array.");
  }

  if (!isBooleanRecord(value.flags)) {
    throw new Error("Bootstrap response.flags must be an object map of booleans.");
  }

  if (!Array.isArray(value.features)) {
    throw new Error("Bootstrap response.features must be an array.");
  }

  value.features.forEach(assertFeature);

  if (!isObject(value.metadata) || typeof value.metadata.source !== "string") {
    throw new Error("Bootstrap response.metadata is invalid.");
  }
}