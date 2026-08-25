from __future__ import annotations

from app.schemas.bootstrap import BootstrapFeature
from app.schemas.runtime_features import RuntimeFeature
from app.schemas.registry_manifest import RegistryManifest


DEFAULT_AUTH = {
    "mode": "mock",
    "required": False,
    "shellAuthRequired": False,
    "tokenForwarding": False,
    "allowedDevModes": ["mock"],
    "roles": [],
}


def _nav_or_default(manifest: RegistryManifest):
    if manifest.nav:
        return manifest.nav.model_dump()

    return {
        "label": manifest.displayName,
        "icon": None,
        "group": None,
        "order": None,
    }


def _auth_or_default(manifest: RegistryManifest):
    if manifest.auth:
        return manifest.auth.model_dump()

    return DEFAULT_AUTH


def registry_manifest_to_bootstrap_feature(
    manifest: RegistryManifest,
) -> BootstrapFeature:
    return BootstrapFeature.model_validate(
        {
            "featureKey": manifest.featureKey,
            "displayName": manifest.displayName,
            "route": manifest.route,
            "version": manifest.version,
            "nav": _nav_or_default(manifest),
            "frontend": manifest.frontend.model_dump(),
            "backend": manifest.backend.model_dump(),
            "authorization": manifest.authorization.model_dump(),
            "auth": _auth_or_default(manifest),
        }
    )


def registry_manifest_to_runtime_feature(
    manifest: RegistryManifest,
) -> RuntimeFeature:
    return RuntimeFeature.model_validate(
        {
            "featureKey": manifest.featureKey,
            "displayName": manifest.displayName,
            "route": manifest.route,
            "version": manifest.version,
            "nav": _nav_or_default(manifest),
            "frontend": manifest.frontend.model_dump(),
            "backend": manifest.backend.model_dump(),
            "authorization": manifest.authorization.model_dump(),
            "auth": _auth_or_default(manifest),
        }
    )