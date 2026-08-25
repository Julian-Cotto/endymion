from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def _require_authorization(manifest: dict) -> None:
    authorization = manifest.get("authorization")

    if not isinstance(authorization, dict):
        raise ValueError("Resolved manifest is missing authorization block.")

    required_permissions = authorization.get("requiredPermissions")
    required_flags = authorization.get("requiredFlags")

    if not isinstance(required_permissions, list):
        raise ValueError("authorization.requiredPermissions must be a list.")

    if not isinstance(required_flags, list):
        raise ValueError("authorization.requiredFlags must be a list.")


def _require_auth(manifest: dict) -> None:
    auth = manifest.get("auth")

    if not isinstance(auth, dict):
        raise ValueError("Resolved manifest is missing auth block.")

    mode = auth.get("mode")
    if mode not in {"entra", "mock", "none"}:
        raise ValueError("auth.mode must be one of: entra, mock, none.")

    if "tokenForwarding" not in auth:
        raise ValueError("auth.tokenForwarding is required.")

    if "tokenStrategy" not in auth:
        raise ValueError("auth.tokenStrategy is required.")


def _normalize_nav(manifest: dict) -> dict:
    nav = manifest.get("nav") or manifest.get("navigation") or {}

    return {
        "label": nav.get("label") or manifest.get("displayName"),
        "icon": nav.get("icon") or "package",
        "group": nav.get("group"),
        "order": nav.get("order") if nav.get("order") is not None else 0,
    }


def _normalize_frontend(manifest: dict) -> dict:
    frontend = manifest.get("frontend") or {}
    entry_url = frontend.get("entryUrl")

    if not entry_url:
        raise ValueError("frontend.entryUrl is required.")

    return {
        "type": frontend.get("type") or "module",
        "entryUrl": entry_url,
        "integrity": frontend.get("integrity"),
        "basePath": frontend.get("basePath") or manifest.get("route") or manifest.get("basePath"),
    }


def _normalize_backend(manifest: dict) -> dict:
    backend = manifest.get("backend") or {}
    api_base_url = backend.get("apiBaseUrl") or backend.get("baseUrl")

    if not api_base_url:
        raise ValueError("backend.apiBaseUrl or backend.baseUrl is required.")

    return {
        "apiBaseUrl": api_base_url,
    }


def _normalize_metadata(manifest: dict) -> dict:
    metadata = manifest.get("metadata") or {}

    return {
        "ownerTeam": metadata.get("ownerTeam") or "platform",
        "commitSha": metadata.get("commitSha"),
        "buildId": metadata.get("buildId"),
        "releaseDate": metadata.get("releaseDate"),
    }


def _normalize_compatibility(manifest: dict) -> dict:
    compatibility = manifest.get("compatibility") or {}

    return {
        "shellContractMin": compatibility.get("shellContractMin"),
        "shellContractMax": compatibility.get("shellContractMax"),
    }


def _build_registry_payload(manifest: dict, environment: str) -> dict:
    route = manifest.get("route") or manifest.get("basePath")

    if not route:
        raise ValueError("manifest.route or manifest.basePath is required.")

    return {
        "manifestVersion": manifest.get("manifestVersion", "1.0"),
        "featureKey": manifest["featureKey"],
        "displayName": manifest["displayName"],
        "version": manifest["version"],
        "environment": environment,
        "route": route,
        "frontend": _normalize_frontend({**manifest, "route": route}),
        "backend": _normalize_backend(manifest),
        "nav": _normalize_nav(manifest),
        "authorization": manifest["authorization"],
        "auth": manifest["auth"],
        "compatibility": _normalize_compatibility(manifest),
        "metadata": _normalize_metadata(manifest),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        default="build/feature-manifest.resolved.json",
        help="Resolved feature manifest path",
    )
    parser.add_argument(
        "--environment",
        default=os.getenv("FEATURE_ENVIRONMENT", "local"),
        help="Target registry environment",
    )
    parser.add_argument(
        "--frontend-url",
        default=os.getenv("FEATURE_FRONTEND_ENTRY_URL"),
        help="Runtime frontend bootstrap entry URL",
    )
    parser.add_argument(
        "--backend-url",
        default=os.getenv("FEATURE_BACKEND_BASE_URL"),
        help="Runtime backend API base URL",
    )
    parser.add_argument(
        "--output",
        default="build/registry-payload.json",
        help="Output registry payload path",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    manifest_path = Path(args.manifest)
    output_path = Path(args.output)

    if not manifest_path.exists():
        raise FileNotFoundError(f"Resolved manifest not found: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    manifest["environment"] = args.environment
    manifest["route"] = manifest.get("route") or manifest.get("basePath")

    if args.frontend_url:
        manifest.setdefault("frontend", {})
        manifest["frontend"]["entryUrl"] = args.frontend_url

    if args.backend_url:
        manifest.setdefault("backend", {})
        manifest["backend"]["apiBaseUrl"] = args.backend_url
        manifest["backend"]["baseUrl"] = args.backend_url

    _require_authorization(manifest)
    _require_auth(manifest)

    payload = _build_registry_payload(
        manifest=manifest,
        environment=args.environment,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"Registry payload written to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())