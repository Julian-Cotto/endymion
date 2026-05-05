import { useEffect, useState } from "react";

import {
  archiveAsset,
  assignAsset,
  changeAssetStatus,
  getAsset,
  getAssetHistory,
  listLocations,
  listStatuses,
  unassignAsset,
} from "../services/inventory";
import type {
  Asset,
  AssetHistoryEntry,
  AssetStatus,
  Location,
} from "../types/inventory";

interface Props {
  assetId: number;
  onBack: () => void;
}

export default function AssetDetail({ assetId, onBack }: Props) {
  const [asset, setAsset] = useState<Asset | null>(null);
  const [history, setHistory] = useState<AssetHistoryEntry[]>([]);
  const [statuses, setStatuses] = useState<AssetStatus[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [assignUpn, setAssignUpn] = useState("");
  const [assignLoc, setAssignLoc] = useState<number | "">("");
  const [statusTo, setStatusTo] = useState("");

  const reload = async () => {
    try {
      const [a, h] = await Promise.all([getAsset(assetId), getAssetHistory(assetId)]);
      setAsset(a);
      setHistory(h);
      setStatusTo(a.status_code);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    }
  };

  useEffect(() => {
    void reload();
    Promise.all([listStatuses(), listLocations()])
      .then(([s, l]) => {
        setStatuses(s);
        setLocations(l);
      })
      .catch((e) => setError(e.message));
  }, [assetId]);

  if (error) return <p style={{ color: "crimson" }}>{error}</p>;
  if (!asset) return <p>Loading…</p>;

  const isArchived = asset.archived_at !== null;

  return (
    <div>
      <button onClick={onBack}>← Back</button>
      <h2>
        {asset.asset_tag ?? asset.serial_number}{" "}
        <small style={{ color: "#666" }}>({asset.asset_type})</small>
      </h2>

      <Grid>
        <KV k="Serial" v={asset.serial_number} mono />
        <KV k="Status" v={asset.status_code} />
        <KV k="Manufacturer" v={asset.manufacturer ?? "—"} />
        <KV k="Model" v={asset.model ?? "—"} />
        <KV k="OS" v={`${asset.os ?? "—"} ${asset.os_version ?? ""}`} />
        <KV k="Assigned" v={asset.assigned_upn ?? "—"} />
        <KV
          k="Location"
          v={
            asset.location_id !== null
              ? locations.find((l) => l.id === asset.location_id)?.name ??
                String(asset.location_id)
              : "—"
          }
        />
        <KV k="Onboarded" v={asset.onboarded_at} />
        {isArchived && <KV k="Archived" v={asset.archived_at!} />}
      </Grid>

      {!isArchived && (
        <>
          <h3>Assign</h3>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <input
              placeholder="user@upn"
              value={assignUpn}
              onChange={(e) => setAssignUpn(e.target.value)}
            />
            <select
              value={assignLoc}
              onChange={(e) =>
                setAssignLoc(e.target.value === "" ? "" : Number(e.target.value))
              }
            >
              <option value="">— location —</option>
              {locations.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.name}
                </option>
              ))}
            </select>
            <button
              onClick={async () => {
                await assignAsset(asset.id, {
                  assigned_upn: assignUpn || undefined,
                  location_id: assignLoc === "" ? undefined : Number(assignLoc),
                });
                setAssignUpn("");
                setAssignLoc("");
                void reload();
              }}
              disabled={!assignUpn && assignLoc === ""}
            >
              Assign
            </button>
            {asset.assigned_upn && (
              <button
                onClick={async () => {
                  await unassignAsset(asset.id);
                  void reload();
                }}
              >
                Unassign
              </button>
            )}
          </div>

          <h3>Change status</h3>
          <div style={{ display: "flex", gap: 8 }}>
            <select
              value={statusTo}
              onChange={(e) => setStatusTo(e.target.value)}
            >
              {statuses.map((s) => (
                <option key={s.code} value={s.code}>
                  {s.label}
                </option>
              ))}
            </select>
            <button
              onClick={async () => {
                await changeAssetStatus(asset.id, { status_code: statusTo });
                void reload();
              }}
              disabled={statusTo === asset.status_code}
            >
              Update status
            </button>
          </div>

          <h3>Archive / offboard</h3>
          <button
            style={{ background: "#fee", color: "#a00", padding: "6px 12px" }}
            onClick={async () => {
              if (!confirm("Archive this asset?")) return;
              await archiveAsset(asset.id);
              void reload();
            }}
          >
            Archive asset
          </button>
        </>
      )}

      <h3 style={{ marginTop: 24 }}>History</h3>
      <ul>
        {history.map((h) => (
          <li key={h.id}>
            <code>{h.performed_at}</code> — <strong>{h.event_type}</strong>{" "}
            {h.from_value !== null && <>from <code>{h.from_value}</code> </>}
            {h.to_value !== null && <>to <code>{h.to_value}</code> </>}
            by {h.performed_by_upn ?? "—"}
            {h.notes ? ` (${h.notes})` : ""}
          </li>
        ))}
      </ul>
    </div>
  );
}

function Grid({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit,minmax(200px,1fr))",
        gap: 8,
        margin: "12px 0",
      }}
    >
      {children}
    </div>
  );
}

function KV({ k, v, mono }: { k: string; v: string; mono?: boolean }) {
  return (
    <div>
      <div style={{ fontSize: 12, color: "#666" }}>{k}</div>
      <div style={{ fontFamily: mono ? "monospace" : undefined }}>{v}</div>
    </div>
  );
}
