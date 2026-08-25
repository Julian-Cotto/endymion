from pathlib import Path


def test_shell_contract_file_contains_v1_markers() -> None:
    content = Path(
        "src/feature_scaffold/templates/frontend/src/platform/authTypes.ts.j2"
    ).read_text(encoding="utf-8")

    assert 'version: "v1"' in content
    assert "isAuthenticated: boolean" in content
    assert "authMode: AuthMode" in content
    assert "export interface ShellFeatureAuthContractV1" in content


def test_shell_runtime_context_template_contains_v1_markers() -> None:
    content = Path(
        "src/feature_scaffold/templates/frontend/src/platform/shellContext.ts.j2"
    ).read_text(encoding="utf-8")

    assert 'version: "v1"' in content
    assert "export interface ShellFeatureRuntimeContractV1" in content
    assert "featureKey: string" in content
    assert "__FEATURE_SHELL_RUNTIME__" in content
    assert "__FEATURE_MOUNT_CONTEXT__" in content


def test_contract_doc_exists_and_mentions_v1_rules() -> None:
    content = Path("docs/runtime-auth-contract-v1.md").read_text(encoding="utf-8")

    assert "Runtime and Auth Contract v1" in content
    assert "Allowed in v1" in content
    assert "Not allowed in v1" in content
    assert "Breaking changes" in content
    assert 'version: "v1"' in content
    assert "__FEATURE_SHELL_AUTH__" in content
    assert "__FEATURE_SHELL_RUNTIME__" in content


def test_contract_doc_mentions_mount_context_shape() -> None:
    content = Path("docs/runtime-auth-contract-v1.md").read_text(encoding="utf-8")

    assert "mount(container, {" in content
    assert "manifest," in content
    assert "session," in content
    assert "runtime," in content


def test_contract_doc_mentions_runtime_resolution_precedence() -> None:
    content = Path("docs/runtime-auth-contract-v1.md").read_text(encoding="utf-8")

    assert "Runtime resolution precedence" in content
    assert "mountContext.runtime.backend.baseUrl" in content
    assert "VITE_API_BASE_URL" in content