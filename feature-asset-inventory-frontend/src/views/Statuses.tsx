import { useEffect, useState } from "react";

import { createStatus, listStatuses, updateStatus } from "../services/inventory";
import type { AssetStatus } from "../types/inventory";

export default function Statuses() {
  const [statuses, setStatuses] = useState<AssetStatus[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [code, setCode] = useState("");
  const [label, setLabel] = useState("");
  const [isTerminal, setIsTerminal] = useState(false);
  const [sortOrder, setSortOrder] = useState(50);

  const reload = () =>
    listStatuses(true)
      .then(setStatuses)
      .catch((e) => setError(e.message));

  useEffect(() => {
    void reload();
  }, []);

  const create = async () => {
    setError(null);
    try {
      await createStatus({
        code: code.trim(),
        label: label.trim(),
        is_terminal: isTerminal,
        sort_order: sortOrder,
      });
      setCode("");
      setLabel("");
      setIsTerminal(false);
      setSortOrder(50);
      void reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    }
  };

  return (
    <div>
      <h2>Statuses</h2>
      {error && <p style={{ color: "crimson" }}>{error}</p>}

      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 12 }}>
        <input
          placeholder="code (lowercase_underscore)"
          value={code}
          onChange={(e) => setCode(e.target.value)}
        />
        <input
          placeholder="label"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
        />
        <input
          type="number"
          placeholder="sort"
          value={sortOrder}
          onChange={(e) => setSortOrder(Number(e.target.value))}
          style={{ width: 80 }}
        />
        <label style={{ fontSize: 13, display: "flex", alignItems: "center", gap: 4 }}>
          <input
            type="checkbox"
            checked={isTerminal}
            onChange={(e) => setIsTerminal(e.target.checked)}
          />
          terminal
        </label>
        <button onClick={() => void create()} disabled={!code || !label}>
          Add
        </button>
      </div>

      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ textAlign: "left", borderBottom: "1px solid #ccc" }}>
            <th>Code</th>
            <th>Label</th>
            <th>Sort</th>
            <th>Terminal</th>
            <th>Active</th>
          </tr>
        </thead>
        <tbody>
          {statuses.map((s) => (
            <tr key={s.code} style={{ borderBottom: "1px solid #eee" }}>
              <td><code>{s.code}</code></td>
              <td>{s.label}</td>
              <td>{s.sort_order}</td>
              <td>{s.is_terminal ? "yes" : ""}</td>
              <td>
                <input
                  type="checkbox"
                  checked={s.is_active}
                  onChange={async (e) => {
                    await updateStatus(s.code, { is_active: e.target.checked });
                    void reload();
                  }}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
