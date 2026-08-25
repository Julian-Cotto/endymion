# Shell local runtime modes

How the shell loads feature definitions in local development.

---

## Entry point

`FeatureHost` calls:

```ts
await loadRuntimeFeatures({
  bootstrapUrl, // from App: getBootstrapUrl()
  signal,       // AbortSignal from FeatureHost effect
});
```

`loadRuntimeFeatures` (`src/platform/runtime/loadRuntimeFeatures.ts`) branches on **`getRuntimeSourceMode()`**:

| `VITE_RUNTIME_SOURCE_MODE` | Behavior |
|----------------------------|----------|
| **`registry`** | `loadRegistryRuntimeResponse(url, { signal })` then **`normalizeRegistryRuntimeResponse`** → **`BootstrapResponse`**. URL = `options.registryRuntimeUrl ?? getRegistryRuntimeUrl()`. |
| **`bootstrap`** (default) | `loadBootstrapResponse(url, { signal })` → **`BootstrapResponse`**. URL = `options.bootstrapUrl ?? getBootstrapUrl()`. |

Defaults in **`src/platform/runtime/runtimeClientConfig.ts`**:

- **`getBootstrapUrl()`** → `VITE_BOOTSTRAP_URL` or **`http://localhost:8001/api/runtime/features`**
- **`getRegistryRuntimeUrl()`** → `VITE_REGISTRY_RUNTIME_URL` or **`http://localhost:8010/api/runtime/features?environment=local`**

---

## Example `.env.local` snippets

**Bootstrap mode (default URLs):**

```env
VITE_RUNTIME_SOURCE_MODE=bootstrap
# Optional override:
# VITE_BOOTSTRAP_URL=http://localhost:8001/api/runtime/features
```

**Registry mode:**

```env
VITE_RUNTIME_SOURCE_MODE=registry
VITE_REGISTRY_RUNTIME_URL=http://localhost:8001/api/runtime/features
```

In registry mode the **registry** URL is fetched; **`VITE_BOOTSTRAP_URL`** / **`getBootstrapUrl()`** is not used for that GET (the **`bootstrapUrl`** prop on **`FeatureHost`** is only passed into **`loadRuntimeFeatures`** as `options.bootstrapUrl`, which is ignored when mode is **`registry`**).

Adjust hosts/ports to match your local API.

---

## After load: mount

1. Runtime payload is **`BootstrapResponse`** (registry path is normalized to that shape).
2. `FeatureHost` finds **`features`** by **`featureKey`**, builds **`FeatureManifest`**, calls **`bootstrapFeature`** with **`runtime`** (v1 contract: flags, permissions, backend, etc.).
3. Feature module: **`mount(container, { manifest, session, runtime })`**. A **function** return value is used as **cleanup** when the host aborts or unmounts.

---

## Typical local ports (reference)

| Service | Port (example) |
|---------|----------------:|
| Shell (Vite) | 3000 |
| Runtime / bootstrap API | 8001 |
| Registry (when on 8010) | 8010 |
| Orders feature dev server | 3200 |
| Catalog feature dev server | 3300 |

---

## Verification

1. Orders feature entry (example): `http://localhost:3200/...` (whatever your `entryUrl` is).
2. Catalog: same pattern on port 3300.
3. Open shell: `http://localhost:3000/orders` or `/catalog`.
4. Network tab: runtime GET should match **`VITE_RUNTIME_SOURCE_MODE`** and show **`Authorization`** when **`VITE_MOCK_ACCESS_TOKEN`** or Entra token populates the session snapshot.

---

## Why this matters

Same downstream contract (**bootstrap-shaped JSON** → **manifest** → **mount**) whether the list comes from a **bootstrap** URL or a **registry** runtime URL that is **normalized** in the shell.
