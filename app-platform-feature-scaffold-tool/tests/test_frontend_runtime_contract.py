from __future__ import annotations

import json
from pathlib import Path

from feature_scaffold.cli import _load_config
from feature_scaffold.generator import ScaffoldGenerator


def _generate_feature(tmp_path: Path, example_name: str) -> Path:
    templates_dir = Path("src/feature_scaffold/templates")
    config = _load_config(Path(f"examples/{example_name}"))
    return ScaffoldGenerator(templates_dir=templates_dir).generate(config, tmp_path)


def test_generated_orders_frontend_runtime_contract(tmp_path: Path) -> None:
    repo_dir = _generate_feature(tmp_path, "orders-feature.json")
    frontend_src = repo_dir / "frontend" / "src"

    assert (frontend_src / "platform" / "authTypes.ts").exists()
    assert (frontend_src / "platform" / "shellContext.ts").exists()
    assert (frontend_src / "platform" / "authAdapter.ts").exists()
    assert (frontend_src / "services" / "apiClient.ts").exists()
    assert (frontend_src / "mount.tsx").exists()
    assert (frontend_src / "bootstrap.ts").exists()
    assert (frontend_src / "bootstrap-entry.tsx").exists()

    bootstrap_entry = (frontend_src / "bootstrap-entry.tsx").read_text(encoding="utf-8")
    assert 'export { mount } from "./bootstrap";' in bootstrap_entry

    bootstrap_ts = (frontend_src / "bootstrap.ts").read_text(encoding="utf-8")
    assert 'import { mountFeature } from "./mount";' in bootstrap_ts
    assert "export function mount(" in bootstrap_ts

    mount_tsx = (frontend_src / "mount.tsx").read_text(encoding="utf-8")
    assert 'import { FeatureAuthProvider } from "./platform/authProvider";' in mount_tsx
    assert "setFeatureMountContext" in mount_tsx
    assert "setShellRuntimeContext" in mount_tsx
    assert "FeatureAuthProvider" in mount_tsx

    auth_types = (frontend_src / "platform" / "authTypes.ts").read_text(encoding="utf-8")
    assert "export interface FeatureAuthContext" in auth_types
    assert "export interface ShellFeatureAuthContractV1" in auth_types
    assert "__FEATURE_SHELL_AUTH__" in auth_types

    auth_adapter = (frontend_src / "platform" / "authAdapter.ts").read_text(encoding="utf-8")
    assert "resolveFeatureAuthContext" in auth_adapter
    assert "isAuthenticated" in auth_adapter
    assert "authMode" in auth_adapter

    api_client = (frontend_src / "services" / "apiClient.ts").read_text(encoding="utf-8")
    assert "export async function apiFetch" in api_client
    assert "export async function apiGet" in api_client
    assert "resolveFeatureAuthContext" in api_client
    assert "getShellRuntimeContext" in api_client


def test_generated_catalog_frontend_runtime_contract(tmp_path: Path) -> None:
    repo_dir = _generate_feature(tmp_path, "catalog-feature.json")
    frontend_src = repo_dir / "frontend" / "src"

    assert (frontend_src / "platform" / "authTypes.ts").exists()
    assert (frontend_src / "bootstrap-entry.tsx").exists()
    assert (frontend_src / "mount.tsx").exists()
    assert (frontend_src / "bootstrap.ts").exists()

    bootstrap_entry = (frontend_src / "bootstrap-entry.tsx").read_text(encoding="utf-8")
    assert 'export { mount } from "./bootstrap";' in bootstrap_entry

    mount_tsx = (frontend_src / "mount.tsx").read_text(encoding="utf-8")
    assert 'import { FeatureAuthProvider } from "./platform/authProvider";' in mount_tsx
    assert "ReactDOM.createRoot" in mount_tsx or "__featureRoot__" in mount_tsx

    app_tsx = (frontend_src / "App.tsx").read_text(encoding="utf-8")
    assert "const json = await apiFetch" in app_tsx
    assert "response.json()" not in app_tsx


def test_generated_local_bootstrap_contract_uses_tsx_and_correct_ports(tmp_path: Path) -> None:
    orders_repo = _generate_feature(tmp_path, "orders-feature.json")
    catalog_repo = _generate_feature(tmp_path, "catalog-feature.json")

    orders_bootstrap = json.loads(
        (orders_repo / "contracts" / "bootstrap-response.local.json").read_text(encoding="utf-8")
    )
    catalog_bootstrap = json.loads(
        (catalog_repo / "contracts" / "bootstrap-response.local.json").read_text(encoding="utf-8")
    )

    orders_feature = orders_bootstrap["features"][0]
    catalog_feature = catalog_bootstrap["features"][0]

    assert orders_bootstrap["flags"] == {}
    assert catalog_bootstrap["flags"] == {}

    assert orders_feature["frontend"]["entryUrl"] == "http://localhost:3200/src/bootstrap-entry.tsx"
    assert catalog_feature["frontend"]["entryUrl"] == "http://localhost:3300/src/bootstrap-entry.tsx"

    assert orders_feature["backend"]["apiBaseUrl"] == "http://localhost:8100/api/orders"
    assert catalog_feature["backend"]["apiBaseUrl"] == "http://localhost:8200/api/catalog"


def test_generated_run_local_ports_do_not_collide_between_orders_and_catalog(tmp_path: Path) -> None:
    orders_repo = _generate_feature(tmp_path, "orders-feature.json")
    catalog_repo = _generate_feature(tmp_path, "catalog-feature.json")

    orders_script = (orders_repo / "scripts" / "run-local.sh").read_text(encoding="utf-8")
    catalog_script = (catalog_repo / "scripts" / "run-local.sh").read_text(encoding="utf-8")

    assert 'BACKEND_PORT="${BACKEND_PORT:-8100}"' in orders_script
    assert 'BOOTSTRAP_PORT="${BOOTSTRAP_PORT:-3050}"' in orders_script
    assert 'FRONTEND_PORT="${FRONTEND_PORT:-3200}"' in orders_script

    assert 'BACKEND_PORT="${BACKEND_PORT:-8200}"' in catalog_script
    assert 'BOOTSTRAP_PORT="${BOOTSTRAP_PORT:-3060}"' in catalog_script
    assert 'FRONTEND_PORT="${FRONTEND_PORT:-3300}"' in catalog_script