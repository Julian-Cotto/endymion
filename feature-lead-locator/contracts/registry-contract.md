# Registry contract

## Payload shape

`scripts/render-registry-payload.py` produces **`build/registry-payload.json`**:

```json
{
  "featureKey": "lead-locator",
  "version": "0.1.0",
  "environment": "dev|test|prod",
  "manifest": {}
}
```

The full resolved manifest lives under **`manifest`** (including **`auth`**). There is **no** duplicate top-level **`auth`** field.

## HTTP routes (align with your registry)

Routes are **platform-specific**. In this scaffold:

- **`scripts/run-local.sh`** (when publishing is enabled) uses **`POST {REGISTRY_BASE_URL}/api/releases`** with the payload body, then **`POST …/api/admin/features/{featureKey}/versions/{version}/activate?environment=local`**.
- The generated backend **`RegistryClient.publish_feature`** uses **`POST {base_url}/api/features/publish`** with the same JSON shape.

Use one style consistently, or adapt the scripts/client to match your registry implementation.