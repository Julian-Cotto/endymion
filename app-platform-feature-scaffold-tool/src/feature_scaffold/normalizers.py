from __future__ import annotations

import re

from .models import NormalizedNames, NormalizedScaffoldConfig, ScaffoldConfig


def _to_kebab(value: str) -> str:
    value = re.sub(r"[_\s]+", "-", value.strip())
    value = re.sub(r"[^a-zA-Z0-9-]+", "-", value)
    value = re.sub(r"-{2,}", "-", value)
    return value.strip("-").lower()


def _to_snake(value: str) -> str:
    value = re.sub(r"[-\s]+", "_", value.strip())
    value = re.sub(r"[^a-zA-Z0-9_]+", "_", value)
    value = re.sub(r"_{2,}", "_", value)
    return value.strip("_").lower()


def _normalize_base_path(value: str) -> str:
    value = value.strip()
    if not value.startswith("/"):
        value = "/" + value
    value = re.sub(r"/{2,}", "/", value)
    if len(value) > 1 and value.endswith("/"):
        value = value[:-1]
    return value


def normalize_config(config: ScaffoldConfig) -> NormalizedScaffoldConfig:
    feature_key = _to_kebab(config.feature_name)
    snake = _to_snake(config.feature_name)
    title = config.display_name.strip() or feature_key.replace("-", " ").title()
    version = config.version
    caps = config.capabilities

    database_enabled = caps.database.enabled
    database_targets = caps.database.targets

    postgres_enabled = caps.database.providers.postgresql.enabled
    postgres_orm_enabled = caps.database.providers.postgresql.orm
    postgres_migrations_enabled = caps.database.providers.postgresql.migrations

    snowflake_enabled = caps.database.providers.snowflake.enabled

    blob_storage_enabled = caps.blob_storage.enabled
    blob_storage_provider = caps.blob_storage.provider
    blob_storage_targets = caps.blob_storage.targets

    cache_enabled = caps.cache.enabled
    cache_targets = caps.cache.targets
    memory_cache_enabled = caps.cache.providers.memory.enabled
    redis_enabled = caps.cache.providers.redis.enabled

    deployment = config.deployment
    dx = config.developer_experience
    auth = config.auth
    backend = config.backend
    frontend = config.frontend
    registry = config.registry
    events = config.events

    names = NormalizedNames(
        feature_key=feature_key,
        repo_name=f"feature-{feature_key}",
        display_name=title,
        title_case_name=title,
        description=config.description.strip(),
        base_path=_normalize_base_path(config.base_path),
        api_base_path=_normalize_base_path(backend.api_base_path),
        python_package_name=f"{snake}_service",
        frontend_package_name=f"@company/feature-{feature_key}",
        backend_module_name=snake,
        feature_var_prefix=snake.upper(),
    )

    return NormalizedScaffoldConfig(
        names=names,
        frontend_enabled=frontend.enabled,
        backend_enabled=backend.enabled,
        shell_integration=frontend.shell_integration,
        registry_enabled=registry.enabled,
        registry_mode=registry.mode,
        auth_mode=auth.mode,
        auth_context_source="shell" if auth.shell_auth_required else "local",
        auth_shell_auth_required=auth.shell_auth_required,
        auth_token_forwarding=auth.token_forwarding,
        auth_allowed_dev_modes=auth.allowed_dev_modes,
        auth_roles=auth.roles,
        backend_token_strategy=auth.backend_token_strategy,
        scheduled_jobs=config.scheduled_jobs,
        event_driven_jobs=config.event_driven_jobs,
        event_listeners=config.event_listeners,
        published_events=events.publishes,
        consumed_events=events.consumes,
        backend_target=deployment.backend_target,
        worker_target=deployment.worker_target,
        include_terraform=getattr(deployment, "include_terraform", True),
        include_github_actions=getattr(deployment, "include_github_actions", True),
        include_docs=getattr(dx, "include_docs", True),
        include_tests=getattr(dx, "include_tests", True),
        include_scripts=getattr(dx, "include_scripts", True),
        manifest_version=version,
        database_enabled=database_enabled,
        database_targets=database_targets,
        postgres_enabled=postgres_enabled,
        postgres_orm_enabled=postgres_orm_enabled,
        postgres_migrations_enabled=postgres_migrations_enabled,
        snowflake_enabled=snowflake_enabled,
        blob_storage_enabled=blob_storage_enabled,
        blob_storage_provider=blob_storage_provider,
        blob_storage_targets=blob_storage_targets,
        cache_enabled=cache_enabled,
        cache_targets=cache_targets,
        memory_cache_enabled=memory_cache_enabled,
        redis_enabled=redis_enabled,
    )