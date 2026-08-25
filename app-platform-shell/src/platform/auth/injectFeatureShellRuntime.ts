import type { ShellFeatureRuntimeContractV1 } from "../contracts/shellFeatureAuth";

export function clearFeatureShellRuntime(): void {
  delete window.__FEATURE_SHELL_RUNTIME__;
}

export function injectFeatureShellRuntime(
  runtime: ShellFeatureRuntimeContractV1,
): void {
  window.__FEATURE_SHELL_RUNTIME__ = runtime;
}