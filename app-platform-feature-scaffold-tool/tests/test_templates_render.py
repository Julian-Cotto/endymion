from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from feature_scaffold.models import (
    BlobStorageCapabilityConfig,
    CapabilitiesConfig,
    DatabaseCapabilityConfig,
    DatabaseProvidersConfig,
    DeveloperExperienceConfig,
    EventContract,
    EventDrivenJobConfig,
    EventListenerConfig,
    EventTriggerConfig,
    EventsConfig,
    PostgresCapabilityConfig,
    RegistryConfig,
    RetryPolicy,
    ScaffoldConfig,
    ScheduledJobConfig,
    SnowflakeCapabilityConfig,
)
from feature_scaffold.generator import local_dev_ports
from feature_scaffold.normalizers import normalize_config
from feature_scaffold.template_engine import TemplateEngine


def _build_context() -> dict:
    config = ScaffoldConfig(
        feature_name="orders",
        display_name="Orders",
        description="Orders feature",
        base_path="/orders",
        registry=RegistryConfig(enabled=True, mode="rest"),
        scheduled_jobs=[
            ScheduledJobConfig(
                name="nightly-sync",
                description="Nightly sync job",
                schedule="0 1 * * *",
                entrypoint="jobs.nightly_sync.runner:run",
                retry_policy=RetryPolicy(max_retries=3, backoff="exponential"),
            )
        ],
        event_driven_jobs=[
            EventDrivenJobConfig(
                name="process-order",
                description="Process order worker",
                trigger=EventTriggerConfig(kind="queue", queue="orders"),
                payload_schema="ProcessOrderPayload",
                dead_letter=True,
                max_concurrency=1,
                retry_policy=RetryPolicy(max_retries=5, backoff="exponential"),
            )
        ],
        event_listeners=[
            EventListenerConfig(
                name="inventory-updated",
                description="Inventory listener",
                event_name="inventory.updated",
                payload_schema="InventoryUpdatedPayload",
            )
        ],
        events=EventsConfig(
            publishes=[EventContract(name="orders.created", schema="OrderCreated")],
            consumes=[EventContract(name="inventory.updated", schema="InventoryUpdated")],
        ),
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
                targets=["api", "jobs", "listeners"],
            ),
        ),
        developer_experience=DeveloperExperienceConfig(
            include_docs=True,
            include_tests=True,
            include_scripts=True,
        ),
    )

    normalized = normalize_config(config)
    data = asdict(normalized)
    data["names"] = asdict(normalized.names)
    data["ports"] = local_dev_ports(normalized.names.feature_key)

    # Representative per-target context used by templated job/worker/listener files
    data.update(
        {
            "target_name": "nightly-sync",
            "target_safe_name": "nightly_sync",
            "target_schedule": "0 1 * * *",
            "trigger_kind": "queue",
            "trigger_topic": "",
            "trigger_subscription": "",
            "trigger_queue": "orders",
            "target_event_name": "inventory.updated",
            "payload_schema": "InventoryUpdatedPayload",
            "dead_letter": True,
            "max_concurrency": 1,
            "max_retries": 5,
            "retry_backoff": "exponential",
            "event_name": "orders.created",
            "event_schema_name": "OrderCreated",
        }
    )

    return data


def test_all_jinja_templates_compile_and_render() -> None:
    templates_dir = Path("src/feature_scaffold/templates")
    engine = TemplateEngine(templates_dir)
    context = _build_context()

    template_paths = [
        str(path.relative_to(templates_dir))
        for path in templates_dir.rglob("*.j2")
    ]

    assert template_paths, "No .j2 templates found"

    for template_path in template_paths:
        rendered = engine.render(template_path, context)
        assert isinstance(rendered, str)