# Registry contract

## Purpose

The **platform registry** stores **resolved** feature manifests for shell and bootstrap consumption. It does **not** treat the raw source file `contracts/feature-manifest.json` as the only runtime input: CI and local scripts produce a **resolved** manifest, then a **registry payload** for publish.

In a generated feature repo the flow is:

1. **`contracts/feature-manifest.json`** — emitted by the scaffold from `build_feature_manifest()` (`src/feature_scaffold/manifest_builder.py` in this tool).
2. **`scripts/render-manifest.py`** — reads the source manifest, applies environment overrides, and writes **`build/feature-manifest.resolved.json`**.
3. **`scripts/render-registry-payload.py`** — wraps that resolved document into **`build/registry-payload.json`** for the HTTP publish API.

## Resolution step (`render-manifest.py`)

The resolver (generated template) typically:

- Sets **`environment`** (default `dev`, or `FEATURE_ENVIRONMENT`).
- Copies **`basePath`** into **`route`**.
- Builds **`nav`** from **`navigation`**.
- Derives **`authorization`** from **`auth.roles`** (`requiredPermissions`, `requiredFlags`).
- Resolves **`frontend.entryUrl`** (`FEATURE_FRONTEND_ENTRY_URL` or manifest default).
- Resolves **`backend.baseUrl`** / **`backend.apiBaseUrl`** / **`backend.healthEndpoint`** (`FEATURE_BACKEND_BASE_URL` or manifest values).

Use the **resolved** file for validation and publishing, not only the source manifest.

## Publish endpoints

The **`render-registry-payload.py`** output (`build/registry-payload.json`) is what you send to your registry’s HTTP API. **Exact routes are platform-specific.**

The generated **`scripts/run-local.sh`** (when `PUBLISH_LOCAL_ENABLED` is `true`) currently:

1. **`POST {REGISTRY_BASE_URL}/api/releases`** with the registry payload JSON as the body.
2. **`POST {REGISTRY_BASE_URL}/api/admin/features/{featureKey}/versions/{version}/activate?environment=local`** to activate the new release for local.

Set `REGISTRY_BASE_URL` (default `http://localhost:8010`) to match a running registry, or set `PUBLISH_LOCAL_ENABLED=false` to skip publish during local dev.

The generated feature backend includes **`RegistryClient.publish_feature`**, which posts to **`POST {base_url}/api/features/publish`** with the same payload shape—use that path or change the client to match your registry.

CI / other environments may use different paths; keep **`run-local.sh`**, backend clients, and the registry API in sync.

## Request body shape

The scaffolded **`render-registry-payload.py`** builds JSON of the form:

```json
{
  "featureKey": "<kebab-case feature key>",
  "version": "<semver from manifest>",
  "environment": "dev|test|prod",
  "manifest": { }
}
```

- **`featureKey`** / **`version`** — identify the feature release (duplicated at the top for convenience; also inside **`manifest`**).
- **`environment`** — taken from the resolved manifest’s **`environment`** field, defaulting to **`"dev"`** if missing.
- **`manifest`** — the **full resolved feature manifest** (the same object as **`build/feature-manifest.resolved.json`**). It includes **`auth`** (e.g. `shellAuthRequired`, `tokenForwarding`, `tokenStrategy`, `allowedDevModes`, `roles`), **`frontend`**, **`backend`**, **`registry`**, **`events`**, **`workers`**, optional **`authorization`**, etc. There is **no separate top-level `auth` field** on the payload.

## Related files

| Path | Role |
|------|------|
| `contracts/feature-manifest.json` | Source manifest in the feature repo (generated). |
| `build/feature-manifest.resolved.json` | Environment-resolved manifest (`render-manifest.py`). |
| `build/registry-payload.json` | Registry publish body from `render-registry-payload.py` (e.g. `POST …/api/releases` in `run-local.sh`). |
| `manifest.schema.json` | JSON Schema for the resolved manifest shape (generated; used by `validate-manifest.py`). |

Template reference for wording: `src/feature_scaffold/templates/contracts/registry-contract.md.j2`.
