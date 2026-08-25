import React from "react";
import ReactDOM from "react-dom/client";
import { MsalProvider } from "@azure/msal-react";

import "./styles/index.css";

import App from "./app/App";
import { msalInstance } from "./platform/auth/msalConfig";

const rootElement = document.getElementById("root");

if (!rootElement) {
  throw new Error("Root element #root was not found.");
}

const root = ReactDOM.createRoot(rootElement);

function render(content: React.ReactNode): void {
  root.render(content);
}

function renderStartupError(error: unknown): void {
  const message =
    error instanceof Error ? error.message : "Failed to initialize the shell.";

  render(
    <div style={{ padding: 16 }}>
      <h1>App Platform Shell</h1>
      <h2>Startup failed</h2>
      <pre style={{ whiteSpace: "pre-wrap" }}>{message}</pre>
    </div>,
  );
}

async function bootstrap(): Promise<void> {
  try {
    await msalInstance.initialize();

    const result = await msalInstance.handleRedirectPromise();

    if (result?.account) {
      msalInstance.setActiveAccount(result.account);
      localStorage.removeItem("app-platform-shell:logout-requested");
    } else {
      const existingAccount =
        msalInstance.getActiveAccount() ?? msalInstance.getAllAccounts()[0];

      if (existingAccount) {
        msalInstance.setActiveAccount(existingAccount);
      }
    }

    render(
      <MsalProvider instance={msalInstance}>
        <App />
      </MsalProvider>,
    );
  } catch (error) {
    console.error("Shell startup failed", error);
    renderStartupError(error);
  }
}

void bootstrap();