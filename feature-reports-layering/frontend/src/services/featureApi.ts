import { apiGet } from "./apiClient";
import type { ShellMountContext } from "../platform/shellContext";

export type FeatureItem = { id: string; name: string; status: string };
export type FeatureItemsResponse = {
  feature_key: string;
  authenticated: boolean;
  user?: string;
  items: FeatureItem[];
};
export type HealthResponse = {
  status: string;
  service: string;
  feature_key: string;
  auth_mode: string;
};

export function getHealth(_shellContext?: ShellMountContext) {
  return apiGet<HealthResponse>("/health");
}

export function getFeatureItems(_shellContext?: ShellMountContext) {
  return apiGet<FeatureItemsResponse>("/items");
}