import { bootstrapFeature } from "../bootstrap/bootstrapFeature";
import type { ShellUserSession } from "../auth/sessionTypes";
import type { FeatureManifest } from "../contracts/featureManifest";
import type { ShellFeatureRuntimeContractV1 } from "../contracts/shellFeatureAuth";

export interface RunFeatureParams {
  container: HTMLElement;
  session: ShellUserSession;

  /**
   * Legacy/standalone mode.
   *
   * Use this only when running a feature directly from a manifest URL.
   * The Shell runtime path should prefer `manifest` + `runtime`.
   */
  manifestUrl?: string;

  /**
   * Preferred Shell runtime mode.
   *
   * App.tsx loads Bootstrap runtime once, selects a feature, then passes the
   * normalized manifest/runtime contract into FeatureHost.
   */
  manifest?: FeatureManifest;
  runtime?: ShellFeatureRuntimeContractV1;
}

export async function runFeature(params: RunFeatureParams): Promise<unknown> {
  return bootstrapFeature(params);
}