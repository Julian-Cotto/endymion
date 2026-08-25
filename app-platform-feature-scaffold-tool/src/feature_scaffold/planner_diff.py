from __future__ import annotations

import json
from pathlib import Path
from typing import TypeAlias

from feature_scaffold.models import PlannedFile

Change: TypeAlias = tuple[str, str]


def _load_managed_files(repo_dir: Path) -> dict[str, str]:
    metadata_path = repo_dir / "scaffold.metadata.json"

    if not metadata_path.exists():
        return {}

    data = json.loads(metadata_path.read_text(encoding="utf-8"))
    return data.get("managedFiles", {})


def compute_plan_diff(
    repo_dir: Path,
    plan: list[PlannedFile],
    rendered_content_by_path: dict[str, str] | None = None,
) -> list[Change]:
    changes: list[Change] = []

    planned_paths = {item.target_path for item in plan}
    managed_files = _load_managed_files(repo_dir)
    rendered_content_by_path = rendered_content_by_path or {}

    for item in plan:
        target = repo_dir / item.target_path

        if not target.exists():
            changes.append(("CREATE", item.target_path))
            continue

        if item.policy == "replace":
            expected = rendered_content_by_path.get(item.target_path)
            if expected is not None:
                current = target.read_text(encoding="utf-8")
                if current != expected:
                    changes.append(("MODIFIED", item.target_path))
                    continue
            changes.append(("REPLACE", item.target_path))

        elif item.policy == "create_if_missing":
            changes.append(("SKIP", item.target_path))
        else:
            changes.append(("UNKNOWN", item.target_path))

    for path in sorted(managed_files):
        if path not in planned_paths and (repo_dir / path).exists():
            changes.append(("ORPHAN", path))

    return changes
