# Runtime and auth contract v1

Defines the **shell-produced** v1 contracts for mounted feature frontends. **Source of truth for TypeScript shapes:** `src/platform/contracts/shellFeatureAuth.ts` (and `bootstrapFeature.ts` for the mount call).

---

## Browser globals

The shell sets:

- `window.__FEATURE_SHELL_AUTH__` — when **`resolveShellFeatureAuth`** returns a contract and **`injectFeatureShellAuth`** runs (version stripped before inject; **`injectFeatureShellAuth`** assigns **`version: "v1"`**).
- `window.__FEATURE_SHELL_RUNTIME__` — via **`injectFeatureShellRuntime`** with the v1 runtime object (flags, permissions, backend, etc.).

There is **no** `window.__FEATURE_MOUNT_CONTEXT__` in the current implementation; features should use the **`mount(..., context)`** argument.

---

## Shell auth contract (`ShellFeatureAuthContractV1`)

```ts
export interface ShellFeatureAuthContractV1 {
  version: "v1";
  isAuthenticated: boolean;
  authMode: "none" | "mock" | "entra";
  userId?: string;
  userName?: string;
  email?: string;
  roles?: string[];
  accessToken?: string;
}
```

Required at runtime on **`window`**: **`version`**, **`isAuthenticated`**, **`authMode`**.

Resolution logic: **`src/platform/auth/resolveShellFeatureAuth.ts`** (driven by **`FeatureManifest`** **`auth`** and **`ShellUserSession`**).

---

## Shell runtime contract (`ShellFeatureRuntimeContractV1`)

```ts
export interface ShellFeatureBackendContractV1 {
  baseUrl?: string;
  healthEndpoint?: string;
  enabled?: boolean;
}

export interface ShellFeatureRuntimeContractV1 {
  version: "v1";
  environment?: string;
  featureKey: string;
  route?: string;
  displayName?: string;
  backend?: ShellFeatureBackendContractV1;
  flags?: Record<string, boolean>;
  permissions?: string[];
}
```

Required: **`version`**, **`featureKey`**.

---

## Mount contract

The shell invokes:

```ts
mount(container, {
  manifest: FeatureManifest;
  session: ShellUserSession;
  runtime: ShellFeatureRuntimeContractV1;
});
```

- **`manifest`** — Built in **`FeatureHost`** from the selected **`BootstrapFeature`**.
- **`session`** — Current **`ShellUserSession`** from **`ShellAuthProvider`** (mock or Entra-derived in **`App.tsx`**).
- **`runtime`** — v1 runtime slice including **`flags`** and **`permissions`** from the bootstrap response.

The return value is **`unknown`**; **`FeatureHost`** treats a **function** as cleanup and invokes it when loads are aborted or the component unmounts.

---

## Compatibility (v1)

**Allowed:** optional fields; consumers ignore unknown fields.

**Breaking:** requires a new version (e.g. v2) — no renames or semantic changes to required fields under **`version: "v1"`**.
