# Runtime and Auth Contract v1

## Purpose

This document defines the current v1 runtime and auth contract between the shell application and generated feature frontends.

It exists to prevent accidental contract drift between:

- the shell application
- generated feature frontends
- scaffold templates
- future registry-driven runtime integration

---

## Scope

This document covers:

- shell auth contract
- shell runtime contract
- mount context contract
- compatibility and versioning rules for v1

---

## Global browser keys

The shell injects:

- window.__FEATURE_SHELL_AUTH__
- window.__FEATURE_SHELL_RUNTIME__
- window.__FEATURE_MOUNT_CONTEXT__

---

## Shell auth contract

    export type AuthMode = "none" | "mock" | "entra";

    export interface ShellFeatureAuthContractV1 {
      version: "v1";
      isAuthenticated: boolean;
      authMode: AuthMode;
      userId?: string;
      userName?: string;
      email?: string;
      roles?: string[];
      accessToken?: string;
    }

### Required fields

- version
- isAuthenticated
- authMode

### Optional fields

- userId
- userName
- email
- roles
- accessToken

---

## Shell runtime contract

    export interface ShellFeatureRuntimeBackendContractV1 {
      baseUrl?: string;
      enabled?: boolean;
      healthEndpoint?: string;
    }

    export interface ShellFeatureRuntimeContractV1 {
      version: "v1";
      environment?: string;
      featureKey: string;
      route?: string;
      displayName?: string;
      backend?: ShellFeatureRuntimeBackendContractV1;
      flags?: Record<string, boolean>;
      permissions?: string[];
    }

### Required fields

- version
- featureKey

---

## Mount context contract

    export interface ShellMountContextV1 {
      manifest?: any;
      session?: any;
      runtime?: ShellFeatureRuntimeContractV1;
    }

### Mount usage

    mount(container, {
      manifest,
      session,
      runtime,
    });

---

## Runtime resolution precedence

Backend API base URL is resolved in this order:

1. mountContext.runtime.backend.baseUrl
2. window.__FEATURE_SHELL_RUNTIME__.backend.baseUrl
3. mountContext.manifest.backend.baseUrl
4. VITE_API_BASE_URL
5. fallback default

---

## Auth resolution precedence

Auth is resolved in this order:

1. window.__FEATURE_SHELL_AUTH__
2. mountContext.session
3. frontend fallback mode

---

## Compatibility rules for v1

### Allowed in v1

- adding optional fields
- adding unknown fields
- ignoring unknown fields

### Not allowed in v1

- renaming fields
- removing fields
- changing semantics
- changing version

---

## Breaking changes

Breaking changes require a new version (v2).

Examples:

- renaming authMode
- removing isAuthenticated
- changing backend structure
- changing mount shape

---

## Generated scaffold expectations

Generated features include:

- authTypes.ts
- shellContext.ts
- authAdapter.ts
- apiClient.ts
- bootstrap-entry.tsx
- bootstrap.ts
- mount.tsx

---

## Local development ports

### Orders

- backend: 8100
- frontend: 3200

### Catalog

- backend: 8200
- frontend: 3300

---

## Why this exists

This contract prevents failures caused by:

- missing auth types
- broken import paths
- ts vs tsx mismatches
- runtime drift between shell and features

---

## Current status

v1 is now locked and enforced by:

- scaffold templates
- generator tests
- runtime contract tests

---
