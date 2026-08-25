from __future__ import annotations

import re

from .models import ScaffoldConfig


class ValidationError(ValueError):
    pass


def _validate_event_name(event_name: str) -> None:
    if not re.fullmatch(r"[a-z0-9]+([.-][a-z0-9]+)*(\.[a-z0-9]+([.-][a-z0-9]+)*)+", event_name):
        raise ValidationError(
            f"Invalid event name '{event_name}'. Expected dotted lower-case form like 'orders.created'."
        )


def validate_config(config: ScaffoldConfig) -> None:
    if not config.feature_name.strip():
        raise ValidationError("feature_name is required.")
    if not config.display_name.strip():
        raise ValidationError("display_name is required.")
    if not config.base_path.strip().startswith("/"):
        raise ValidationError("base_path must start with '/'.")

    if config.auth.mode == "none" and config.auth.backend_token_strategy != "none":
        raise ValidationError("auth.mode='none' requires backend_token_strategy='none'.")

    if not any([
        config.frontend.enabled,
        config.backend.enabled,
        bool(config.scheduled_jobs),
        bool(config.event_driven_jobs),
        bool(config.event_listeners),
    ]):
        raise ValidationError("At least one execution surface must be enabled.")

    seen = set()
    for job in config.scheduled_jobs:
        if not job.name.strip():
            raise ValidationError("Scheduled job name cannot be empty.")
        if not job.schedule.strip():
            raise ValidationError(f"Scheduled job '{job.name}' requires a schedule.")
        if job.name in seen:
            raise ValidationError(f"Duplicate component name: {job.name}")
        seen.add(job.name)

    for worker in config.event_driven_jobs:
        if not worker.name.strip():
            raise ValidationError("Event-driven job name cannot be empty.")
        if worker.name in seen:
            raise ValidationError(f"Duplicate component name: {worker.name}")
        seen.add(worker.name)
        if worker.trigger.kind == "topic-subscription":
            if not worker.trigger.topic.strip() or not worker.trigger.subscription.strip():
                raise ValidationError(
                    f"Event-driven job '{worker.name}' requires trigger.topic and trigger.subscription."
                )
        elif worker.trigger.kind == "queue":
            if not worker.trigger.queue.strip():
                raise ValidationError(
                    f"Event-driven job '{worker.name}' requires trigger.queue."
                )

    for listener in config.event_listeners:
        if not listener.name.strip():
            raise ValidationError("Event listener name cannot be empty.")
        if listener.name in seen:
            raise ValidationError(f"Duplicate component name: {listener.name}")
        seen.add(listener.name)
        if not listener.event_name.strip():
            raise ValidationError(f"Event listener '{listener.name}' requires event_name.")
        _validate_event_name(listener.event_name)

    for event in config.events.publishes:
        _validate_event_name(event.name)
    for event in config.events.consumes:
        _validate_event_name(event.name)

    duplicates = {e.name for e in config.events.publishes}.intersection(
        {e.name for e in config.events.consumes}
    )
    if duplicates:
        raise ValidationError(
            f"Events cannot currently appear in both publishes and consumes: {sorted(duplicates)}"
        )

    # --- capability validation ---
    database = config.capabilities.database
    blob_storage = config.capabilities.blob_storage
    cache = config.capabilities.cache

    valid_targets = {"api", "jobs", "listeners"}

    # Database capability
    for target in database.targets:
        if target not in valid_targets:
            raise ValidationError(f"Unsupported database target: {target}")

    if database.enabled:
        if not database.targets:
            raise ValidationError(
                "Database capability is enabled but no database targets were specified."
            )

        if not (
            database.providers.postgresql.enabled
            or database.providers.snowflake.enabled
        ):
            raise ValidationError(
                "Database capability is enabled but no database providers were enabled."
            )

    # Validate PostgreSQL internals only if PostgreSQL is enabled
    if database.providers.postgresql.enabled:
        pass

    # Blob storage capability
    for target in blob_storage.targets:
        if target not in valid_targets:
            raise ValidationError(f"Unsupported blob storage target: {target}")

    if blob_storage.enabled and not blob_storage.targets:
        raise ValidationError(
            "Blob storage capability is enabled but no blob storage targets were specified."
        )

    if blob_storage.enabled and blob_storage.provider not in {"azure_blob"}:
        raise ValidationError(
            f"Unsupported blob storage provider: {blob_storage.provider}"
        )

    # Cache capability
    for target in cache.targets:
        if target not in valid_targets:
            raise ValidationError(f"Unsupported cache target: {target}")

    if cache.enabled:
        if not cache.targets:
            raise ValidationError(
                "Cache capability is enabled but no cache targets were specified."
            )

        if not (
            cache.providers.memory.enabled
            or cache.providers.redis.enabled
        ):
            raise ValidationError(
                "Cache capability is enabled but no cache providers were enabled."
            )

    if cache.providers.redis.enabled and not cache.enabled:
        raise ValidationError(
            "Redis cache cannot be enabled when cache capability is disabled."
        )

    if cache.enabled and not cache.providers.memory.enabled and not cache.providers.redis.enabled:
        raise ValidationError(
            "At least one cache provider must be enabled when cache capability is enabled."
        )