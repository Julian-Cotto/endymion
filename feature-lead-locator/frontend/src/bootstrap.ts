import { mountFeature } from "./mount";
import type { ShellMountContext } from "./platform/shellContext";

export function mount(
  container: HTMLElement,
  context?: ShellMountContext,
) {
  return mountFeature(container, context);
}