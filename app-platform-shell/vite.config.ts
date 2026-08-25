import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: true,
    allowedHosts: [
      "localhost",
      ".ngrok-free.dev",
      "cozily-deceiver-tricky.ngrok-free.dev",
    ],
    // Same-origin proxies for local dev — lets one ngrok tunnel cover
    // shell + APIs + feature MFEs. Production serves these via real
    // path-based routing so this block is dev-only.
    proxy: {
      // Feature MFE — keep prefix on forward so feature's vite `base` matches.
      "/_mfe/asset-inventory": {
        target: "http://localhost:3200",
        ws: true,
        changeOrigin: false,
      },
      "/_mfe/continued-education": {
        target: "http://localhost:3300",
        ws: true,
        changeOrigin: false,
      },
      "/_mfe/document-compliance": {
        target: "http://localhost:3400",
        ws: true,
        changeOrigin: false,
      },
      // Bootstrap-api: /api/shell/*, /api/runtime/features
      "/api/shell": {
        target: "http://localhost:8765",
        changeOrigin: true,
      },
      "/api/runtime": {
        target: "http://localhost:8765",
        changeOrigin: true,
      },
      // Inventory backend — feature reuses shell origin, no CORS dance.
      "/api/inventory": {
        target: "http://localhost:8200",
        changeOrigin: true,
      },
      // Continued Education backend.
      "/api/education": {
        target: "http://localhost:8300",
        changeOrigin: true,
      },
      // Document Compliance backend.
      "/api/document-compliance": {
        target: "http://localhost:8400",
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
    setupFiles: ["./src/test/setup.ts"],
  },
});