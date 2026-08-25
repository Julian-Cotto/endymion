# App Platform — Shell & Feature System

## Overview

This repository contains the **Shell Application** for a modular, feature-based platform.

The platform enables:

* Dynamic microfrontend loading
* Centralized authentication (Microsoft Entra ID)
* Feature-level authorization
* Runtime configuration via a bootstrap-shaped **GET** (direct bootstrap URL or registry runtime URL normalized in the shell)
* Optional **registry** mode (`VITE_RUNTIME_SOURCE_MODE=registry`)

---

## Architecture

### High-Level Flow

```
User → Shell (mock or MSAL) → GET runtime JSON (bootstrap or registry URL) → normalize (registry) → mount(feature)
```

---

## Core Components

### Shell application

* React + Vite + `@azure/msal-browser` / `@azure/msal-react`
* **`VITE_AUTH_MODE`**: **`mock`** (default) or **`entra`** — see `src/platform/auth/msalConfig.ts` and `src/app/App.tsx`
* **`main.tsx`**: MSAL `initialize()` + `handleRedirectPromise()` before `MsalProvider` + `App`
* Hosts and mounts microfrontends; passes **`manifest`**, **`session`**, and **`runtime`** into **`mount`**

---

### Runtime / bootstrap API (backend)

The shell does **not** hardcode a single path; URLs come from env with code defaults in `src/platform/runtime/runtimeClientConfig.ts`:

* **Bootstrap mode** (default): `GET` **`VITE_BOOTSTRAP_URL`** or default **`http://localhost:8001/api/runtime/features`**
* **Registry mode**: `GET` **`VITE_REGISTRY_RUNTIME_URL`** or default **`http://localhost:8010/api/runtime/features?environment=local`**, then **`normalizeRegistryRuntimeResponse`** to the same JSON shape as bootstrap.

Typical backend responsibilities (outside this repo):

* Authenticate the caller (e.g. JWT on `Authorization: Bearer …` — the shell forwards **`accessToken`** from the session snapshot when present)
* Return **`user`**, **`permissions`**, **`flags`**, **`features[]`**, **`metadata`**, **`environment`**

---

### Registry (optional)

* Backend may expose a **registry** runtime JSON contract (`src/platform/contracts/registryRuntimeResponse.ts`)
* Shell **`loadRegistryRuntimeResponse`** + **`normalizeRegistryRuntimeResponse`** → **`BootstrapResponse`** for the rest of the pipeline

---

### Feature Module

Each feature includes:

* Microfrontend (React + Vite)
* Backend service (FastAPI)
* Manifest (contract)
* Optional jobs/workers/listeners

---

## Runtime flow

### Step-by-step

1. User opens the shell; **`main.tsx`** initializes MSAL and renders **`App`** inside **`MsalProvider`**.
2. **`App`**: if **`VITE_AUTH_MODE=entra`**, MSAL login / silent acquire for **`VITE_ENTRA_SCOPES`**; otherwise **mock** session with optional **`VITE_MOCK_ACCESS_TOKEN`**.
3. **`FeatureHost`** updates **`setShellSessionSnapshot(session)`** and calls **`loadRuntimeFeatures({ bootstrapUrl: getBootstrapUrl(), signal })`**.
4. Runtime **`GET`** uses **`buildRuntimeRequestHeaders()`** (Bearer when snapshot has **`accessToken`**). Bootstrap JSON is **`assertBootstrapResponse`**-validated.
5. Response includes **`user`**, **`permissions`**, **`flags`**, **`features`**, etc.
6. Shell selects **`featureKey`**, builds **`FeatureManifest`**, runs **`bootstrapFeature`** (sets **`window.__FEATURE_SHELL_*`**, dynamic **`import(entryUrl)`**).
7. **`mount(container, { manifest, session, runtime })`** — optional **function** return for cleanup (see **`FeatureHost`** **`asCleanup`**).

---

## Feature Contract

### Bootstrap Feature Shape

```ts
{
  featureKey: string
  displayName: string
  route: string
  version: string

  frontend: {
    enabled: boolean
    entryUrl: string
    mountFunction: string
  }

  backend: {
    enabled: boolean
    apiBaseUrl: string
    healthEndpoint?: string
  }

  authorization: {
    requiredPermissions: string[]
    requiredFlags: string[]
  }

  auth: {
    required?: boolean
    mode?: "entra" | "mock" | "none"
    tokenForwarding?: boolean
    tokenStrategy?: "forwarded-bearer" | "none"
    allowedDevModes?: string[]
    roles?: string[]
  }
}
```

---

### Microfrontend mount contract

Each feature should export **`mount`** (or the name from **`frontend.mountFunction`**):

```ts
export function mount(
  container: HTMLElement,
  context: {
    manifest: FeatureManifest;
    session: ShellUserSession;
    runtime: ShellFeatureRuntimeContractV1;
  },
): unknown;
```

The shell may receive a **function** back and use it as **cleanup** when the route/session changes or the host unmounts. Prefer idempotent mount and avoid calling **`createRoot()`** multiple times on the same container without teardown.

---

## Authentication

### Modes

* **`mock`** (default): dev **`ShellUserSession`** in **`MockShellApp`**; optional **`VITE_MOCK_ACCESS_TOKEN`** on the session for API Bearer headers.
* **`entra`**: **`EntraShellApp`** uses MSAL **`loginRedirect`** / **`acquireTokenSilent`** with **`VITE_ENTRA_SCOPES`** (comma- or space-separated list; legacy **`VITE_ENTRA_SCOPE`** supported). Config from **`msalConfig.ts`** (`VITE_ENTRA_CLIENT_ID`, **`VITE_ENTRA_AUTHORITY`** or tenant-based authority, redirect URIs).

### Flow (Entra)

1. **`loginRedirect`** when no account (after **`InteractionStatus.None`**).
2. Silent token for API scopes; on **`InteractionRequiredAuthError`**, **`acquireTokenRedirect`**.
3. **`ShellUserSession`** holds **`accessToken`** for **`buildRuntimeRequestHeaders`** and for **`mount`** context.
4. Logout: **`logoutRedirect()`** and clearing **`app-platform-shell:last-feature-route`** in **`App.tsx`**.

---

### Token Usage

* JWT validated in backend
* Claims → roles → permissions
* Permissions drive feature visibility

---

### Logout

```ts
logoutRedirect()
```

* Clears MSAL session
* Clears local storage state

---

## Development

### Run Shell

```bash
npm install
npm run dev
```

---

### Environment Configuration

`.env.local`

#### Entra mode

```env
VITE_AUTH_MODE=entra
VITE_RUNTIME_SOURCE_MODE=bootstrap
VITE_BOOTSTRAP_URL=http://localhost:8001/api/runtime/features
VITE_ENTRA_CLIENT_ID=...
VITE_ENTRA_TENANT_ID=...   # optional if VITE_ENTRA_AUTHORITY is set
VITE_ENTRA_AUTHORITY=https://login.microsoftonline.com/<tenant>   # optional alternative to tenant id
VITE_ENTRA_SCOPES=api://<api-app-id>/.default
VITE_ENTRA_REDIRECT_URI=http://localhost:3000
```

---

#### Mock mode

```env
VITE_AUTH_MODE=mock
VITE_MOCK_ACCESS_TOKEN=dev-token
VITE_BOOTSTRAP_URL=http://localhost:8001/api/runtime/features
```

---

### Local Development Flow

1. Start Bootstrap API
2. Start feature frontends (ports 3200, 3300, etc.)
3. Start Shell
4. Navigate to:

```
http://localhost:3000/orders
http://localhost:3000/catalog
```

---

## Production

### Deployment Model

| Component     | Recommended Hosting          |
| ------------- | ---------------------------- |
| Shell         | Static Web Apps              |
| Bootstrap API | App Service / Container      |
| Features      | Static Web Apps / Containers |
| Registry      | App Service / Container      |

---

### Security

* Entra ID required
* JWT validation enforced
* No mock mode in production
* Token forwarding controlled per feature

---

### Observability

* Log Analytics integration
* request_id propagation
* structured logging (JSON)

---

## Registry vs Bootstrap

| Aspect    | Bootstrap API    | Registry            |
| --------- | ---------------- | ------------------- |
| Source    | Computed runtime | Stored manifests    |
| Filtering | Yes              | No (raw data)       |
| Auth      | Backend validates caller | Same; shell still sends **Bearer** when session has **`accessToken`** |
| Output    | Final config     | Needs normalization |

---

## Troubleshooting

### 401 Unauthorized

* Missing token
* Invalid scope
* Token not forwarded

---

### Login Loop

* Incorrect redirect URI
* Missing scopes
* MSAL misconfiguration

---

### Feature Not Loading

* Wrong `entryUrl`
* CORS issue
* Missing `mount()` export

---

### React Error: createRoot()

* Feature mounted twice
* Cleanup not implemented

---

### ERR_INSUFFICIENT_RESOURCES

* Infinite re-render loop
* Repeated fetch calls

---

## Design Principles

* **Feature isolation**
* **Runtime-driven behavior**
* **Centralized auth**
* **Loose coupling via contracts**
* **Environment-aware configuration**

---

## Next Steps

Planned improvements:

* Feature compatibility enforcement (`shellContractMin/max`)
* Strict runtime validation (schema validation)
* CI/CD integration with registry publishing
* Terraform-based infrastructure automation
* Developer onboarding automation (scaffold + docs)

---

## Summary

This platform provides a **scalable, enterprise-grade foundation** for:

* Microfrontend architectures
* Event-driven systems
* Secure, centralized authentication
* Independent feature delivery

It is designed to allow teams to **build, deploy, and evolve features independently** while maintaining a consistent runtime experience.
