# Shell consumption contract

## Purpose

The **application shell** consumes **resolved** registry records (and the manifest embedded in the registry payload), not the unchecked `contracts/feature-manifest.json` file alone. Runtime URL assembly, environment selection, and mount wiring are driven by the **published** manifest shape.

The shell should not:

- re-derive production URLs from scratch without the manifest
- treat the on-disk source manifest as the only runtime truth before resolution
- invent mount function names or entry URLs that contradict the manifest

The shell should:

- fetch the latest **resolved** manifest for an environment (via registry / platform API)
- load the frontend entry using **`frontend.entryUrl`** and **`frontend.entryStrategy`**
- call **`frontend.mountFunction`** with the platform shell context
- honor **`auth`** as provided: `required`, `mode`, `shellAuthRequired`, `tokenForwarding`, `tokenStrategy`, `allowedDevModes`, `roles`

After **`render-manifest.py`**, also consider **`authorization`** (derived permissions from roles), **`environment`**, **`route`**, and **`nav`** when present on the resolved document.

## Source vs resolved manifest

| Stage | File | Notes |
|-------|------|--------|
| Source | `contracts/feature-manifest.json` | Produced by `build_feature_manifest()`; includes `featureKey`, `frontend`, `backend`, `auth`, `registry`, `events`, `workers`. |
| Resolved | `build/feature-manifest.resolved.json` | Adds/overrides URLs, `environment`, `route`, `nav`, `authorization`, normalized backend paths. Use this for runtime. |

## Fields (shell-relevant)

The generator builds the source manifest in `manifest_builder.py`. Typical top-level fields:

| Field | Meaning |
|-------|---------|
| `featureKey` | Stable kebab-case identifier. |
| `displayName` | Human label. |
| `description` | Optional description. |
| `basePath` | Browser route prefix (leading `/`). |
| `version` | Semver string for this scaffold/manifest. |
| `navigation` | UI label/icon hints (`label`, `icon`). |
| `frontend.enabled` | Whether the microfrontend is active. |
| `frontend.entryStrategy` | e.g. `vite-dynamic-import`. |
| `frontend.entryUrl` | Asset URL for dynamic import (e.g. `/features/<key>/assets/bootstrap.js`); may be overridden when resolved. |
| `frontend.mountFunction` | Named export to invoke (e.g. `mount`). |
| `backend.enabled` | Whether the feature API is active. |
| `backend.baseUrl` | API path prefix after resolution (e.g. `/api/orders`). |
| `backend.apiBaseUrl` | Often mirrored with `baseUrl` on the resolved manifest. |
| `backend.healthEndpoint` | Health check path. |
| `auth.required` | Derived: `auth.mode != "none"`. |
| `auth.mode` | `entra`, `mock`, or `none`. |
| `auth.shellAuthRequired` | Shell must supply auth context. |
| `auth.tokenForwarding` | Frontend should forward tokens to the backend as configured. |
| `auth.tokenStrategy` | Backend token handling label (see generated `manifest.schema.json` enum; aligns with feature JSON `backend_token_strategy` after normalization). |
| `auth.allowedDevModes` | Allowed auth modes in development. |
| `auth.roles` | Platform role names for the feature. |
| `registry.enabled` / `registry.mode` | Registry integration flags. |
| `events.publishes` / `events.consumes` | Event name arrays (dotted names). |
| `workers.scheduledJobs` | Job **names** (strings). |
| `workers.eventDrivenJobs` | Worker **names** (strings). |
| `workers.eventListeners` | Listener **names** (strings). |

## Validation

- Validate resolved manifests with **`scripts/validate-manifest.py`** (runs **`jsonschema`** against **`manifest.schema.json`** at the feature repo root, plus explicit checks on **`auth`**).
- The canonical schema file is generated as **`manifest.schema.json`** in the feature repo; the tool also ships logic under `src/feature_scaffold/manifest_validator.py` for this package.

## Runtime loading model

Example:

```ts
const module = await import(feature.frontend.entryUrl);
module[feature.frontend.mountFunction](container, shellContext);
```

Always use the **resolved** manifest in real environments so `entryUrl`, `baseUrl`, and `environment` match deployment.
