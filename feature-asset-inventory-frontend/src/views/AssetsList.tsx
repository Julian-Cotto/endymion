import { useEffect, useState } from "react";

import { listAssets, listStatuses } from "../services/inventory";
import type { Asset, AssetStatus } from "../types/inventory";

interface Props {
  onSelect: (id: number) => void;
}

export default function AssetsList({ onSelect }: Props) {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [statuses, setStatuses] = useState<AssetStatus[]>([]);
  const [q, setQ] = useState("");
  const [statusCode, setStatusCode] = useState("");
  const [assetType, setAssetType] = useState("");
  const [includeArchived, setIncludeArchived] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listStatuses().then(setStatuses).catch((e) => setError(e.message));
  }, []);

  const reload = async () => {
    try {
      const data = await listAssets({
        q: q || undefined,
        status_code: statusCode || undefined,
        asset_type: assetType || undefined,
        include_archived: includeArchived,
        limit: 200,
      });
      setAssets(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    }
  };

  useEffect(() => {
    void reload();
  }, [statusCode, assetType, includeArchived]);

  return (
    <div>
      <h2>Assets</h2>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
        <input
          placeholder="Search tag/serial/model"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && void reload()}
        />
        <select value={statusCode} onChange={(e) => setStatusCode(e.target.value)}>
          <option value="">All statuses</option>
          {statuses.map((s) => (
            <option key={s.code} value={s.code}>
              {s.label}
            </option>
          ))}
        </select>
        <select value={assetType} onChange={(e) => setAssetType(e.target.value)}>
          <option value="">All types</option>
          <option value="laptop">Laptop</option>
          <option value="desktop">Desktop</option>
          <option value="thin_client">Thin client</option>
        </select>
        <label style={{ fontSize: 13, display: "flex", alignItems: "center", gap: 4 }}>
          <input
            type="checkbox"
            checked={includeArchived}
            onChange={(e) => setIncludeArchived(e.target.checked)}
          />
          Include archived
        </label>
        <button onClick={() => void reload()}>Search</button>
      </div>
      {error && <p style={{ color: "crimson" }}>{error}</p>}
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ textAlign: "left", borderBottom: "1px solid #ccc" }}>
            <th>Tag</th>
            <th>Serial</th>
            <th>Type</th>
            <th>Model</th>
            <th>OS</th>
            <th>Status</th>
            <th>Assigned</th>
          </tr>
        </thead>
        <tbody>
          {assets.map((a) => (
            <tr
              key={a.id}
              style={{ cursor: "pointer", borderBottom: "1px solid #eee" }}
              onClick={() => onSelect(a.id)}
            >
              <td>{a.asset_tag ?? "—"}</td>
              <td style={{ fontFamily: "monospace" }}>{a.serial_number}</td>
              <td>{a.asset_type}</td>
              <td>
                {a.manufacturer ?? ""} {a.model ?? ""}
              </td>
              <td>
                {a.os ?? ""} {a.os_version ?? ""}
              </td>
              <td>{a.status_code}</td>
              <td>{a.assigned_upn ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {assets.length === 0 && <p>No assets.</p>}
    </div>
  );
}
