from __future__ import annotations

from feature_scaffold.migrations import MIGRATIONS, apply_migrations
from feature_scaffold.version import SCAFFOLD_VERSION


def build_scaffold_metadata(normalized, plan, existing_metadata=None, upgrade: bool = False) -> dict:
    metadata = {
        "scaffoldVersion": SCAFFOLD_VERSION,
        "featureKey": normalized.names.feature_key,
        "repoName": normalized.names.repo_name,
        "manifestVersion": normalized.manifest_version,
        "managedFiles": {
            item.target_path: item.policy for item in plan
        },
    }

    if upgrade and existing_metadata:
        applied = existing_metadata.get("appliedMigrations", [])
        metadata = apply_migrations(metadata, applied)

    metadata["appliedMigrations"] = [
        m.key for m in MIGRATIONS
    ]

    return metadata


def merge_applied_migrations(existing: list[str] | None) -> list[str]:
    existing_set = set(existing or [])
    all_keys = [m.key for m in MIGRATIONS]

    result = list(existing_set)

    for key in all_keys:
        if key not in existing_set:
            result.append(key)

    return result
