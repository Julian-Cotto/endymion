from __future__ import annotations

import argparse
import difflib
import json
from pathlib import Path

from feature_scaffold.exit_codes import MODIFIED_FILES, ORPHAN_FILES, VERSION_MISMATCH
from feature_scaffold.file_writer import write_text_file
from feature_scaffold.metadata import build_scaffold_metadata
from feature_scaffold.migrations import get_migrations_since, get_pending_migrations
from feature_scaffold.planner_diff import compute_plan_diff
from feature_scaffold.version import SCAFFOLD_VERSION

from .generator import ScaffoldGenerator, _build_template_context, _merge_context
from .manifest_builder import build_feature_manifest
from .models import (
    AuthConfig,
    BackendConfig,
    DeploymentConfig,
    DeveloperExperienceConfig,
    EventContract,
    EventDrivenJobConfig,
    EventListenerConfig,
    EventTriggerConfig,
    EventsConfig,
    FrontendConfig,
    RegistryConfig,
    RetryPolicy,
    ScaffoldConfig,
    ScheduledJobConfig,
    ApiDeploymentConfig,
    JobDeploymentTargetConfig,
    ListenerDeploymentTargetConfig,
    CapabilitiesConfig,
    DatabaseCapabilityConfig,
    DatabaseProvidersConfig,
    PostgresCapabilityConfig,
    SnowflakeCapabilityConfig,
    BlobStorageCapabilityConfig,
    CacheCapabilityConfig,
    CacheProvidersConfig,
    MemoryCacheCapabilityConfig,
    RedisCacheCapabilityConfig,
)
from .normalizers import normalize_config
from .planners import build_file_plan


def _load_config(config_path: Path) -> ScaffoldConfig:
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    
    auth = raw.get("auth") or {}

    allowed_dev_modes = auth.get("allowed_dev_modes", ["mock"])
    if not isinstance(allowed_dev_modes, list):
        allowed_dev_modes = ["mock"]

    roles = auth.get("roles", [])
    if not isinstance(roles, list):
        roles = []

    auth_mode = str(auth.get("mode", "mock")).strip().lower()

    raw["auth"] = {
        "mode": auth_mode,
        "backend_token_strategy": auth.get(
            "backend_token_strategy",
            "forwarded-bearer" if auth_mode == "entra" else "none",
        ),
        "shell_auth_required": auth.get("shell_auth_required", True),
        "token_forwarding": auth.get("token_forwarding", auth_mode == "entra"),
        "allowed_dev_modes": allowed_dev_modes,
        "roles": roles,
    }

    # --- capabilities normalization ---
    capabilities = raw.get("capabilities") or {}

    database = capabilities.get("database") or {}
    database_targets = database.get("targets", [])
    if not isinstance(database_targets, list):
        database_targets = []

    providers = database.get("providers") or {}
    postgresql = providers.get("postgresql") or {}
    snowflake = providers.get("snowflake") or {}

    blob_storage = capabilities.get("blob_storage") or {}
    blob_storage_targets = blob_storage.get("targets", [])
    if not isinstance(blob_storage_targets, list):
        blob_storage_targets = []

    cache = capabilities.get("cache") or {}
    cache_targets = cache.get("targets", [])
    if not isinstance(cache_targets, list):
        cache_targets = []

    cache_providers = cache.get("providers") or {}
    memory_cache = cache_providers.get("memory") or {}
    redis_cache = cache_providers.get("redis") or {}

    raw["capabilities"] = {
        "database": {
            "enabled": database.get("enabled", False),
            "targets": database_targets,
            "providers": {
                "postgresql": {
                    "enabled": postgresql.get("enabled", False),
                    "orm": postgresql.get("orm", True),
                    "migrations": postgresql.get("migrations", True),
                },
                "snowflake": {
                    "enabled": snowflake.get("enabled", False),
                },
            },
        },
        "blob_storage": {
            "enabled": blob_storage.get("enabled", False),
            "provider": blob_storage.get("provider", "azure_blob"),
            "targets": blob_storage_targets,
        },
        "cache": {
            "enabled": cache.get("enabled", False),
            "targets": cache_targets,
            "providers": {
                "memory": {
                    "enabled": memory_cache.get("enabled", True),
                },
                "redis": {
                    "enabled": redis_cache.get("enabled", False),
                },
            },
        },
    }
    # --- end capabilities normalization ---

    scheduled_jobs = [
        ScheduledJobConfig(
            name=j["name"],
            description=j.get("description", ""),
            schedule=j.get("schedule", ""),
            entrypoint=j.get("entrypoint", ""),
            retry_policy=RetryPolicy(**j.get("retry_policy", {})),
        )
        for j in raw.get("scheduled_jobs", [])
    ]

    event_driven_jobs = []
    for w in raw.get("event_driven_jobs", []):
        event_driven_jobs.append(
            EventDrivenJobConfig(
                name=w["name"],
                description=w.get("description", ""),
                trigger=EventTriggerConfig(**w.get("trigger", {})),
                payload_schema=w.get("payload_schema", ""),
                dead_letter=w.get("dead_letter", True),
                max_concurrency=w.get("max_concurrency", 1),
                retry_policy=RetryPolicy(**w.get("retry_policy", {})),
            )
        )

    event_listeners = [
        EventListenerConfig(
            name=listener["name"],
            description=listener.get("description", ""),
            event_name=listener.get("event_name", ""),
            payload_schema=listener.get("payload_schema", ""),
        )
        for listener in raw.get("event_listeners", [])
    ]

    events = EventsConfig(
        publishes=[EventContract(**e) for e in raw.get("events", {}).get("publishes", [])],
        consumes=[EventContract(**e) for e in raw.get("events", {}).get("consumes", [])],
    )

    deployment_raw = raw.get("deployment", {})

    api_deployment = ApiDeploymentConfig(
        **deployment_raw.get("api", {})
    )

    job_deployments = [
        JobDeploymentTargetConfig(**j)
        for j in deployment_raw.get("jobs", [])
    ]

    listener_deployments = [
        ListenerDeploymentTargetConfig(**listener)
        for listener in deployment_raw.get("listeners", [])
    ]

    return ScaffoldConfig(
        feature_name=raw["feature_name"],
        display_name=raw["display_name"],
        description=raw.get("description", ""),
        base_path=raw["base_path"],
        version=raw.get("version", "0.1.0"),
        frontend=FrontendConfig(**raw.get("frontend", {})),
        backend=BackendConfig(**raw.get("backend", {})),
        auth=AuthConfig(**raw.get("auth", {})),
        registry=RegistryConfig(**raw.get("registry", {})),
        capabilities=CapabilitiesConfig(
            database=DatabaseCapabilityConfig(
                enabled=raw.get("capabilities", {}).get("database", {}).get("enabled", False),
                targets=raw.get("capabilities", {}).get("database", {}).get("targets", []),
                providers=DatabaseProvidersConfig(
                    postgresql=PostgresCapabilityConfig(
                        **raw.get("capabilities", {})
                          .get("database", {})
                          .get("providers", {})
                          .get("postgresql", {})
                    ),
                    snowflake=SnowflakeCapabilityConfig(
                        **raw.get("capabilities", {})
                          .get("database", {})
                          .get("providers", {})
                          .get("snowflake", {})
                    ),
                ),
            ),
            blob_storage=BlobStorageCapabilityConfig(
                **raw.get("capabilities", {}).get("blob_storage", {})
            ),
            cache=CacheCapabilityConfig(
                enabled=raw.get("capabilities", {}).get("cache", {}).get("enabled", False),
                targets=raw.get("capabilities", {}).get("cache", {}).get("targets", []),
                providers=CacheProvidersConfig(
                    memory=MemoryCacheCapabilityConfig(
                        **raw.get("capabilities", {})
                          .get("cache", {})
                          .get("providers", {})
                          .get("memory", {})
                    ),
                    redis=RedisCacheCapabilityConfig(
                        **raw.get("capabilities", {})
                          .get("cache", {})
                          .get("providers", {})
                          .get("redis", {})
                    ),
                ),
            ),
        ),
        scheduled_jobs=scheduled_jobs,
        event_driven_jobs=event_driven_jobs,
        event_listeners=event_listeners,
        events=events,
        deployment=DeploymentConfig(
            api=api_deployment,
            jobs=job_deployments,
            listeners=listener_deployments,
        ),
        developer_experience=DeveloperExperienceConfig(**raw.get("developer_experience", {})),
    )

def run_plan(
    config_path: Path,
    repo_path: Path,
    templates_dir: Path,
    fail_on_modified: bool = False,
    fail_on_orphan: bool = False,
    json_output: bool = False,
    show_diff: bool = False,
    fail_on_version_mismatch: bool = False,
    upgrade: bool = False,
    upgrade_preview: bool = False,
) -> None:
    if not repo_path.name:
        raise SystemExit("--repo must point to a repository directory")

    config = _load_config(config_path)
    normalized = normalize_config(config)
    plan = build_file_plan(normalized)
    version_mismatch = _check_scaffold_version(repo_path)

    if upgrade_preview and version_mismatch:
        metadata = _load_existing_metadata(repo_path)
        if metadata is None:
            print("\nUpgrade Preview: scaffold.metadata.json missing or unreadable.")
            return

        print("\nUpgrade Preview:")
        print(f"Current version: {metadata.get('scaffoldVersion')}")
        print(f"Target version: {SCAFFOLD_VERSION}")

        migrations = get_migrations_since(metadata.get("scaffoldVersion"))

        if not migrations:
            print("No migrations required.")
        else:
            print("Migrations to be applied:")
            for m in migrations:
                print(f"  - [{m.version}] {m.key}: {m.description}")

        return

    engine = ScaffoldGenerator(templates_dir).engine

    base_context = _build_template_context(normalized)
    existing_metadata = _load_existing_metadata(repo_path)
    rendered_content_by_path: dict[str, str] = {}

    for item in plan:
        context = _merge_context(base_context, item.template_context)

        if item.target_path == "contracts/feature-manifest.json":
            content = build_feature_manifest(normalized)
        elif item.target_path == "scaffold.metadata.json":
            content = json.dumps(
                build_scaffold_metadata(
                    normalized,
                    plan,
                    existing_metadata=existing_metadata,
                    upgrade=False,
                ),
                indent=2,
            ) + "\n"
        elif item.literal_content is not None:
            content = item.literal_content
        elif item.template_path is not None:
            content = engine.render(item.template_path, context)
        else:
            continue

        rendered_content_by_path[item.target_path] = content

    changes = compute_plan_diff(repo_path, plan, rendered_content_by_path)

    counts: dict[str, int] = {}

    for action, _ in changes:
        counts[action] = counts.get(action, 0) + 1

    if json_output:
        payload = {
            "repo": str(repo_path),
            "summary": {
                action: counts.get(action, 0)
                for action in ["CREATE", "REPLACE", "MODIFIED", "SKIP", "ORPHAN"]
                if counts.get(action, 0) > 0
            },
            "changes": [
                {"action": action, "path": path}
                for action, path in changes
            ],
        }

        print(json.dumps(payload, indent=2))

    else:
        for action, path in changes:
            print(f"{action:8} {path}")

            if show_diff and action == "MODIFIED":
                target = repo_path / path
                expected = rendered_content_by_path.get(path)

                if expected is not None and target.exists():
                    current = target.read_text(encoding="utf-8")

                    diff = difflib.unified_diff(
                        expected.splitlines(keepends=True),
                        current.splitlines(keepends=True),
                        fromfile=f"expected/{path}",
                        tofile=f"current/{path}",
                    )

                    print("".join(diff))

        print("\nSummary:")
        for action in ["CREATE", "REPLACE", "MODIFIED", "SKIP", "ORPHAN"]:
            if action in counts:
                print(f"{action:8}: {counts[action]}")

    if fail_on_modified:
        has_modified = any(action == "MODIFIED" for action, _ in changes)
        if has_modified:
            print("Plan failed: modified scaffold-managed files detected")
            raise SystemExit(MODIFIED_FILES)

    if fail_on_orphan:
        has_orphan = any(action == "ORPHAN" for action, _ in changes)
        if has_orphan:
            print("Plan failed: orphaned scaffold-managed files detected")
            raise SystemExit(ORPHAN_FILES)

    if fail_on_version_mismatch and version_mismatch and not upgrade:
        print("Plan failed: scaffold version mismatch. Use --upgrade to upgrade the scaffold version.")
        raise SystemExit(VERSION_MISMATCH)


def _prompt_yes_no(message: str) -> bool:
    response = input(f"{message} [y/N]: ").strip().lower()
    return response in {"y", "yes"}


def _load_existing_metadata(repo_path: Path) -> dict | None:
    metadata_file = repo_path / "scaffold.metadata.json"
    if not metadata_file.exists():
        return None

    try:
        return json.loads(metadata_file.read_text(encoding="utf-8"))
    except Exception:
        return None


def _check_scaffold_version(repo_path: Path) -> bool:
    metadata = _load_existing_metadata(repo_path)
    if not metadata:
        return False

    existing_version = metadata.get("scaffoldVersion")

    if existing_version != SCAFFOLD_VERSION:
        print(
            f"WARNING: scaffold version mismatch. "
            f"repo={existing_version}, tool={SCAFFOLD_VERSION}"
        )

        migrations = get_migrations_since(existing_version)
        applied = set(metadata.get("appliedMigrations", []))
        pending = [m for m in migrations if m.key not in applied]

        if pending:
            print("Pending migrations (not yet applied):")
            for m in pending:
                print(f"  - [{m.version}] {m.key}: {m.description}")

        return True

    return False


def run_apply(
    config_path: Path,
    repo_path: Path,
    templates_dir: Path,
    interactive: bool = False,
    fail_on_version_mismatch: bool = False,
    upgrade: bool = False,
    dry_run: bool = False,
    non_interactive: bool = False,
) -> None:
    config = _load_config(config_path)
    normalized = normalize_config(config)
    generator = ScaffoldGenerator(templates_dir)

    if interactive and non_interactive:
        raise SystemExit("--interactive and --non-interactive cannot be used together")

    if not repo_path.name:
        raise SystemExit("--repo must point to a repository directory")

    output_root = repo_path.parent
    expected_repo_dir = output_root / normalized.names.repo_name

    if expected_repo_dir != repo_path:
        raise SystemExit(
            f"--repo does not match config output path. "
            f"Expected: {expected_repo_dir}"
        )

    version_mismatch = _check_scaffold_version(repo_path)
    existing_metadata = _load_existing_metadata(repo_path)

    if upgrade and version_mismatch:
        current_version = existing_metadata.get("scaffoldVersion") if existing_metadata else None

        print(f"\nApplying scaffold upgrade from {current_version} to {SCAFFOLD_VERSION}")

        pending = get_pending_migrations(
            current_version,
            existing_metadata.get("appliedMigrations") if existing_metadata else None,
        )

        if not pending:
            print("No migrations to apply.")
        else:
            for m in pending:
                print(f"Applied migration: {m.key}")

    if fail_on_version_mismatch and version_mismatch and not upgrade:
        print("Plan failed: scaffold version mismatch. Use --upgrade to upgrade the scaffold version.")
        raise SystemExit(VERSION_MISMATCH)

    plan = build_file_plan(normalized)
    base_context = _build_template_context(normalized)

    rendered_content_by_path: dict[str, str] = {}

    for item in plan:
        context = _merge_context(base_context, item.template_context)

        if item.target_path == "contracts/feature-manifest.json":
            content = build_feature_manifest(normalized)
        elif item.target_path == "scaffold.metadata.json":
            content = json.dumps(
                build_scaffold_metadata(
                    normalized,
                    plan,
                    existing_metadata=existing_metadata,
                    upgrade=upgrade,
                ),
                indent=2,
            ) + "\n"
        elif item.literal_content is not None:
            content = item.literal_content
        elif item.template_path is not None:
            content = generator.engine.render(item.template_path, context)
        else:
            continue

        rendered_content_by_path[item.target_path] = content

    changes = compute_plan_diff(repo_path, plan, rendered_content_by_path)

    if non_interactive:
        has_modified = any(action == "MODIFIED" for action, _ in changes)
        if has_modified:
            print("Apply failed: modified scaffold-managed files detected in non-interactive mode")
            raise SystemExit(MODIFIED_FILES)

    allowed_modified_paths: set[str] = set()

    if interactive:
        for action, path in changes:
            if action == "MODIFIED":
                if path == "scaffold.metadata.json":
                    allowed_modified_paths.add(path)
                    continue

                if _prompt_yes_no(f"Overwrite modified file {path}?"):
                    allowed_modified_paths.add(path)

    for item in plan:
        context = _merge_context(base_context, item.template_context)
        target_file = repo_path / item.target_path

        if item.target_path == "contracts/feature-manifest.json":
            content = build_feature_manifest(normalized)
        elif item.target_path == "scaffold.metadata.json":
            content = json.dumps(
                build_scaffold_metadata(
                    normalized,
                    plan,
                    existing_metadata=existing_metadata,
                    upgrade=upgrade,
                ),
                indent=2,
            ) + "\n"
        elif item.literal_content is not None:
            content = item.literal_content
        elif item.template_path is not None:
            content = generator.engine.render(item.template_path, context)
        else:
            raise ValueError(f"No content source for {item.target_path}")

        if item.policy == "create_if_missing" and target_file.exists():
            continue

        if interactive and target_file.exists():
            expected = rendered_content_by_path.get(item.target_path)
            if expected is not None and target_file.read_text(encoding="utf-8") != expected:
                if item.target_path not in allowed_modified_paths:
                    continue

        if dry_run:
            print(f"DRY RUN: Skipping write to {item.target_path}")
        else:
            write_text_file(repo_path, item.target_path, content)

    if dry_run:
        print(f"Dry-run complete for: {repo_path}")
    else:
        print(f"Applied scaffold updates to: {repo_path}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="feature-scaffold")
    parser.add_argument("command", choices=["create", "plan", "apply"])
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", default=".")
    parser.add_argument("--repo", required=False)
    parser.add_argument("--templates-dir", default=str(Path(__file__).parent / "templates"))
    parser.add_argument("--fail-on-modified", action="store_true")
    parser.add_argument("--fail-on-orphan", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--diff", action="store_true", dest="show_diff")
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--fail-on-version-mismatch", action="store_true")
    parser.add_argument("--upgrade", action="store_true")
    parser.add_argument("--upgrade-preview", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--non-interactive", action="store_true")
    args = parser.parse_args()

    if args.command == "create":
        config = _load_config(Path(args.config))
        generator = ScaffoldGenerator(Path(args.templates_dir))
        repo_dir = generator.generate(config, Path(args.output_dir))
        print(f"Generated scaffold at: {repo_dir}")

    elif args.command == "plan":
        if not args.repo:
            raise SystemExit("--repo is required for plan")
        run_plan(
            Path(args.config),
            Path(args.repo),
            Path(args.templates_dir),
            fail_on_modified=args.fail_on_modified,
            fail_on_orphan=args.fail_on_orphan,
            json_output=args.json_output,
            show_diff=args.show_diff,
            fail_on_version_mismatch=args.fail_on_version_mismatch,
            upgrade=args.upgrade,
            upgrade_preview=args.upgrade_preview,
        )

    elif args.command == "apply":
        if not args.repo:
            raise SystemExit("--repo is required for apply")
        run_apply(
            Path(args.config),
            Path(args.repo),
            Path(args.templates_dir),
            interactive=args.interactive,
            fail_on_version_mismatch=args.fail_on_version_mismatch,
            upgrade=args.upgrade,
            dry_run=args.dry_run,
            non_interactive=args.non_interactive,
        )


if __name__ == "__main__":
    main()
