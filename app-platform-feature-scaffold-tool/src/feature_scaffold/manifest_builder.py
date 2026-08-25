from __future__ import annotations

import json

from .models import NormalizedScaffoldConfig


def _normalize_auth_mode(value: str | None) -> str:
    value = (value or "mock").strip().lower()

    if value not in {"entra", "mock", "none"}:
        return "mock"

    return value


def _normalize_token_strategy(value: str | None, auth_mode: str) -> str:
    value = (value or "").strip()

    if value == "bearer":
        return "forwarded-bearer"

    if value in {"forwarded-bearer", "shell-session", "none"}:
        return value

    if auth_mode == "entra":
        return "forwarded-bearer"

    return "none"


def build_feature_manifest(config: NormalizedScaffoldConfig) -> str:
    names = config.names
    version = config.manifest_version

    required_permissions = [f"{names.feature_key}.view"]
    required_flags = [f"{names.feature_key}.enabled"]

    auth_mode = _normalize_auth_mode(config.auth_mode)
    token_strategy = _normalize_token_strategy(config.backend_token_strategy, auth_mode)

    shell_auth_required = config.auth_shell_auth_required
    token_forwarding = config.auth_token_forwarding

    if auth_mode == "entra":
        shell_auth_required = True
        token_forwarding = True
        token_strategy = "forwarded-bearer"

    if auth_mode == "none":
        shell_auth_required = False
        token_forwarding = False
        token_strategy = "none"

    manifest = {
        "manifestVersion": "1.0",
        "featureKey": names.feature_key,
        "displayName": names.display_name,
        "description": names.description,
        "basePath": names.base_path,
        "route": names.base_path,
        "navigation": {
            "label": names.display_name,
            "icon": "package",
        },
        "nav": {
            "label": names.display_name,
            "icon": "package",
            "group": None,
            "order": 0,
        },
        "version": version,
        "frontend": {
            "enabled": config.frontend_enabled,
            "type": "module",
            "entryStrategy": "vite-dynamic-import",
            "entryUrl": f"/features/{names.feature_key}/assets/bootstrap.js",
            "mountFunction": "mount",
            "integrity": None,
            "basePath": names.base_path,
        },
        "backend": {
            "enabled": config.backend_enabled,
            "baseUrl": names.api_base_path,
            "apiBaseUrl": names.api_base_path,
            "healthEndpoint": f"{names.api_base_path}/health",
        },
        "authorization": {
            "requiredPermissions": required_permissions,
            "requiredFlags": required_flags,
        },
        "auth": {
            "required": auth_mode != "none",
            "mode": auth_mode,
            "shellAuthRequired": shell_auth_required,
            "tokenForwarding": token_forwarding,
            "tokenStrategy": token_strategy,
            "allowedDevModes": config.auth_allowed_dev_modes or ["mock"],
            "roles": [],
        },
        "registry": {
            "enabled": config.registry_enabled,
            "mode": config.registry_mode,
        },
        "compatibility": {
            "shellContractMin": None,
            "shellContractMax": None,
        },
        "metadata": {
            "ownerTeam": "platform",
            "commitSha": None,
            "buildId": None,
            "releaseDate": None,
        },
        "events": {
            "publishes": [e.name for e in config.published_events],
            "consumes": [e.name for e in config.consumed_events],
        },
        "workers": {
            "scheduledJobs": [j.name for j in config.scheduled_jobs],
            "eventDrivenJobs": [w.name for w in config.event_driven_jobs],
            "eventListeners": [listener.name for listener in config.event_listeners],
        },
    }

    return json.dumps(manifest, indent=2) + "\n"