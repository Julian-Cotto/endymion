import { useEffect, useState } from "react";

import ScanInput from "../components/ScanInput";
import {
  listLocations,
  listStatuses,
  lookupAssetBySerial,
  onboardAsset,
} from "../services/inventory";
import type { AssetStatus, AssetType, Location } from "../types/inventory";

interface Props {
  onCreated: (assetId: number) => void;
}

const TYPE_OPTIONS: { value: AssetType; label: string }[] = [
  { value: "laptop", label: "Laptop" },
  { value: "desktop", label: "Desktop" },
  { value: "thin_client", label: "Thin client" },
];

export default function OnboardAsset({ onCreated }: Props) {
  const [serial, setSerial] = useState("");
  const [assetTag, setAssetTag] = useState("");
  const [assetType, setAssetType] = useState<AssetType>("laptop");
  const [manufacturer, setManufacturer] = useState("");
  const [model, setModel] = useState("");
  const [os, setOs] = useState("");
  const [osVersion, setOsVersion] = useState("");
  const [statusCode, setStatusCode] = useState("in_warehouse");
  const [locationId, setLocationId] = useState<number | "">("");
  const [notes, setNotes] = useState("");
  const [duplicate, setDuplicate] = useState<number | null>(null);
  const [statuses, setStatuses] = useState<AssetStatus[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    Promise.all([listStatuses(), listLocations()])
      .then(([s, l]) => {
        setStatuses(s);
        setLocations(l);
      })
      .catch((e) => setError(e.message));
  }, []);

  async function handleScan(value: string) {
    setSerial(value);
    setDuplicate(null);
    try {
      const existing = await lookupAssetBySerial(value);
      setDuplicate(existing.id);
    } catch {
      // 404 expected for new asset
    }
  }

  async function submit() {
    setError(null);
    setSubmitting(true);
    try {
      const created = await onboardAsset({
        asset_tag: assetTag.trim() || null,
        serial_number: serial.trim(),
        asset_type: assetType,
        manufacturer: manufacturer || null,
        model: model || null,
        os: os || null,
        os_version: osVersion || null,
        status_code: statusCode,
        location_id: locationId === "" ? null : Number(locationId),
        notes: notes || null,
      });
      onCreated(created.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to onboard");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      <h2>Onboard asset</h2>
      <div style={{ display: "grid", gap: 12, maxWidth: 480 }}>
        <ScanInput
          value={serial}
          onChange={setSerial}
          onScan={handleScan}
          label="Serial number (scan or type)"
        />
        {duplicate !== null && (
          <div style={{ color: "crimson" }}>
            Serial already exists as asset #{duplicate}.
          </div>
        )}
        <Field label="Asset tag (optional)">
          <input
            value={assetTag}
            onChange={(e) => setAssetTag(e.target.value)}
            placeholder="leave blank if none"
          />
        </Field>
        <Field label="Type">
          <select
            value={assetType}
            onChange={(e) => setAssetType(e.target.value as AssetType)}
          >
            {TYPE_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Manufacturer">
          <input
            value={manufacturer}
            onChange={(e) => setManufacturer(e.target.value)}
          />
        </Field>
        <Field label="Model">
          <input value={model} onChange={(e) => setModel(e.target.value)} />
        </Field>
        <div style={{ display: "flex", gap: 8 }}>
          <Field label="OS">
            <input value={os} onChange={(e) => setOs(e.target.value)} />
          </Field>
          <Field label="OS version">
            <input
              value={osVersion}
              onChange={(e) => setOsVersion(e.target.value)}
            />
          </Field>
        </div>
        <Field label="Status">
          <select
            value={statusCode}
            onChange={(e) => setStatusCode(e.target.value)}
          >
            {statuses.map((s) => (
              <option key={s.code} value={s.code}>
                {s.label}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Location (optional)">
          <select
            value={locationId}
            onChange={(e) =>
              setLocationId(e.target.value === "" ? "" : Number(e.target.value))
            }
          >
            <option value="">— none —</option>
            {locations.map((l) => (
              <option key={l.id} value={l.id}>
                {l.name} ({l.type})
              </option>
            ))}
          </select>
        </Field>
        <Field label="Notes">
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={3}
          />
        </Field>
        {error && <div style={{ color: "crimson" }}>{error}</div>}
        <button
          onClick={() => void submit()}
          disabled={submitting || !serial.trim() || duplicate !== null}
        >
          {submitting ? "Saving…" : "Onboard asset"}
        </button>
      </div>
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", flex: 1 }}>
      <label style={{ fontSize: 12, marginBottom: 4 }}>{label}</label>
      {children}
    </div>
  );
}
