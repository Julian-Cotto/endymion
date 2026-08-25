from pathlib import Path

from feature_scaffold.cli import _load_config
from feature_scaffold.generator import ScaffoldGenerator


def _generate_feature(tmp_path: Path, example_name: str) -> Path:
    templates_dir = Path("src/feature_scaffold/templates")
    config = _load_config(Path(f"examples/{example_name}"))
    return ScaffoldGenerator(templates_dir=templates_dir).generate(config, tmp_path)


def test_generated_auth_types_are_v1(tmp_path: Path) -> None:
    repo_dir = _generate_feature(tmp_path, "orders-feature.json")
    content = (
        repo_dir / "frontend" / "src" / "platform" / "authTypes.ts"
    ).read_text(encoding="utf-8")

    assert 'version: "v1"' in content
    assert "export interface ShellFeatureAuthContractV1" in content
    assert "isAuthenticated: boolean" in content
    assert "authMode: AuthMode" in content


def test_generated_shell_context_is_v1(tmp_path: Path) -> None:
    repo_dir = _generate_feature(tmp_path, "orders-feature.json")
    content = (
        repo_dir / "frontend" / "src" / "platform" / "shellContext.ts"
    ).read_text(encoding="utf-8")

    assert 'version: "v1"' in content
    assert "export interface ShellFeatureRuntimeContractV1" in content
    assert "featureKey: string" in content
    assert "__FEATURE_SHELL_RUNTIME__" in content
    assert "__FEATURE_MOUNT_CONTEXT__" in content


def test_generated_mount_chain_uses_runtime_context_v1(tmp_path: Path) -> None:
    repo_dir = _generate_feature(tmp_path, "orders-feature.json")

    bootstrap_entry = (
        repo_dir / "frontend" / "src" / "bootstrap-entry.tsx"
    ).read_text(encoding="utf-8")
    bootstrap_ts = (
        repo_dir / "frontend" / "src" / "bootstrap.ts"
    ).read_text(encoding="utf-8")
    mount_tsx = (
        repo_dir / "frontend" / "src" / "mount.tsx"
    ).read_text(encoding="utf-8")

    assert 'export { mount } from "./bootstrap";' in bootstrap_entry
    assert 'import { mountFeature } from "./mount";' in bootstrap_ts
    assert "context?: ShellMountContext" in bootstrap_ts
    assert "setFeatureMountContext" in mount_tsx
    assert "setShellRuntimeContext" in mount_tsx
    assert 'import { FeatureAuthProvider } from "./platform/authProvider";' in mount_tsx


def test_generated_api_client_uses_runtime_precedence(tmp_path: Path) -> None:
    repo_dir = _generate_feature(tmp_path, "orders-feature.json")
    content = (
        repo_dir / "frontend" / "src" / "services" / "apiClient.ts"
    ).read_text(encoding="utf-8")

    assert "mountContext?.runtime?.backend?.baseUrl" in content
    assert "getShellRuntimeContext" in content
    assert "mountContext?.manifest?.backend?.baseUrl" in content
    assert "VITE_API_BASE_URL" in content
    assert "LOCAL_DEFAULT_API_BASE_URL" in content