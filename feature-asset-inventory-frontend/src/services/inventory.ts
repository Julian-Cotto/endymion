import { apiDelete, apiGet, apiPatch, apiPost } from "./apiClient";
import type {
  Asset,
  AssetAssignPayload,
  AssetCreatePayload,
  AssetHistoryEntry,
  AssetStatus,
  AssetStatusChangePayload,
  AssetStatusCreatePayload,
  Location,
  LocationCreatePayload,
} from "../types/inventory";

// statuses
export const listStatuses = (includeInactive = false) =>
  apiGet<AssetStatus[]>(`/statuses?include_inactive=${includeInactive}`);

export const createStatus = (payload: AssetStatusCreatePayload) =>
  apiPost<AssetStatus>("/statuses", payload);

export const updateStatus = (
  code: string,
  payload: Partial<AssetStatusCreatePayload>,
) => apiPatch<AssetStatus>(`/statuses/${encodeURIComponent(code)}`, payload);

// locations
export const listLocations = (includeInactive = false) =>
  apiGet<Location[]>(`/locations?include_inactive=${includeInactive}`);

export const getLocation = (id: number) =>
  apiGet<Location>(`/locations/${id}`);

export const createLocation = (payload: LocationCreatePayload) =>
  apiPost<Location>("/locations", payload);

export const updateLocation = (
  id: number,
  payload: Partial<LocationCreatePayload>,
) => apiPatch<Location>(`/locations/${id}`, payload);

export const deleteLocation = (id: number) =>
  apiDelete<void>(`/locations/${id}`);

// assets
export interface AssetsQuery {
  q?: string;
  asset_type?: string;
  status_code?: string;
  location_id?: number;
  assigned_upn?: string;
  include_archived?: boolean;
  limit?: number;
  offset?: number;
}

function toQuery(q: AssetsQuery): string {
  const params = new URLSearchParams();
  Object.entries(q).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") params.set(k, String(v));
  });
  const s = params.toString();
  return s ? `?${s}` : "";
}

export const listAssets = (q: AssetsQuery = {}) =>
  apiGet<Asset[]>(`/assets${toQuery(q)}`);

export const getAsset = (id: number) => apiGet<Asset>(`/assets/${id}`);

export const lookupAssetBySerial = (serial: string) =>
  apiGet<Asset>(`/assets/lookup?serial=${encodeURIComponent(serial)}`);

export const onboardAsset = (payload: AssetCreatePayload) =>
  apiPost<Asset>("/assets", payload);

export const updateAsset = (
  id: number,
  payload: Partial<AssetCreatePayload>,
) => apiPatch<Asset>(`/assets/${id}`, payload);

export const assignAsset = (id: number, payload: AssetAssignPayload) =>
  apiPost<Asset>(`/assets/${id}/assign`, payload);

export const unassignAsset = (id: number) =>
  apiPost<Asset>(`/assets/${id}/unassign`, {});

export const changeAssetStatus = (
  id: number,
  payload: AssetStatusChangePayload,
) => apiPost<Asset>(`/assets/${id}/status`, payload);

export const archiveAsset = (id: number, notes?: string) =>
  apiPost<Asset>(`/assets/${id}/archive`, { notes });

export const getAssetHistory = (id: number) =>
  apiGet<AssetHistoryEntry[]>(`/assets/${id}/history`);
