export type AssetType = "laptop" | "desktop" | "thin_client";
export type LocationType = "warehouse" | "site";

export interface AssetStatus {
  code: string;
  label: string;
  is_terminal: boolean;
  sort_order: number;
  is_active: boolean;
}

export interface Location {
  id: number;
  code: string;
  name: string;
  type: LocationType;
  address: string | null;
  is_active: boolean;
}

export interface Asset {
  id: number;
  asset_tag: string | null;
  serial_number: string;
  asset_type: AssetType;
  manufacturer: string | null;
  model: string | null;
  os: string | null;
  os_version: string | null;
  status_code: string;
  location_id: number | null;
  assigned_upn: string | null;
  assigned_at: string | null;
  onboarded_at: string;
  archived_at: string | null;
  notes: string | null;
}

export interface AssetHistoryEntry {
  id: number;
  asset_id: number;
  event_type: string;
  from_value: string | null;
  to_value: string | null;
  performed_by_upn: string | null;
  performed_at: string;
  notes: string | null;
}

export interface AssetCreatePayload {
  asset_tag?: string | null;
  serial_number: string;
  asset_type: AssetType;
  manufacturer?: string | null;
  model?: string | null;
  os?: string | null;
  os_version?: string | null;
  status_code?: string;
  location_id?: number | null;
  notes?: string | null;
}

export interface AssetAssignPayload {
  assigned_upn?: string | null;
  location_id?: number | null;
  notes?: string | null;
}

export interface AssetStatusChangePayload {
  status_code: string;
  notes?: string | null;
}

export interface LocationCreatePayload {
  code: string;
  name: string;
  type: LocationType;
  address?: string | null;
  is_active?: boolean;
}

export interface AssetStatusCreatePayload {
  code: string;
  label: string;
  is_terminal?: boolean;
  sort_order?: number;
  is_active?: boolean;
}
