from feature_scaffold.models import (
    BlobStorageCapabilityConfig,
    CacheCapabilityConfig,
    CacheProvidersConfig,
    CapabilitiesConfig,
    DatabaseCapabilityConfig,
    DatabaseProvidersConfig,
    EventDrivenJobConfig,
    EventListenerConfig,
    EventTriggerConfig,
    MemoryCacheCapabilityConfig,
    PostgresCapabilityConfig,
    RedisCacheCapabilityConfig,
    ScheduledJobConfig,
    ScaffoldConfig,
    SnowflakeCapabilityConfig,
)
from feature_scaffold.normalizers import normalize_config
from feature_scaffold.planners import build_file_plan


def test_build_file_plan_includes_jobs_workers_and_listeners() -> None:
    config = ScaffoldConfig(
        feature_name="orders",
        display_name="Orders",
        base_path="/orders",
        scheduled_jobs=[ScheduledJobConfig(name="nightly-reconciliation", schedule="0 2 * * *")],
        event_driven_jobs=[EventDrivenJobConfig(name="submit-order", trigger=EventTriggerConfig(kind="topic-subscription", topic="orders", subscription="submit-order"), payload_schema="SubmitOrderRequested")],
        event_listeners=[EventListenerConfig(name="inventory-reserved", event_name="inventory.reserved", payload_schema="InventoryReserved")],
    )
    paths = {item.target_path for item in build_file_plan(normalize_config(config))}
    assert "jobs/nightly_reconciliation/main.py" in paths
    assert "workers/submit_order/main.py" in paths
    assert "listeners/inventory_reserved/main.py" in paths


def test_build_file_plan_includes_database_and_blob_storage_platform_files() -> None:
    config = ScaffoldConfig(
        feature_name="orders",
        display_name="Orders",
        base_path="/orders",
        capabilities=CapabilitiesConfig(
            database=DatabaseCapabilityConfig(
                enabled=True,
                targets=["api", "jobs", "listeners"],
                providers=DatabaseProvidersConfig(
                    postgresql=PostgresCapabilityConfig(
                        enabled=True,
                        orm=True,
                        migrations=True,
                    ),
                    snowflake=SnowflakeCapabilityConfig(
                        enabled=True,
                    ),
                ),
            ),
            blob_storage=BlobStorageCapabilityConfig(
                enabled=True,
                provider="azure_blob",
                targets=["api", "jobs"],
            ),
        ),
    )

    normalized = normalize_config(config)
    plan = build_file_plan(normalized)
    paths = {item.target_path for item in plan}

    assert "backend/app/platform/database/config.py" in paths
    assert "backend/app/platform/database/base.py" in paths
    assert "backend/app/platform/database/session.py" in paths
    assert "backend/app/platform/database/snowflake.py" in paths
    assert "backend/alembic.ini" in paths
    assert "backend/alembic/env.py" in paths
    assert "backend/alembic/script.py.mako" in paths
    assert "backend/alembic/versions/.gitkeep" in paths

    assert "backend/app/platform/storage/config.py" in paths
    assert "backend/app/platform/storage/blob_client.py" in paths
    assert "backend/app/platform/storage/blob_service.py" in paths
    assert "backend/app/api/platform_capabilities.py" in paths

def test_build_file_plan_excludes_database_and_blob_storage_platform_files_when_disabled() -> None:
    config = ScaffoldConfig(
        feature_name="orders",
        display_name="Orders",
        base_path="/orders",
    )

    normalized = normalize_config(config)
    plan = build_file_plan(normalized)
    paths = {item.target_path for item in plan}

    assert "backend/app/platform/database/config.py" not in paths
    assert "backend/app/platform/database/base.py" not in paths
    assert "backend/app/platform/database/session.py" not in paths
    assert "backend/app/platform/database/snowflake.py" not in paths
    assert "backend/alembic.ini" not in paths

    assert "backend/app/platform/storage/config.py" not in paths
    assert "backend/app/platform/storage/blob_client.py" not in paths
    assert "backend/app/platform/storage/blob_service.py" not in paths
    assert "backend/app/api/platform_capabilities.py" not in paths

def test_build_file_plan_includes_runtime_capability_helpers_for_jobs_and_listeners() -> None:
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

    normalized = normalize_config(config)
    plan = build_file_plan(normalized)
    paths = {item.target_path for item in plan}

    assert "backend/app/runtime/__init__.py" in paths
    assert "backend/app/runtime/database.py" in paths
    assert "backend/app/runtime/storage.py" in paths

def test_build_file_plan_includes_cache_files_when_cache_enabled() -> None:
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

    normalized = normalize_config(config)
    plan = build_file_plan(normalized)
    paths = {item.target_path for item in plan}

    assert "backend/app/platform/cache/config.py" in paths
    assert "backend/app/platform/cache/memory_cache.py" in paths
    assert "backend/app/platform/cache/cache_factory.py" in paths
    assert "backend/app/platform/cache/redis_cache.py" in paths
    assert "backend/app/platform/cache/dependencies.py" in paths
    assert "backend/app/runtime/cache.py" in paths
    assert "backend/app/api/cache_capabilities.py" in paths

def test_build_file_plan_includes_mount_tsx_not_ts() -> None:
    config = ScaffoldConfig(
        feature_name="orders",
        display_name="Orders",
        base_path="/orders",
    )

    normalized = normalize_config(config)
    plan = build_file_plan(normalized)
    paths = {item.target_path for item in plan}

    assert "frontend/src/mount.tsx" in paths
    assert "frontend/src/mount.ts" not in paths

def test_build_file_plan_includes_bootstrap_entry_tsx_not_ts() -> None:
    config = ScaffoldConfig(
        feature_name="orders",
        display_name="Orders",
        base_path="/orders",
    )

    normalized = normalize_config(config)
    plan = build_file_plan(normalized)
    paths = {item.target_path for item in plan}

    assert "frontend/src/bootstrap-entry.tsx" in paths
    assert "frontend/src/bootstrap-entry.ts" not in paths


def test_build_file_plan_includes_frontend_auth_types() -> None:
    config = ScaffoldConfig(
        feature_name="orders",
        display_name="Orders",
        base_path="/orders",
    )

    normalized = normalize_config(config)
    plan = build_file_plan(normalized)
    paths = {item.target_path for item in plan}

    assert "frontend/src/platform/authTypes.ts" in paths