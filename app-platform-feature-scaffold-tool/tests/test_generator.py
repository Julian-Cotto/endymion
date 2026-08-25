import json
from pathlib import Path

from feature_scaffold.generator import ScaffoldGenerator
from feature_scaffold.models import (
    BackendConfig,
    BlobStorageCapabilityConfig,
    CacheCapabilityConfig,
    CacheProvidersConfig, 
    CapabilitiesConfig, 
    DatabaseCapabilityConfig, 
    DatabaseProvidersConfig, 
    EventDrivenJobConfig, 
    EventListenerConfig, 
    EventTriggerConfig, 
    PostgresCapabilityConfig, 
    RegistryConfig, 
    ScaffoldConfig, 
    ScheduledJobConfig,
    MemoryCacheCapabilityConfig,
    RedisCacheCapabilityConfig,
)

def test_generator_creates_repo(tmp_path: Path) -> None:
    templates_dir = Path(__file__).parent.parent / "src" / "feature_scaffold" / "templates"
    repo_dir = ScaffoldGenerator(templates_dir=templates_dir).generate(
        ScaffoldConfig(feature_name="orders", display_name="Orders", base_path="/orders"),
        tmp_path,
    )
    assert (repo_dir / "README.md").exists()
    assert (repo_dir / "contracts" / "feature-manifest.json").exists()
    manifest = json.loads((repo_dir / "contracts" / "feature-manifest.json").read_text(encoding="utf-8"))
    assert manifest["featureKey"] == "orders"
    
def test_generate_api_capability_wiring_files(tmp_path: Path) -> None:
    templates_dir = Path("src/feature_scaffold/templates")


    config = ScaffoldConfig(
        feature_name="orders",
        display_name="Orders",
        base_path="/orders",
        capabilities=CapabilitiesConfig(
            database=DatabaseCapabilityConfig(
                enabled=True,
                targets=["api"],
                providers=DatabaseProvidersConfig(
                    postgresql=PostgresCapabilityConfig(
                        enabled=True,
                        orm=True,
                        migrations=True,
                    )
                ),
            ),
            blob_storage=BlobStorageCapabilityConfig(
                enabled=True,
                provider="azure_blob",
                targets=["api"],
            ),
        ),
    )

    repo_dir = ScaffoldGenerator(templates_dir=templates_dir).generate(config, tmp_path)

    assert (repo_dir / "backend/app/platform/database/dependencies.py").exists()
    assert (repo_dir / "backend/app/platform/storage/dependencies.py").exists()
    assert (repo_dir / "backend/app/api/platform_capabilities.py").exists()  

def test_backend_requirements_generated(tmp_path: Path) -> None:
    templates_dir = Path("src/feature_scaffold/templates")

    repo_dir = ScaffoldGenerator(templates_dir=templates_dir).generate(
        ScaffoldConfig(
            feature_name="orders",
            display_name="Orders",
            base_path="/orders",
        ),
        tmp_path,
    )

    assert (repo_dir / "backend/requirements.txt").exists()


def test_requirements_include_capabilities(tmp_path: Path) -> None:
    templates_dir = Path("src/feature_scaffold/templates")

    config = ScaffoldConfig(
        feature_name="orders",
        display_name="Orders",
        base_path="/orders",
        capabilities=CapabilitiesConfig(
            database=DatabaseCapabilityConfig(
                enabled=True,
                targets=["api"],
                providers=DatabaseProvidersConfig(
                    postgresql=PostgresCapabilityConfig(
                        enabled=True,
                        orm=True,
                        migrations=True,
                    )
                ),
            ),
            blob_storage=BlobStorageCapabilityConfig(
                enabled=True,
                provider="azure_blob",
                targets=["api"],
            ),
        ),
    )

    repo_dir = ScaffoldGenerator(templates_dir=templates_dir).generate(config, tmp_path)

    content = (repo_dir / "backend/requirements.txt").read_text()

    assert "sqlalchemy" in content
    assert "psycopg2-binary" in content
    assert "azure-storage-blob" in content

def test_generate_alembic_files_when_postgres_migrations_enabled(tmp_path: Path) -> None:
    templates_dir = Path("src/feature_scaffold/templates")

    config = ScaffoldConfig(
        feature_name="orders",
        display_name="Orders",
        base_path="/orders",
        capabilities=CapabilitiesConfig(
            database=DatabaseCapabilityConfig(
                enabled=True,
                targets=["api"],
                providers=DatabaseProvidersConfig(
                    postgresql=PostgresCapabilityConfig(
                        enabled=True,
                        orm=True,
                        migrations=True,
                    )
                ),
            ),
        ),
    )

    repo_dir = ScaffoldGenerator(templates_dir=templates_dir).generate(config, tmp_path)

    assert (repo_dir / "backend/alembic.ini").exists()
    assert (repo_dir / "backend/alembic/env.py").exists()
    assert (repo_dir / "backend/alembic/script.py.mako").exists()
    assert (repo_dir / "backend/alembic/versions/.gitkeep").exists()
    assert (repo_dir / "backend/app/models/example.py").exists()

def test_requirements_include_alembic_when_postgres_migrations_enabled(tmp_path: Path) -> None:
    templates_dir = Path("src/feature_scaffold/templates")

    config = ScaffoldConfig(
        feature_name="orders",
        display_name="Orders",
        base_path="/orders",
        capabilities=CapabilitiesConfig(
            database=DatabaseCapabilityConfig(
                enabled=True,
                targets=["api"],
                providers=DatabaseProvidersConfig(
                    postgresql=PostgresCapabilityConfig(
                        enabled=True,
                        orm=True,
                        migrations=True,
                    )
                ),
            ),
        ),
    )

    repo_dir = ScaffoldGenerator(templates_dir=templates_dir).generate(config, tmp_path)
    content = (repo_dir / "backend/requirements.txt").read_text(encoding="utf-8")

    assert "alembic" in content

def test_generate_runtime_capability_helpers_for_jobs_and_listeners(tmp_path: Path) -> None:
    templates_dir = Path("src/feature_scaffold/templates")

    config = ScaffoldConfig(
        feature_name="orders",
        display_name="Orders",
        base_path="/orders",
        capabilities=CapabilitiesConfig(
            database=DatabaseCapabilityConfig(
                enabled=True,
                targets=["jobs", "listeners"],
                providers=DatabaseProvidersConfig(
                    postgresql=PostgresCapabilityConfig(
                        enabled=True,
                        orm=True,
                        migrations=True,
                    )
                ),
            ),
            blob_storage=BlobStorageCapabilityConfig(
                enabled=True,
                provider="azure_blob",
                targets=["jobs", "listeners"],
            ),
        ),
    )

    repo_dir = ScaffoldGenerator(templates_dir=templates_dir).generate(config, tmp_path)

    assert (repo_dir / "backend/app/runtime/__init__.py").exists()
    assert (repo_dir / "backend/app/runtime/database.py").exists()
    assert (repo_dir / "backend/app/runtime/storage.py").exists()

def test_generate_job_worker_listener_files_with_runtime_capabilities(tmp_path: Path) -> None:
    templates_dir = Path("src/feature_scaffold/templates")

    config = ScaffoldConfig(
        feature_name="orders",
        display_name="Orders",
        base_path="/orders",
        scheduled_jobs=[
            ScheduledJobConfig(name="nightly-sync", schedule="0 1 * * *"),
        ],
        event_driven_jobs=[
            EventDrivenJobConfig(
                name="process-order",
                trigger=EventTriggerConfig(kind="queue", queue="orders"),
            ),
        ],
        event_listeners=[
            EventListenerConfig(
                name="inventory-updated",
                event_name="inventory.updated",
            ),
        ],
        capabilities=CapabilitiesConfig(
            database=DatabaseCapabilityConfig(
                enabled=True,
                targets=["jobs", "listeners"],
                providers=DatabaseProvidersConfig(
                    postgresql=PostgresCapabilityConfig(
                        enabled=True,
                        orm=True,
                        migrations=True,
                    )
                ),
            ),
            blob_storage=BlobStorageCapabilityConfig(
                enabled=True,
                provider="azure_blob",
                targets=["jobs", "listeners"],
            ),
        ),
    )

    repo_dir = ScaffoldGenerator(templates_dir=templates_dir).generate(config, tmp_path)

    assert (repo_dir / "jobs/nightly_sync/runner.py").exists()
    assert (repo_dir / "workers/process_order/handler.py").exists()
    assert (repo_dir / "listeners/inventory_updated/handler.py").exists()

    assert (repo_dir / "backend/app/runtime/database.py").exists()
    assert (repo_dir / "backend/app/runtime/storage.py").exists()

def test_generate_registry_integration_files(tmp_path: Path) -> None:
    templates_dir = Path("src/feature_scaffold/templates")

    config = ScaffoldConfig(
        feature_name="orders",
        display_name="Orders",
        base_path="/orders",
        registry=RegistryConfig(enabled=True, mode="rest"),
    )

    repo_dir = ScaffoldGenerator(templates_dir=templates_dir).generate(config, tmp_path)

    assert (repo_dir / "docs/registry-integration.md").exists()
    assert (repo_dir / "contracts/registry-contract.md").exists()
    assert (repo_dir / "backend/app/platform/registry_models.py").exists()
    assert (repo_dir / "backend/app/platform/registry_client.py").exists()

def test_backend_requirements_include_httpx(tmp_path: Path) -> None:
    templates_dir = Path("src/feature_scaffold/templates")

    repo_dir = ScaffoldGenerator(templates_dir=templates_dir).generate(
        ScaffoldConfig(
            feature_name="orders",
            display_name="Orders",
            base_path="/orders",
        ),
        tmp_path,
    )

    content = (repo_dir / "backend/requirements.txt").read_text(encoding="utf-8")
    assert "httpx" in content

def test_generate_cache_files_when_cache_enabled(tmp_path: Path) -> None:
    templates_dir = Path("src/feature_scaffold/templates")

    config = ScaffoldConfig(
        feature_name="orders",
        display_name="Orders",
        base_path="/orders",
        capabilities=CapabilitiesConfig(
            cache=CacheCapabilityConfig(
                enabled=True,
                targets=["api", "jobs", "listeners"],
                providers=CacheProvidersConfig(
                    memory=MemoryCacheCapabilityConfig(enabled=True),
                    redis=RedisCacheCapabilityConfig(enabled=True),
                ),
            )
        ),
    )

    repo_dir = ScaffoldGenerator(templates_dir=templates_dir).generate(config, tmp_path)

    assert (repo_dir / "backend/app/platform/cache/config.py").exists()
    assert (repo_dir / "backend/app/platform/cache/memory_cache.py").exists()
    assert (repo_dir / "backend/app/platform/cache/cache_factory.py").exists()
    assert (repo_dir / "backend/app/platform/cache/redis_cache.py").exists()
    assert (repo_dir / "backend/app/platform/cache/dependencies.py").exists()
    assert (repo_dir / "backend/app/runtime/cache.py").exists()
    assert (repo_dir / "backend/app/api/cache_capabilities.py").exists()

def test_generate_cache_docs_when_cache_enabled(tmp_path: Path) -> None:
    templates_dir = Path("src/feature_scaffold/templates")

    config = ScaffoldConfig(
        feature_name="orders",
        display_name="Orders",
        base_path="/orders",
        capabilities=CapabilitiesConfig(
            cache=CacheCapabilityConfig(
                enabled=True,
                targets=["api", "jobs", "listeners"],
                providers=CacheProvidersConfig(
                    memory=MemoryCacheCapabilityConfig(enabled=True),
                    redis=RedisCacheCapabilityConfig(enabled=True),
                ),
            )
        ),
    )

    repo_dir = ScaffoldGenerator(templates_dir=templates_dir).generate(config, tmp_path)

    assert (repo_dir / "docs/cache-capability.md").exists()

def test_backend_requirements_include_redis_when_enabled(tmp_path: Path) -> None:
    templates_dir = Path("src/feature_scaffold/templates")

    config = ScaffoldConfig(
        feature_name="orders",
        display_name="Orders",
        base_path="/orders",
        capabilities=CapabilitiesConfig(
            cache=CacheCapabilityConfig(
                enabled=True,
                targets=["api"],
                providers=CacheProvidersConfig(
                    memory=MemoryCacheCapabilityConfig(enabled=True),
                    redis=RedisCacheCapabilityConfig(enabled=True),
                ),
            )
        ),
    )

    repo_dir = ScaffoldGenerator(templates_dir=templates_dir).generate(config, tmp_path)
    content = (repo_dir / "backend/requirements.txt").read_text(encoding="utf-8")

    assert "redis" in content

def test_generate_backend_env_example_includes_cache_settings(tmp_path: Path) -> None:
    templates_dir = Path("src/feature_scaffold/templates")

    config = ScaffoldConfig(
        feature_name="orders",
        display_name="Orders",
        base_path="/orders",
        capabilities=CapabilitiesConfig(
            cache=CacheCapabilityConfig(
                enabled=True,
                targets=["api"],
                providers=CacheProvidersConfig(
                    memory=MemoryCacheCapabilityConfig(enabled=True),
                    redis=RedisCacheCapabilityConfig(enabled=True),
                ),
            )
        ),
    )

    repo_dir = ScaffoldGenerator(templates_dir=templates_dir).generate(config, tmp_path)
    content = (repo_dir / "backend/.env.example").read_text(encoding="utf-8")

    assert "CACHE_BACKEND=redis" in content
    assert "REDIS_URL=redis://localhost:6379/0" in content


def test_backend_pyproject_includes_redis_when_enabled(tmp_path: Path) -> None:
    templates_dir = Path("src/feature_scaffold/templates")

    config = ScaffoldConfig(
        feature_name="orders",
        display_name="Orders",
        base_path="/orders",
        capabilities=CapabilitiesConfig(
            cache=CacheCapabilityConfig(
                enabled=True,
                targets=["api"],
                providers=CacheProvidersConfig(
                    memory=MemoryCacheCapabilityConfig(enabled=True),
                    redis=RedisCacheCapabilityConfig(enabled=True),
                ),
            )
        ),
    )

    repo_dir = ScaffoldGenerator(templates_dir=templates_dir).generate(config, tmp_path)
    content = (repo_dir / "backend/pyproject.toml").read_text(encoding="utf-8")

    assert "redis" in content

def test_generate_bootstrap_response_contract_files(tmp_path: Path) -> None:
    templates_dir = Path("src/feature_scaffold/templates")

    config = ScaffoldConfig(
        feature_name="orders",
        display_name="Orders",
        base_path="/orders",
        registry=RegistryConfig(enabled=True, mode="push"),
    )

    repo_dir = ScaffoldGenerator(templates_dir=templates_dir).generate(config, tmp_path)

    assert (repo_dir / "docs/bootstrap-response-contract.md").exists()
    assert (repo_dir / "contracts/bootstrap-response-example.json").exists()


def test_bootstrap_response_example_contains_expected_envelope(tmp_path: Path) -> None:
    templates_dir = Path("src/feature_scaffold/templates")

    repo_dir = ScaffoldGenerator(templates_dir=templates_dir).generate(
        ScaffoldConfig(
            feature_name="orders",
            display_name="Orders",
            base_path="/orders",
            backend=BackendConfig(api_base_path="/api/orders"),
        ),
        tmp_path,
    )

    content = json.loads(
        (repo_dir / "contracts" / "bootstrap-response-example.json").read_text(encoding="utf-8")
    )

    assert content["environment"] == "dev"
    assert "user" in content
    assert "permissions" in content
    assert "flags" in content
    assert "features" in content
    assert "metadata" in content

    feature = content["features"][0]
    assert feature["featureKey"] == "orders"
    assert feature["route"] == "/orders"
    assert feature["backend"]["apiBaseUrl"] == "/api/orders"
    assert "authorization" in feature


def test_generate_local_bootstrap_mock(tmp_path: Path) -> None:
    templates_dir = Path("src/feature_scaffold/templates")

    repo_dir = ScaffoldGenerator(templates_dir=templates_dir).generate(
        ScaffoldConfig(
            feature_name="orders",
            display_name="Orders",
            base_path="/orders",
        ),
        tmp_path,
    )

    assert (repo_dir / "contracts/bootstrap-response.local.json").exists()
    assert (repo_dir / "scripts/serve-bootstrap-mock.py").exists()

def test_generate_mount_file_as_tsx(tmp_path: Path) -> None:
    templates_dir = Path("src/feature_scaffold/templates")

    repo_dir = ScaffoldGenerator(templates_dir=templates_dir).generate(
        ScaffoldConfig(
            feature_name="orders",
            display_name="Orders",
            base_path="/orders",
        ),
        tmp_path,
    )

    assert (repo_dir / "frontend" / "src" / "mount.tsx").exists()
    assert not (repo_dir / "frontend" / "src" / "mount.ts").exists()


def test_generated_readme_includes_local_stack_workflow(tmp_path: Path) -> None:
    templates_dir = Path("src/feature_scaffold/templates")

    repo_dir = ScaffoldGenerator(templates_dir=templates_dir).generate(
        ScaffoldConfig(
            feature_name="orders",
            display_name="Orders",
            base_path="/orders",
        ),
        tmp_path,
    )

    content = (repo_dir / "README.md").read_text(encoding="utf-8")

    assert "## Local development" in content
    assert "./scripts/bootstrap.sh" in content
    assert "./scripts/run-local.sh" in content
    assert "http://localhost:3050/bootstrap" in content
    assert "Shell runs separately" in content or "does not start the shell automatically" in content


def test_generated_run_local_sh_includes_bootstrap_mock_and_readiness(tmp_path: Path) -> None:
    templates_dir = Path("src/feature_scaffold/templates")

    repo_dir = ScaffoldGenerator(templates_dir=templates_dir).generate(
        ScaffoldConfig(
            feature_name="orders",
            display_name="Orders",
            base_path="/orders",
        ),
        tmp_path,
    )

    content = (repo_dir / "scripts" / "run-local.sh").read_text(encoding="utf-8")

    assert "serve-bootstrap-mock.py" in content
    assert "BOOTSTRAP_PORT" in content
    assert "BOOTSTRAP_HEALTH_PATH" in content
    assert "wait_for_http" in content
    assert "http://localhost:${BOOTSTRAP_PORT}${BOOTSTRAP_HEALTH_PATH}" in content
    assert "npm run dev -- --host 0.0.0.0 --port" in content


def test_generated_run_local_ps1_includes_bootstrap_mock_and_readiness(tmp_path: Path) -> None:
    templates_dir = Path("src/feature_scaffold/templates")

    repo_dir = ScaffoldGenerator(templates_dir=templates_dir).generate(
        ScaffoldConfig(
            feature_name="orders",
            display_name="Orders",
            base_path="/orders",
        ),
        tmp_path,
    )

    content = (repo_dir / "scripts" / "run-local.ps1").read_text(encoding="utf-8")

    assert "serve-bootstrap-mock.py" in content
    assert "BootstrapPort" in content
    assert "BootstrapHealthPath" in content
    assert "Wait-Url" in content
    assert 'http://localhost:$BootstrapPort$BootstrapHealthPath' in content
    assert '--host", "0.0.0.0"' in content
    assert '--port", $FrontendPort' in content


def test_generated_bootstrap_scripts_point_to_run_local(tmp_path: Path) -> None:
    templates_dir = Path("src/feature_scaffold/templates")

    repo_dir = ScaffoldGenerator(templates_dir=templates_dir).generate(
        ScaffoldConfig(
            feature_name="orders",
            display_name="Orders",
            base_path="/orders",
        ),
        tmp_path,
    )

    sh_content = (repo_dir / "scripts" / "bootstrap.sh").read_text(encoding="utf-8")
    ps1_content = (repo_dir / "scripts" / "bootstrap.ps1").read_text(encoding="utf-8")

    assert "./scripts/run-local.sh" in sh_content
    assert r".\scripts\run-local.ps1" in ps1_content


import os


def test_generated_shell_scripts_are_executable(tmp_path: Path) -> None:
    templates_dir = Path("src/feature_scaffold/templates")

    repo_dir = ScaffoldGenerator(templates_dir=templates_dir).generate(
        ScaffoldConfig(
            feature_name="orders",
            display_name="Orders",
            base_path="/orders",
        ),
        tmp_path,
    )

    bootstrap_sh = repo_dir / "scripts" / "bootstrap.sh"
    run_local_sh = repo_dir / "scripts" / "run-local.sh"
    validate_sh = repo_dir / "scripts" / "validate.sh"

    assert os.access(bootstrap_sh, os.X_OK)
    assert os.access(run_local_sh, os.X_OK)
    assert os.access(validate_sh, os.X_OK)


def test_generated_frontend_bootstrap_files_exist(tmp_path: Path) -> None:
    templates_dir = Path("src/feature_scaffold/templates")

    repo_dir = ScaffoldGenerator(templates_dir=templates_dir).generate(
        ScaffoldConfig(
            feature_name="orders",
            display_name="Orders",
            base_path="/orders",
        ),
        tmp_path,
    )

    bootstrap_path = repo_dir / "frontend" / "src" / "bootstrap.ts"
    bootstrap_entry_path = repo_dir / "frontend" / "src" / "bootstrap-entry.tsx"
    mount_path = repo_dir / "frontend" / "src" / "mount.tsx"

    assert bootstrap_path.exists()
    assert bootstrap_entry_path.exists()
    assert mount_path.exists()

    bootstrap_entry_content = bootstrap_entry_path.read_text(encoding="utf-8")
    assert 'export { mount } from "./bootstrap";' in bootstrap_entry_content


def test_generated_local_bootstrap_response_uses_bootstrap_entry(tmp_path: Path) -> None:
    templates_dir = Path("src/feature_scaffold/templates")

    repo_dir = ScaffoldGenerator(templates_dir=templates_dir).generate(
        ScaffoldConfig(
            feature_name="orders",
            display_name="Orders",
            base_path="/orders",
        ),
        tmp_path,
    )

    content = (
        repo_dir / "contracts" / "bootstrap-response.local.json"
    ).read_text(encoding="utf-8")

    payload = json.loads(content)
    feature = payload["features"][0]

    assert feature["frontend"]["entryUrl"] == "http://localhost:3200/src/bootstrap-entry.tsx"
    assert feature["backend"]["apiBaseUrl"] == "http://localhost:8100/api"
    assert payload["flags"] == {}


def test_generated_frontend_vite_config_supports_shell_local_dev(tmp_path: Path) -> None:
    templates_dir = Path("src/feature_scaffold/templates")

    repo_dir = ScaffoldGenerator(templates_dir=templates_dir).generate(
        ScaffoldConfig(
            feature_name="orders",
            display_name="Orders",
            base_path="/orders",
        ),
        tmp_path,
    )

    content = (repo_dir / "frontend" / "vite.config.ts").read_text(encoding="utf-8")

    assert 'entry: "src/bootstrap-entry.tsx"' in content
    assert '"http://localhost:3000"' in content
    assert '"http://localhost:3200"' in content
    assert '"http://localhost:3300"' in content
    assert "const isMicrofrontendBuild = mode === \"mf\";" in content


def test_generated_api_client_exports_api_get(tmp_path: Path) -> None:
    templates_dir = Path("src/feature_scaffold/templates")

    repo_dir = ScaffoldGenerator(templates_dir=templates_dir).generate(
        ScaffoldConfig(
            feature_name="orders",
            display_name="Orders",
            base_path="/orders",
        ),
        tmp_path,
    )

    content = (
        repo_dir / "frontend" / "src" / "services" / "apiClient.ts"
    ).read_text(encoding="utf-8")

    assert "export async function apiFetch<" in content
    assert "export async function apiGet<" in content
    assert "export async function apiPost<" in content
    assert "export async function apiPut<" in content
    assert "export async function apiPatch<" in content
    assert "export async function apiDelete<" in content
    assert "return apiFetch<T>(path, {" in content


def test_generated_auth_provider_exports_auth_provider(tmp_path: Path) -> None:
    templates_dir = Path("src/feature_scaffold/templates")

    repo_dir = ScaffoldGenerator(templates_dir=templates_dir).generate(
        ScaffoldConfig(
            feature_name="orders",
            display_name="Orders",
            base_path="/orders",
        ),
        tmp_path,
    )

    content = (
        repo_dir / "frontend" / "src" / "platform" / "authProvider.tsx"
    ).read_text(encoding="utf-8")

    assert "AuthProvider" in content
    assert "export" in content