import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { FeatureAuthProvider } from "./platform/authProvider";

// Standalone dev only: seed a mock shell session so the feature renders and
// talks to the local backend (port 8500). In the shell, the host injects these.
if (import.meta.env.DEV && !window.__FEATURE_SHELL_AUTH__) {
  window.__FEATURE_SHELL_AUTH__ = {
    version: "v1",
    isAuthenticated: true,
    authMode: "mock",
    userId: "dev-user",
    userName: "Local Dev User",
    email: "dev@example.local",
    roles: ["reports-layering.view", "reports-layering.create", "reports-layering.admin"],
    accessToken: "dev-token",
  };
  window.__FEATURE_SHELL_RUNTIME__ = {
    version: "v1",
    backend: { baseUrl: "http://localhost:8500/api/reports" },
  } as never;
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