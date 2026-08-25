from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

from feature_scaffold.metadata import build_scaffold_metadata

from .file_writer import write_text_file
from .manifest_builder import build_feature_manifest
from .models import ScaffoldConfig
from .normalizers import normalize_config
from .planners import build_file_plan
from .template_engine import TemplateEngine
from .validators import validate_config


def local_dev_ports(feature_key: str) -> SimpleNamespace:
    """Default local ports; aligned with scripts/run-local.*.j2."""
    if feature_key == "catalog":
        return SimpleNamespace(frontend_port=3300, backend_port=8200, bootstrap_port=3060)
    return SimpleNamespace(frontend_port=3200, backend_port=8100, bootstrap_port=3050)


def _build_template_context(config) -> dict:
    data = asdict(config)
    data["names"] = asdict(config.names)

    # Convenience aliases for templates
    data["auth_mode"] = config.auth_mode
    data["auth_shell_required"] = config.auth_shell_auth_required
    data["auth_token_forwarding"] = config.auth_token_forwarding
    data["auth_allowed_dev_modes"] = config.auth_allowed_dev_modes
    data["auth_roles"] = config.auth_roles
    data["ports"] = local_dev_ports(config.names.feature_key)

    return data


def _merge_context(base: dict, extra: dict | None) -> dict:
    merged = dict(base)
    if extra:
        merged.update(extra)
    return merged


class ScaffoldGenerator:
    def __init__(self, templates_dir: Path) -> None:
        self.engine = TemplateEngine(templates_dir)

    def generate(self, config: ScaffoldConfig, output_root: Path) -> Path:
        validate_config(config)
        normalized = normalize_config(config)
        repo_dir = output_root / normalized.names.repo_name
        base_context = _build_template_context(normalized)

        plan = build_file_plan(normalized)

        for item in plan:
            if item.target_path == "scaffold.metadata.json":
                continue
            context = _merge_context(base_context, item.template_context)
            target_file = repo_dir / item.target_path

            if item.target_path == "contracts/feature-manifest.json":
                content = build_feature_manifest(normalized)
            elif item.literal_content is not None:
                content = item.literal_content
            elif item.template_path is not None:
                content = self.engine.render(item.template_path, context)
            else:
                raise ValueError(f"No content source for {item.target_path}")

            if item.policy == "create_if_missing" and target_file.exists():
                continue

            write_text_file(repo_dir, item.target_path, content)
            written = repo_dir / item.target_path
            if written.suffix == ".sh":
                os.chmod(written, 0o755)

        metadata = build_scaffold_metadata(normalized, plan)
        write_text_file(
            repo_dir,
            "scaffold.metadata.json",
            json.dumps(metadata, indent=2) + "\n",
        )

        return repo_dir
