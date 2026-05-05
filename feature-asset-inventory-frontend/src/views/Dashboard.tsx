import { useEffect, useState } from "react";

import { listAssets, listStatuses } from "../services/inventory";
import type { Asset, AssetStatus } from "../types/inventory";

export default function Dashboard() {
  const [statuses, setStatuses] = useState<AssetStatus[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([listStatuses(), listAssets({ limit: 500 })])
      .then(([s, a]) => {
        setStatuses(s);
        setAssets(a);
      })
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <p style={{ color: "crimson" }}>{error}</p>;

  const counts: Record<string, number> = {};
  assets.forEach((a) => {
    counts[a.status_code] = (counts[a.status_code] ?? 0) + 1;
  });

  return (
    <div>
      <h2>Dashboard</h2>
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        {statuses.map((s) => (
          <div
            key={s.code}
            style={{
              border: "1px solid #ccc",
              padding: 12,
              minWidth: 140,
              borderRadius: 6,
            }}
          >
            <div style={{ fontSize: 12, color: "#666" }}>{s.label}</div>
            <div style={{ fontSize: 24, fontWeight: 600 }}>
              {counts[s.code] ?? 0}
            </div>
          </div>
        ))}
      </div>
      <h3 style={{ marginTop: 24 }}>Recent assets</h3>
      <ul>
        {assets.slice(0, 10).map((a) => (
          <li key={a.id}>
            <strong>{a.asset_tag}</strong> — {a.asset_type} — {a.status_code}
            {a.assigned_upn ? ` — ${a.assigned_upn}` : ""}
          </li>
        ))}
      </ul>
    </div>
  );
}
