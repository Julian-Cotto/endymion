import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const isMicrofrontendBuild = mode === "mf";
  const localPort = 3600;

  const sharedConfig = {
    plugins: [react()],
    server: {
      host: "0.0.0.0",
      port: localPort,
      cors: {
        origin: [
          "http://localhost:3000",
          "http://localhost:3600",
          "http://localhost:3300",
          "http://localhost:5173",
        ],
        methods: ["GET", "OPTIONS"],
        allowedHeaders: ["Content-Type", "Accept"],
        credentials: true,
      },
    },
    test: {
      environment: "jsdom",
      setupFiles: "./src/tests/setup.ts",
      globals: true,
    },
  };

  if (isMicrofrontendBuild) {
    return {
      ...sharedConfig,
      build: {
        lib: {
          entry: "src/bootstrap-entry.tsx",
          name: "LeadLocatorFeature",
          fileName: () => "bootstrap.js",
          formats: ["es"],
        },
        outDir: "dist/mf",
        emptyOutDir: true,
      },
    };
  }

  return {
    ...sharedConfig,
    build: {
      outDir: "dist/app",
      emptyOutDir: true,
    },
  };
});