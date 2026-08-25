import React from "react";
import ReactDOM from "react-dom/client";

import App from "./App";
import { FeatureAuthProvider } from "./platform/authProvider";
import {
  setFeatureMountContext,
  setShellRuntimeContext,
  type ShellMountContext,
} from "./platform/shellContext";

export function mountFeature(
  container: HTMLElement,
  context?: ShellMountContext,
) {
  setFeatureMountContext(context);
  setShellRuntimeContext(context?.runtime);

  const root = ReactDOM.createRoot(container);

  root.render(
    <React.StrictMode>
      <FeatureAuthProvider>
        <App />
      </FeatureAuthProvider>
    </React.StrictMode>,
  );

  return () => {
    setFeatureMountContext(undefined);
    setShellRuntimeContext(undefined);
    root.unmount();
  };
}