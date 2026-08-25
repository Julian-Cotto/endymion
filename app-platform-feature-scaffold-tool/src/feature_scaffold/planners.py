from __future__ import annotations

from typing import Any

from .models import NormalizedScaffoldConfig, PlannedFile


def _database_platform_files(config: NormalizedScaffoldConfig) -> list[PlannedFile]:
    if not config.database_enabled:
        return []

    files: list[PlannedFile] = [
        PlannedFile("backend/app/platform/database/__init__.py", literal_content=""),
        PlannedFile("backend/app/platform/database/config.py", "backend/app/platform/database/config.py.j2"),
    ]

    if config.postgres_enabled:
        files.extend([
            PlannedFile("backend/app/platform/database/base.py", "backend/app/platform/database/base.py.j2"),
            PlannedFile("backend/app/platform/database/session.py", "backend/app/platform/database/session.py.j2"),
        ])

    if config.snowflake_enabled:
        files.append(
            PlannedFile("backend/app/platform/database/snowflake.py", "backend/app/platform/database/snowflake.py.j2")
        )

    if config.postgres_enabled and config.postgres_migrations_enabled:
        files.extend([
            PlannedFile("backend/alembic.ini", "backend/alembic.ini.j2"),
            PlannedFile("backend/alembic/env.py", "backend/alembic/env.py.j2"),
            PlannedFile("backend/alembic/script.py.mako", "backend/alembic/script.py.mako.j2"),
            PlannedFile("backend/alembic/versions/.gitkeep", literal_content=""),
            PlannedFile("backend/app/models/__init__.py", "backend/app/models/__init__.py.j2"),
            PlannedFile("backend/app/models/example.py", "backend/app/models/example.py.j2"),
        ])

    if config.postgres_enabled and config.postgres_migrations_enabled and config.include_docs:
        files.append(
            PlannedFile(
                "docs/database-migrations.md",
                "docs/database-migrations.md.j2",
            )
        )

    return files


def _blob_storage_platform_files(config: NormalizedScaffoldConfig) -> list[PlannedFile]:
    if not config.blob_storage_enabled:
        return []

    return [
        PlannedFile("backend/app/platform/storage/__init__.py", literal_content=""),
        PlannedFile("backend/app/platform/storage/config.py", "backend/app/platform/storage/config.py.j2"),
        PlannedFile("backend/app/platform/storage/blob_client.py", "backend/app/platform/storage/blob_client.py.j2"),
        PlannedFile("backend/app/platform/storage/blob_service.py", "backend/app/platform/storage/blob_service.py.j2"),
    ]


def _api_capability_wiring_files(config: NormalizedScaffoldConfig) -> list[PlannedFile]:
    files: list[PlannedFile] = []

    if not config.backend_enabled:
        return files

    if config.database_enabled and "api" in config.database_targets:
        files.append(
            PlannedFile(
                "backend/app/platform/database/dependencies.py",
                "backend/app/platform/database/dependencies.py.j2",
            )
        )

    if config.blob_storage_enabled and "api" in config.blob_storage_targets:
        files.append(
            PlannedFile(
                "backend/app/platform/storage/dependencies.py",
                "backend/app/platform/storage/dependencies.py.j2",
            )
        )

    if (
        (config.database_enabled and "api" in config.database_targets)
        or (config.blob_storage_enabled and "api" in config.blob_storage_targets)
    ):
        files.append(
            PlannedFile(
                "backend/app/api/platform_capabilities.py",
                "backend/app/api/platform_capabilities.py.j2",
            )
        )

    return files


def _runtime_capability_wiring_files(config: NormalizedScaffoldConfig) -> list[PlannedFile]:
    files: list[PlannedFile] = []

    needs_database_runtime = (
        config.database_enabled
        and any(target in config.database_targets for target in ("jobs", "listeners"))
    )
    needs_storage_runtime = (
        config.blob_storage_enabled
        and any(target in config.blob_storage_targets for target in ("jobs", "listeners"))
    )

    if not (needs_database_runtime or needs_storage_runtime):
        return files

    files.append(
        PlannedFile("backend/app/runtime/__init__.py", literal_content="")
    )

    if needs_database_runtime:
        files.append(
            PlannedFile(
                "backend/app/runtime/database.py",
                "backend/app/runtime/database.py.j2",
            )
        )

    if needs_storage_runtime:
        files.append(
            PlannedFile(
                "backend/app/runtime/storage.py",
                "backend/app/runtime/storage.py.j2",
            )
        )

    return files


def _cache_platform_files(config: NormalizedScaffoldConfig) -> list[PlannedFile]:
    if not config.cache_enabled:
        return []

    files: list[PlannedFile] = [
        PlannedFile("backend/app/platform/cache/__init__.py", literal_content=""),
        PlannedFile("backend/app/platform/cache/config.py", "backend/app/platform/cache/config.py.j2"),
        PlannedFile("backend/app/platform/cache/memory_cache.py", "backend/app/platform/cache/memory_cache.py.j2"),
        PlannedFile("backend/app/platform/cache/cache_factory.py", "backend/app/platform/cache/cache_factory.py.j2"),
    ]

    if config.redis_enabled:
        files.append(
            PlannedFile("backend/app/platform/cache/redis_cache.py", "backend/app/platform/cache/redis_cache.py.j2")
        )

    return files


def _api_cache_wiring_files(config: NormalizedScaffoldConfig) -> list[PlannedFile]:
    files: list[PlannedFile] = []

    if not config.backend_enabled:
        return files

    if config.cache_enabled and "api" in config.cache_targets:
        files.extend([
            PlannedFile(
                "backend/app/platform/cache/dependencies.py",
                "backend/app/platform/cache/dependencies.py.j2",
            ),
            PlannedFile(
                "backend/app/api/cache_capabilities.py",
                "backend/app/api/cache_capabilities.py.j2",
            ),
        ])

    return files


def _runtime_cache_wiring_files(config: NormalizedScaffoldConfig) -> list[PlannedFile]:
    if not config.cache_enabled:
        return []

    if not any(target in config.cache_targets for target in ("jobs", "listeners")):
        return []

    return [
        PlannedFile("backend/app/runtime/cache.py", "backend/app/runtime/cache.py.j2"),
    ]


def build_file_plan(config: NormalizedScaffoldConfig) -> list[PlannedFile]:
    plan: list[PlannedFile] = [
        PlannedFile("README.md", "common/README.md.j2"),
        PlannedFile(".gitignore", "common/gitignore.j2"),
        PlannedFile(".editorconfig", "common/editorconfig.j2"),
        PlannedFile(".env.example", "common/env.example.j2"),
        PlannedFile("scaffold.metadata.json", "common/scaffold.metadata.json.j2"),
        PlannedFile("contracts/api-contract.md", "contracts/api-contract.md.j2"),
        PlannedFile("contracts/events-contract.md", "contracts/events-contract.md.j2"),
        PlannedFile("contracts/feature-manifest.json"),
        PlannedFile("contracts/registry-contract.md", "contracts/registry-contract.md.j2"),
        PlannedFile("contracts/bootstrap-runtime-example.json", "contracts/bootstrap-runtime-example.json.j2"),
        PlannedFile("contracts/bootstrap-response.local.json", "contracts/bootstrap-response.local.json.j2"),
        PlannedFile("manifest.schema.json", literal_content=None, template_path="common/manifest.schema.json.j2"),
        PlannedFile("contracts/bootstrap-response-example.json", "contracts/bootstrap-response-example.json.j2"),
    ]

    if config.include_docs:
        plan.extend([
            PlannedFile("docs/onboarding.md", "docs/onboarding.md.j2"),
            PlannedFile("docs/feature-development-guide.md", "docs/feature-development-guide.md.j2"),
            PlannedFile("docs/runbook.md", "docs/runbook.md.j2"),
            PlannedFile("docs/architecture.md", "docs/architecture.md.j2"),
            PlannedFile("docs/authentication.md", "docs/authentication.md.j2"),
        ])

    if config.frontend_enabled:
        plan.extend([
            PlannedFile("frontend/.env.example", "frontend/env.example.j2"),
            PlannedFile("frontend/package.json", "frontend/package.json.j2"),
            PlannedFile("frontend/tsconfig.json", "frontend/tsconfig.json.j2"),
            PlannedFile("frontend/vite.config.ts", "frontend/vite.config.ts.j2"),
            PlannedFile("frontend/index.html", "frontend/index.html.j2"),
            PlannedFile("frontend/src/main.tsx", "frontend/src/main.tsx.j2"),
            PlannedFile("frontend/src/bootstrap-entry.tsx", "frontend/src/bootstrap-entry.tsx.j2"),
            PlannedFile("frontend/src/bootstrap.ts", "frontend/src/bootstrap.ts.j2"),
            PlannedFile("frontend/src/mount.tsx", "frontend/src/mount.tsx.j2"),
            PlannedFile("frontend/src/App.tsx", "frontend/src/App.tsx.j2", policy="create_if_missing"),
            PlannedFile("frontend/src/routes.tsx", "frontend/src/routes.tsx.j2"),
            PlannedFile("frontend/src/app/FeatureApp.tsx", "frontend/src/app/FeatureApp.tsx.j2"),
            PlannedFile("frontend/src/platform/shellContext.ts", "frontend/src/platform/shellContext.ts.j2"),
            PlannedFile("frontend/src/platform/authProvider.tsx", "frontend/src/platform/authProvider.tsx.j2"),
            PlannedFile("frontend/src/platform/authAdapter.ts", "frontend/src/platform/authAdapter.ts.j2"),
            PlannedFile("frontend/src/platform/registryClient.ts", "frontend/src/platform/registryClient.ts.j2"),
            PlannedFile("frontend/src/platform/featureConfig.ts", "frontend/src/platform/featureConfig.ts.j2"),
            PlannedFile("frontend/src/platform/authTypes.ts", "frontend/src/platform/authTypes.ts.j2"),
            PlannedFile(
                "frontend/src/components/FeatureHomePage.tsx",
                "frontend/src/components/FeatureHomePage.tsx.j2",
                policy="create_if_missing",
            ),
            PlannedFile(
                "frontend/src/components/BackendHealthCard.tsx",
                "frontend/src/components/BackendHealthCard.tsx.j2",
                policy="create_if_missing",
            ),
            PlannedFile("frontend/src/services/apiClient.ts", "frontend/src/services/apiClient.ts.j2"),
            PlannedFile("frontend/src/services/featureApi.ts", "frontend/src/services/featureApi.ts.j2"),
            PlannedFile("frontend/src/tests/setup.ts", "frontend/src/tests/setup.ts.j2"),
        ])
        if config.include_tests:
            plan.append(PlannedFile("frontend/src/tests/App.test.tsx", "frontend/src/tests/App.test.tsx.j2"))

    if config.backend_enabled:
        plan.extend([
            PlannedFile("backend/app/__init__.py", literal_content=""),
            PlannedFile("backend/app/api/__init__.py", literal_content=""),
            PlannedFile("backend/app/platform/__init__.py", literal_content=""),
            PlannedFile("backend/app/services/__init__.py", literal_content=""),
            PlannedFile("backend/app/domain/__init__.py", literal_content=""),
            PlannedFile("backend/app/schemas/__init__.py", literal_content=""),
            PlannedFile("backend/app/events/__init__.py", literal_content=""),
            PlannedFile("backend/app/infrastructure/__init__.py", literal_content=""),
            PlannedFile("backend/pyproject.toml", "backend/pyproject.toml.j2"),
            PlannedFile("backend/pytest.ini", "backend/pytest.ini.j2"),
            PlannedFile("backend/app/main.py", "backend/app/main.py.j2"),
            PlannedFile("backend/app/config.py", "backend/app/config.py.j2"),
            PlannedFile("backend/app/dependencies.py", "backend/app/dependencies.py.j2"),
            PlannedFile("backend/app/api/health.py", "backend/app/api/health.py.j2"),
            PlannedFile("backend/app/api/feature.py", "backend/app/api/feature.py.j2", policy="create_if_missing"),
            PlannedFile("backend/app/platform/auth_context.py", "backend/app/platform/auth_context.py.j2"),
            PlannedFile("backend/app/platform/permissions.py", "backend/app/platform/permissions.py.j2"),
            PlannedFile("backend/app/platform/config_client.py", "backend/app/platform/config_client.py.j2"),
            PlannedFile("backend/app/platform/response_models.py", "backend/app/platform/response_models.py.j2"),
            PlannedFile("backend/app/platform/registry_models.py", "backend/app/platform/registry_models.py.j2"),
            PlannedFile("backend/app/platform/registry_client.py", "backend/app/platform/registry_client.py.j2"),
            PlannedFile(
                "backend/app/services/feature_service.py",
                "backend/app/services/feature_service.py.j2",
                policy="create_if_missing",
            ),
            PlannedFile("backend/app/domain/models.py", "backend/app/domain/models.py.j2"),
            PlannedFile("backend/app/schemas/health.py", "backend/app/schemas/health.py.j2"),
            PlannedFile("backend/app/schemas/feature.py", "backend/app/schemas/feature.py.j2"),
            PlannedFile("backend/app/events/publisher.py", "backend/app/events/publisher.py.j2"),
            PlannedFile("backend/app/events/models.py", "backend/app/events/models.py.j2"),
            PlannedFile("backend/app/infrastructure/logging.py", "backend/app/infrastructure/logging.py.j2"),
            PlannedFile("backend/.env.production.example", "backend/.env.production.example.j2"),
        ])

        plan.extend(_database_platform_files(config))
        plan.extend(_api_capability_wiring_files(config))
        plan.extend(_blob_storage_platform_files(config))
        plan.extend(_runtime_capability_wiring_files(config))
        plan.extend(_cache_platform_files(config))
        plan.extend(_api_cache_wiring_files(config))
        plan.extend(_runtime_cache_wiring_files(config))

        plan.append(
            PlannedFile(
                "backend/requirements.txt",
                "backend/requirements.txt.j2",
            )
        )

        plan.append(
            PlannedFile(
                "backend/.env.example",
                "backend/.env.example.j2",
            )
        )

        if config.include_tests:
            plan.extend([
                PlannedFile("backend/tests/test_health.py", "backend/tests/test_health.py.j2"),
                PlannedFile("backend/tests/test_feature.py", "backend/tests/test_feature.py.j2"),
                PlannedFile("backend/tests/test_auth_context.py", "backend/tests/test_auth_context.py.j2"),
            ])

    if config.scheduled_jobs:
        plan.append(PlannedFile("jobs/__init__.py", literal_content=""))
    for job in config.scheduled_jobs:
        safe_name = job.name.replace("-", "_")
        base = f"jobs/{safe_name}"
        job_ctx = {"target_name": job.name, "target_safe_name": safe_name, "target_schedule": job.schedule}
        plan.extend([
            PlannedFile(f"{base}/__init__.py", literal_content=""),
            PlannedFile(f"{base}/main.py", "jobs/main.py.j2", template_context=job_ctx),
            PlannedFile(f"{base}/config.py", "jobs/config.py.j2", template_context=job_ctx),
            PlannedFile(f"{base}/runner.py", "jobs/runner.py.j2", template_context=job_ctx, policy="create_if_missing"),
        ])
        if config.include_tests:
            plan.append(PlannedFile(f"{base}/test_runner.py", "jobs/test_runner.py.j2", template_context=job_ctx))

    if config.event_driven_jobs:
        plan.append(PlannedFile("workers/__init__.py", literal_content=""))
    for worker in config.event_driven_jobs:
        safe_name = worker.name.replace("-", "_")
        base = f"workers/{safe_name}"
        worker_ctx: dict[str, Any] = {
            "target_name": worker.name,
            "target_safe_name": safe_name,
            "trigger_kind": worker.trigger.kind,
            "trigger_topic": worker.trigger.topic,
            "trigger_subscription": worker.trigger.subscription,
            "trigger_queue": worker.trigger.queue,
            "target_event_name": worker.payload_schema or worker.name,
            "dead_letter": worker.dead_letter,
            "max_concurrency": worker.max_concurrency,
            "max_retries": worker.retry_policy.max_retries,
            "retry_backoff": worker.retry_policy.backoff,
        }
        plan.extend([
            PlannedFile(f"{base}/__init__.py", literal_content=""),
            PlannedFile(f"{base}/main.py", "workers/main.py.j2", template_context=worker_ctx),
            PlannedFile(f"{base}/config.py", "workers/config.py.j2", template_context=worker_ctx),
            PlannedFile(f"{base}/handler.py", "workers/handler.py.j2", template_context=worker_ctx, policy="create_if_missing"),
            PlannedFile(f"{base}/contract.py", "workers/contract.py.j2", template_context=worker_ctx),
        ])
        if config.include_tests:
            plan.append(PlannedFile(f"{base}/test_handler.py", "workers/test_handler.py.j2", template_context=worker_ctx))

    if config.event_listeners:
        plan.append(PlannedFile("listeners/__init__.py", literal_content=""))
    for listener in config.event_listeners:
        safe_name = listener.name.replace("-", "_")
        base = f"listeners/{safe_name}"
        listener_ctx = {
            "target_name": listener.name,
            "target_safe_name": safe_name,
            "target_event_name": listener.event_name,
            "payload_schema": listener.payload_schema,
        }
        plan.extend([
            PlannedFile(f"{base}/__init__.py", literal_content=""),
            PlannedFile(f"{base}/main.py", "listeners/main.py.j2", template_context=listener_ctx),
            PlannedFile(f"{base}/config.py", "listeners/config.py.j2", template_context=listener_ctx),
            PlannedFile(f"{base}/handler.py", "listeners/handler.py.j2", template_context=listener_ctx, policy="create_if_missing"),
            PlannedFile(f"{base}/contract.py", "listeners/contract.py.j2", template_context=listener_ctx),
        ])
        if config.include_tests:
            plan.append(PlannedFile(f"{base}/test_handler.py", "listeners/test_handler.py.j2", template_context=listener_ctx))

    for event in config.published_events + config.consumed_events:
        plan.append(
            PlannedFile(
                f"contracts/events/{event.name}.json",
                "contracts/event-schema.json.j2",
                template_context={"event_name": event.name, "event_schema_name": event.schema},
            )
        )

    if config.include_terraform:
        plan.extend([
            PlannedFile("infra/terraform/versions.tf", "infra/versions.tf.j2"),
            PlannedFile("infra/terraform/providers.tf", "infra/providers.tf.j2"),
            PlannedFile("infra/terraform/variables.tf", "infra/variables.tf.j2"),
            PlannedFile("infra/terraform/main.tf", "infra/main.tf.j2"),
            PlannedFile("infra/terraform/outputs.tf", "infra/outputs.tf.j2"),
            PlannedFile("infra/terraform/dev.tfvars.example", "infra/dev.tfvars.example.j2"),
            PlannedFile("infra/terraform/test.tfvars.example", "infra/test.tfvars.example.j2"),
            PlannedFile("infra/terraform/prod.tfvars.example", "infra/prod.tfvars.example.j2"),
            PlannedFile("infra/terraform/README.md", "infra/README.md.j2"),
        ])

    if config.include_github_actions:
        plan.extend([
            PlannedFile(".github/workflows/ci.yml", "github/ci.yml.j2"),
            PlannedFile(".github/workflows/deploy.dev.yml", "github/deploy.dev.yml.j2"),
            PlannedFile(".github/workflows/deploy.test.yml", "github/deploy.test.yml.j2"),
            PlannedFile(".github/workflows/deploy.prod.yml", "github/deploy.prod.yml.j2"),
        ])

    if config.include_scripts:
        plan.extend([
            PlannedFile("scripts/bootstrap.sh", "scripts/bootstrap.sh.j2"),
            PlannedFile("scripts/bootstrap.ps1", "scripts/bootstrap.ps1.j2"),
            PlannedFile("scripts/validate.sh", "scripts/validate.sh.j2"),
            PlannedFile("scripts/validate.ps1", "scripts/validate.ps1.j2"),
            PlannedFile("scripts/run-local.sh", "scripts/run-local.sh.j2"),
            PlannedFile("scripts/run-local.ps1", "scripts/run-local.ps1.j2"),
            PlannedFile("scripts/render-manifest.py", "scripts/render-manifest.py.j2"),
            PlannedFile("scripts/validate-manifest.py", "scripts/validate-manifest.py.j2"),
            PlannedFile("scripts/render-registry-payload.py", "scripts/render-registry-payload.py.j2"),
            PlannedFile("scripts/serve-bootstrap-mock.py", "scripts/serve-bootstrap-mock.py.j2"),
            PlannedFile("scripts/publish-local.sh", "scripts/publish-local.sh.j2"),
            PlannedFile("scripts/publish-local.ps1", "scripts/publish-local.ps1.j2"),
        ])

    if config.include_docs and config.database_enabled:
        plan.append(
            PlannedFile(
                "docs/database-capability.md",
                "docs/database-capability.md.j2",
            )
        )

    if config.include_docs and config.blob_storage_enabled:
        plan.append(
            PlannedFile(
                "docs/blob-storage-capability.md",
                "docs/blob-storage-capability.md.j2",
            )
        )

    if config.include_scripts and config.postgres_enabled and config.postgres_migrations_enabled:
        plan.extend([
            PlannedFile("scripts/run-migrations.sh", "scripts/run-migrations.sh.j2"),
            PlannedFile("scripts/run-migrations.ps1", "scripts/run-migrations.ps1.j2"),
        ])

    if config.include_docs and config.registry_enabled:
        plan.append(
            PlannedFile(
                "docs/registry-integration.md",
                "docs/registry-integration.md.j2",
            )
        )

    if config.include_docs and config.cache_enabled:
        plan.append(
            PlannedFile(
                "docs/cache-capability.md",
                "docs/cache-capability.md.j2",
            )
        )

    if config.include_docs:
        plan.append(
            PlannedFile(
                "docs/bootstrap-runtime-contract.md",
                "docs/bootstrap-runtime-contract.md.j2",
            )
        )

    if config.include_docs:
        plan.append(
            PlannedFile(
                "docs/bootstrap-response-contract.md",
                "docs/bootstrap-response-contract.md.j2",
            )
        )

    return plan