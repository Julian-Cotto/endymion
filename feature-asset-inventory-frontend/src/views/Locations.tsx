import { useEffect, useState } from "react";

import {
  createLocation,
  deleteLocation,
  listLocations,
  updateLocation,
} from "../services/inventory";
import type { Location, LocationType } from "../types/inventory";

export default function Locations() {
  const [locations, setLocations] = useState<Location[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [type, setType] = useState<LocationType>("warehouse");
  const [address, setAddress] = useState("");

  const reload = () =>
    listLocations(true)
      .then(setLocations)
      .catch((e) => setError(e.message));

  useEffect(() => {
    void reload();
  }, []);

  const create = async () => {
    setError(null);
    try {
      await createLocation({
        code: code.trim(),
        name: name.trim(),
        type,
        address: address || null,
      });
      setCode("");
      setName("");
      setAddress("");
      void reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    }
  };

  return (
    <div>
      <h2>Locations</h2>
      {error && <p style={{ color: "crimson" }}>{error}</p>}

      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 12 }}>
        <input placeholder="code" value={code} onChange={(e) => setCode(e.target.value)} />
        <input placeholder="name" value={name} onChange={(e) => setName(e.target.value)} />
        <select value={type} onChange={(e) => setType(e.target.value as LocationType)}>
          <option value="warehouse">warehouse</option>
          <option value="site">site</option>
        </select>
        <input
          placeholder="address"
          value={address}
          onChange={(e) => setAddress(e.target.value)}
        />
        <button onClick={() => void create()} disabled={!code || !name}>
          Add
        </button>
      </div>

      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ textAlign: "left", borderBottom: "1px solid #ccc" }}>
            <th>Code</th>
            <th>Name</th>
            <th>Type</th>
            <th>Address</th>
            <th>Active</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {locations.map((l) => (
            <tr key={l.id} style={{ borderBottom: "1px solid #eee" }}>
              <td>{l.code}</td>
              <td>{l.name}</td>
              <td>{l.type}</td>
              <td>{l.address ?? ""}</td>
              <td>
                <input
                  type="checkbox"
                  checked={l.is_active}
                  onChange={async (e) => {
                    await updateLocation(l.id, { is_active: e.target.checked });
                    void reload();
                  }}
                />
              </td>
              <td>
                <button
                  onClick={async () => {
                    if (!confirm(`Delete ${l.name}?`)) return;
                    try {
                      await deleteLocation(l.id);
                      void reload();
                    } catch (err) {
                      alert(err instanceof Error ? err.message : String(err));
                    }
                  }}
                >
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
