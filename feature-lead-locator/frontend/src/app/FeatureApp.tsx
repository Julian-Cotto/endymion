import { FeatureHomePage } from "../components/FeatureHomePage";
import type { ShellMountContext } from "../platform/shellContext";

export function FeatureApp({
  shellContext,
}: {
  shellContext?: ShellMountContext;
}) {
  return <FeatureHomePage shellContext={shellContext} />;
}