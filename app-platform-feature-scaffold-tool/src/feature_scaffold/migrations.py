from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from feature_scaffold.version import SCAFFOLD_VERSION


@dataclass(frozen=True, slots=True)
class ScaffoldMigration:
    version: str
    key: str
    description: str


MigrationTransform = Callable[[dict[str, Any]], dict[str, Any]]

MIGRATIONS: list[ScaffoldMigration] = [
    ScaffoldMigration(
        version="0.1.0",
        key="initial-incremental-scaffold",
        description="Initial incremental scaffold engine with plan/apply, metadata, and ownership policies.",
    ),
]

MIGRATION_TRANSFORMS: dict[str, MigrationTransform] = {}


def get_migrations_since(version: str | None) -> list[ScaffoldMigration]:
    if version is None:
        return MIGRATIONS

    seen = False
    result: list[ScaffoldMigration] = []

    for migration in MIGRATIONS:
        if seen:
            result.append(migration)
        elif migration.version == version:
            seen = True

    if not seen:
        return MIGRATIONS

    return result


def get_current_scaffold_version() -> str:
    return SCAFFOLD_VERSION


def apply_migrations(
    metadata: dict[str, Any],
    applied_migration_keys: list[str] | None = None,
) -> dict[str, Any]:
    updated = dict(metadata)
    already_applied = set(applied_migration_keys or [])

    for migration in MIGRATIONS:
        if migration.key in already_applied:
            continue

        transform = MIGRATION_TRANSFORMS.get(migration.key)
        if transform is not None:
            updated = transform(updated)

    return updated


def get_pending_migrations(
    existing_version: str | None,
    applied_migration_keys: list[str] | None = None,
) -> list[ScaffoldMigration]:
    migrations = get_migrations_since(existing_version)
    applied = set(applied_migration_keys or [])
    return [m for m in migrations if m.key not in applied]
