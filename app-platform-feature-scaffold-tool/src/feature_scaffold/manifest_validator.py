from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


def _schema_path() -> Path:
    return Path(__file__).parent / "manifest.schema.json"


def load_manifest_schema() -> dict[str, Any]:
    return json.loads(_schema_path().read_text(encoding="utf-8"))


def validate_manifest_dict(manifest: dict[str, Any]) -> None:
    schema = load_manifest_schema()
    validator = Draft202012Validator(schema)
    validator.validate(manifest)


def validate_manifest_json_text(manifest_text: str) -> None:
    manifest = json.loads(manifest_text)
    validate_manifest_dict(manifest)