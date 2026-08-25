export type RuntimeSourceMode = "bootstrap" | "registry";

function readEnv(name: string): string | undefined {
  const value = import.meta.env[name];

  if (typeof value !== "string") {
    return undefined;
  }

  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : undefined;
}

export function getRuntimeSourceMode(): RuntimeSourceMode {
  const value = (readEnv("VITE_RUNTIME_SOURCE_MODE") ?? "bootstrap").toLowerCase();

  if (value === "registry") {
    return "registry";
  }

  return "bootstrap";
}

export function getBootstrapUrl(): string {
  return readEnv("VITE_BOOTSTRAP_URL") ?? "http://localhost:8765/api/runtime/features";
}

export function getRegistryRuntimeUrl(): string {
  return (
    readEnv("VITE_REGISTRY_RUNTIME_URL") ??
    "http://localhost:8010/api/runtime/features?environment=local"
  );
}