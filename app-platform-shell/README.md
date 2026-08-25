# App Platform Shell

A **React + Vite + TypeScript** host that loads **feature microfrontends** at runtime. The shell resolves a **runtime feature list** (bootstrap-shaped JSON), picks a feature by **URL segment**, dynamically **imports** `frontend.entryUrl`, and calls **`mount(container, { manifest, session, runtime })`**.

The Vite app lives at the **repository root** (`package.json`, `src/`, `public/`, `docs/`).

---

## Repository layout

| Path | Purpose |
|------|---------|
| `src/app/` | `App.tsx` (MSAL + mock shell), `FeatureHost`, `ShellAuthProvider` |
| `src/platform/` | `loadRuntimeFeatures`, bootstrap/registry fetch, MSAL config, contracts, session snapshot |
| `docs/` | Runtime modes, platform overview, auth/runtime contracts |
| `platform_shell_development_guide.md` | Deeper bootstrap / manifest / mount pipeline |

---

## Requirements

- **Node.js** 18+ recommended

---

## Install and run

```bash
npm install
npm run dev
```

Open **http://localhost:3000** (port **3000** in `package.json`).

| Command | Description |
|---------|-------------|
| `npm run dev` | Dev server |
| `npm run build` | `tsc -b` + Vite production build |
| `npm run preview` | Preview production build |
| `npm test` | Vitest |

---

## Startup and auth modes

**`src/main.tsx`** initializes **`PublicClientApplication`** (`msalInstance.initialize()`), handles **`handleRedirectPromise()`**, then renders **`MsalProvider`** + **`App`**.

**`VITE_AUTH_MODE`** (`src/platform/auth/msalConfig.ts` → **`getShellAuthMode()`**):

| Value | Behavior |
|-------|----------|
| **`entra`** (`VITE_AUTH_MODE=entra`) | **`EntraShellApp`**: MSAL login / silent token for **`VITE_ENTRA_SCOPES`** (or legacy **`VITE_ENTRA_SCOPE`**), then **`ShellFrame`** with real session. |
| **`mock`** (default if unset or any other value) | **`MockShellApp`**: static dev session; **`accessToken`** from **`VITE_MOCK_ACCESS_TOKEN`**. |

Entra-related env vars are read in **`src/platform/auth/msalConfig.ts`** (e.g. **`VITE_ENTRA_CLIENT_ID`**, **`VITE_ENTRA_TENANT_ID`** / **`VITE_ENTRA_AUTHORITY`**, **`VITE_ENTRA_REDIRECT_URI`**, **`VITE_ENTRA_POST_LOGOUT_REDIRECT_URI`**, scopes above).

---

## How the shell picks a feature

**`App.tsx`** uses the first URL path segment as **`featureKey`** (default **`orders`**). For **`/`**, it may restore **`localStorage`** key **`app-platform-shell:last-feature-route`**. Navigation uses in-app **`navigate()`** (full page assign to preserve path) for **Orders** / **Catalog**.

**`FeatureHost`** receives **`bootstrapUrl={getBootstrapUrl()}`** and **`featureKey`**. It calls **`loadRuntimeFeatures({ bootstrapUrl, signal })`** so the fetch can be **aborted** on unmount or when **`sessionKey`** changes.

---

## Runtime configuration (`import.meta.env`)

Use **`.env.local`** at the repo root (gitignored). Start from **`.env.example`** (tracked template).

### Runtime source (`loadRuntimeFeatures`)

| Variable | Default (in code) | Meaning |
|----------|-------------------|---------|
| `VITE_RUNTIME_SOURCE_MODE` | `bootstrap` | **`bootstrap`** → `loadBootstrapResponse(url, { signal })`. **`registry`** → `loadRegistryRuntimeResponse` + **`normalizeRegistryRuntimeResponse`**. |

| Variable | Default (in `runtimeClientConfig.ts`) | Meaning |
|----------|---------------------------------------|---------|
| `VITE_BOOTSTRAP_URL` | `http://localhost:8001/api/runtime/features` | URL used in bootstrap mode (and passed from **`App`** into **`FeatureHost`**). |
| `VITE_REGISTRY_RUNTIME_URL` | `http://localhost:8010/api/runtime/features?environment=local` | Registry runtime URL in registry mode. |

More examples: **`docs/local-runtime-modes.md`**, architecture: **`docs/platform.md`**.

---

## HTTP calls to bootstrap / registry

**`loadBootstrapResponse`** / **`loadRegistryRuntimeResponse`**: **`GET`** with **`buildRuntimeRequestHeaders()`** — **`Accept: application/json`**, and **`Authorization: Bearer …`** when **`getShellSessionSnapshot()`** has a non-empty **`accessToken`**. **`FeatureHost`** keeps the snapshot in sync with the React session. Optional **`AbortSignal`** is passed through from **`FeatureHost`**.

Bootstrap JSON is validated with **`assertBootstrapResponse`** after fetch.

---

## Feature bundle contract

The remote module should export **`mount`** (or **`frontend.mountFunction`**). Context type is defined in **`bootstrapFeature.ts`**; it includes **`manifest`**, **`session`**, and **`ShellFeatureRuntimeContractV1`** as **`runtime`**.

**`FeatureHost`** treats a **function** return value from **`mount`** as cleanup and runs it when the load is superseded or the host unmounts.

---

## Globals exposed to features

- **`window.__FEATURE_SHELL_AUTH__`** — From **`resolveShellFeatureAuth`** + **`injectFeatureShellAuth`** when applicable (`src/platform/contracts/shellFeatureAuth.ts`).
- **`window.__FEATURE_SHELL_RUNTIME__`** — From **`injectFeatureShellRuntime`** with flags/permissions from the normalized runtime row.

---

## Further reading

- **`docs/local-runtime-modes.md`** — env examples and verification  
- **`docs/platform.md`** — platform architecture and contracts  
- **`docs/runtime-auth-contract-v1.md`** — v1 runtime/auth globals and mount shape  
- **`platform_shell_development_guide.md`** — bootstrap validation, manifest mapping, pipeline details  
- **`src/platform/contracts/bootstrapResponse.ts`** — bootstrap JSON shape  

---

## Summary

The shell loads **MSAL** (when configured), resolves **mock vs Entra** session, **GET**s runtime configuration (bootstrap or registry path), **normalizes** registry payloads to the bootstrap shape, **mounts** the selected feature with **abort/cleanup** behavior, and exposes **v1** globals for feature bundles.
