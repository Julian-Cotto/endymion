import { useState } from "react";

import { useFeatureAuth } from "./platform/authProvider";
import AssetDetail from "./views/AssetDetail";
import AssetsList from "./views/AssetsList";
import Dashboard from "./views/Dashboard";
import Locations from "./views/Locations";
import OnboardAsset from "./views/OnboardAsset";
import Statuses from "./views/Statuses";

const FEATURE_NAME = "IT Asset Inventory";

type View =
  | { kind: "dashboard" }
  | { kind: "assets" }
  | { kind: "asset"; id: number }
  | { kind: "onboard" }
  | { kind: "locations" }
  | { kind: "statuses" };

const TABS: { kind: View["kind"]; label: string; admin?: boolean }[] = [
  { kind: "dashboard", label: "Dashboard" },
  { kind: "assets", label: "Assets" },
  { kind: "onboard", label: "Onboard" },
  { kind: "locations", label: "Locations", admin: true },
  { kind: "statuses", label: "Statuses", admin: true },
];

export default function App() {
  const auth = useFeatureAuth();
  const [view, setView] = useState<View>({ kind: "dashboard" });

  if (!auth.isAuthenticated && auth.authMode === "entra") {
    return (
      <div>
        <h1>{FEATURE_NAME}</h1>
        <p>This feature requires shell authentication.</p>
      </div>
    );
  }

  const isAdmin =
    auth.roles?.includes("admin") ||
    auth.permissions?.includes("asset-inventory.manage") ||
    auth.permissions?.includes("*");

  const tabs = TABS.filter((t) => !t.admin || isAdmin);

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", padding: 16 }}>
      <h1 style={{ marginTop: 0 }}>{FEATURE_NAME}</h1>
      <p style={{ color: "#666", marginTop: 0 }}>
        Signed in as {auth.userName ?? auth.email ?? "unknown"}
      </p>

      <nav style={{ display: "flex", gap: 8, marginBottom: 16, borderBottom: "1px solid #ccc" }}>
        {tabs.map((t) => {
          const active =
            view.kind === t.kind ||
            (t.kind === "assets" && view.kind === "asset");
          return (
            <button
              key={t.kind}
              onClick={() => setView({ kind: t.kind } as View)}
              style={{
                background: "none",
                border: "none",
                padding: "8px 12px",
                borderBottom: active ? "2px solid #06c" : "2px solid transparent",
                fontWeight: active ? 600 : 400,
                cursor: "pointer",
              }}
            >
              {t.label}
            </button>
          );
        })}
      </nav>

      {view.kind === "dashboard" && <Dashboard />}
      {view.kind === "assets" && (
        <AssetsList onSelect={(id) => setView({ kind: "asset", id })} />
      )}
      {view.kind === "asset" && (
        <AssetDetail
          assetId={view.id}
          onBack={() => setView({ kind: "assets" })}
        />
      )}
      {view.kind === "onboard" && (
        <OnboardAsset
          onCreated={(id) => setView({ kind: "asset", id })}
        />
      )}
      {view.kind === "locations" && <Locations />}
      {view.kind === "statuses" && <Statuses />}
    </div>
  );
}
