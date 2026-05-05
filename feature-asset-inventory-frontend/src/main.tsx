import React from "react";
import ReactDOM from "react-dom/client";

import App from "./App";
import { FeatureAuthProvider } from "./platform/authProvider";

if (import.meta.env.DEV && typeof window !== "undefined") {
  if (!window.__FEATURE_SHELL_AUTH__) {
    window.__FEATURE_SHELL_AUTH__ = {
      version: "v1",
      authMode: "mock",
      isAuthenticated: true,
      userId: "dev-user",
      userName: "dev@local",
      email: "dev@local",
      roles: ["admin"],
      accessToken: "dev-token",
    };
  }
  if (!window.__FEATURE_SHELL_RUNTIME__) {
    // Same-origin path so requests work behind any host (LAN IP, ngrok tunnel,
    // localhost). Vite proxy forwards /api/inventory/it -> :8200.
    window.__FEATURE_SHELL_RUNTIME__ = {
      version: "v1",
      environment: "local",
      featureKey: "asset-inventory",
      backend: {
        baseUrl: "/api/inventory/it",
        enabled: true,
      },
      flags: {},
      permissions: ["asset-inventory.view", "asset-inventory.write", "asset-inventory.manage"],
    };
  }
}

const rootElement = document.getElementById("root");
if (!rootElement) throw new Error("Root element not found.");

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <FeatureAuthProvider>
      <App />
    </FeatureAuthProvider>
  </React.StrictMode>
);
