from __future__ import annotations

from datetime import UTC, datetime

from app.core.auth import AuthenticatedUser
from app.core.config import Settings, get_settings
from app.schemas.bootstrap import (
    BootstrapFeature,
    BootstrapMetadata,
    BootstrapResponse,
    BootstrapUser,
)
from app.schemas.registry_manifest import RegistryManifest
from app.schemas.runtime_features import (
    RuntimeFeature,
    RuntimeFeaturesResponse,
    RuntimeMetadata,
    RuntimeUser,
)
from app.services.appconfig_service import AppConfigFlagService
from app.services.cache import CacheBackend
from app.services.permission_mapper import has_permission
from app.services.permissions import PermissionService
from app.services.registry_client import RegistryClient
from app.services.registry_manifest_mapper import (
    registry_manifest_to_bootstrap_feature,
    registry_manifest_to_runtime_feature,
)


class BootstrapService:
    def __init__(
        self,
        registry_client: RegistryClient,
        flag_service: AppConfigFlagService,
        permission_service: PermissionService,
        cache: CacheBackend,
        cache_ttl_seconds: int,
        include_flag_prefixes: list[str],
        app_env: str,
        settings: Settings | None = None,
    ):
        self.registry_client = registry_client
        self.flag_service = flag_service
        self.permission_service = permission_service
        self.cache = cache
        self.cache_ttl_seconds = cache_ttl_seconds
        self.include_flag_prefixes = include_flag_prefixes
        self.app_env = app_env
        self.settings = settings or get_settings()

    async def build_bootstrap(self, user: AuthenticatedUser) -> BootstrapResponse:
        if self.settings.bootstrap_mode == "mock":
            return self._build_mock_bootstrap(user)

        return await self._build_registry_bootstrap(user)

    async def build_runtime_features(
        self,
        user: AuthenticatedUser,
    ) -> RuntimeFeaturesResponse:
        if self.settings.bootstrap_mode == "mock":
            return self._build_mock_runtime_features(user)

        return await self._build_registry_runtime_features(user)

    def _build_mock_bootstrap(self, user: AuthenticatedUser) -> BootstrapResponse:
        permissions = self.permission_service.get_permissions(user)

        all_features = [
            self._coerce_mock_feature(item) for item in self.settings.mock_features
        ]

        resolved_flags = self._build_mock_flags(all_features)

        features = [
            feature
            for feature in all_features
            if self._is_mock_feature_enabled(feature.featureKey)
            and self._is_authorized_for_feature(
                required_permissions=feature.authorization.requiredPermissions,
                required_flags=feature.authorization.requiredFlags,
                permissions=permissions,
                resolved_flags=resolved_flags,
            )
        ]

        return BootstrapResponse(
            environment=self.app_env,
            user=BootstrapUser(
                id=user.id,
                displayName=user.display_name,
                email=user.email,
            ),
            permissions=permissions,
            flags=self._filter_frontend_flags(resolved_flags),
            features=features,
            metadata=BootstrapMetadata(
                source="bootstrap-service-mock",
                generatedBy="shell-bootstrap-api",
                generatedAtUtc=datetime.now(UTC).isoformat(),
            ),
        )

    def _build_mock_runtime_features(
        self,
        user: AuthenticatedUser,
    ) -> RuntimeFeaturesResponse:
        permissions = self.permission_service.get_permissions(user)

        all_features = [
            self._coerce_mock_runtime_feature(item)
            for item in self.settings.mock_features
        ]

        resolved_flags = self._build_mock_runtime_flags(all_features)

        features = [
            feature
            for feature in all_features
            if self._is_mock_feature_enabled(feature.featureKey)
            and self._is_authorized_for_feature(
                required_permissions=feature.authorization.requiredPermissions,
                required_flags=feature.authorization.requiredFlags,
                permissions=permissions,
                resolved_flags=resolved_flags,
            )
        ]

        return RuntimeFeaturesResponse(
            environment=self.app_env,
            user=RuntimeUser(
                id=user.id,
                displayName=user.display_name,
                email=user.email,
            ),
            permissions=permissions,
            flags=self._filter_frontend_flags(resolved_flags),
            features=features,
            metadata=RuntimeMetadata(
                source="runtime-service-mock",
                generatedBy="shell-bootstrap-api",
                generatedAtUtc=datetime.now(UTC).isoformat(),
            ),
        )

    def _is_mock_feature_enabled(self, feature_key: str) -> bool:
        if not self.include_flag_prefixes:
            return True

        feature_prefix = f"{feature_key}."
        return any(
            feature_prefix.startswith(prefix)
            for prefix in self.include_flag_prefixes
        )

    def _build_mock_flags(self, features: list[BootstrapFeature]) -> dict[str, bool]:
        flags: dict[str, bool] = {"shell.debug": True}

        for feature in features:
            flags[f"{feature.featureKey}.enabled"] = True

        return flags

    def _build_mock_runtime_flags(
        self,
        features: list[RuntimeFeature],
    ) -> dict[str, bool]:
        flags: dict[str, bool] = {"shell.debug": True}

        for feature in features:
            flags[f"{feature.featureKey}.enabled"] = True

        return flags

    def _coerce_mock_feature(self, raw: dict) -> BootstrapFeature:
        return BootstrapFeature.model_validate(
            {
                "featureKey": raw["featureKey"],
                "displayName": raw.get("displayName"),
                "route": raw["route"],
                "version": raw.get("version", "local"),
                "nav": raw.get("nav"),
                "frontend": raw["frontend"],
                "backend": raw["backend"],
                "authorization": {
                    "requiredPermissions": raw.get("authorization", {}).get(
                        "requiredPermissions",
                        [],
                    ),
                    "requiredFlags": raw.get("authorization", {}).get(
                        "requiredFlags",
                        [],
                    ),
                },
                "auth": raw.get("auth")
                or {
                    "mode": "mock",
                    "required": False,
                    "shellAuthRequired": False,
                    "tokenForwarding": False,
                    "allowedDevModes": ["mock"],
                    "roles": [],
                },
            }
        )

    def _coerce_mock_runtime_feature(self, raw: dict) -> RuntimeFeature:
        return RuntimeFeature.model_validate(
            {
                "featureKey": raw["featureKey"],
                "displayName": raw.get("displayName"),
                "route": raw["route"],
                "version": raw.get("version", "local"),
                "nav": raw.get("nav"),
                "frontend": raw["frontend"],
                "backend": raw["backend"],
                "authorization": {
                    "requiredPermissions": raw.get("authorization", {}).get(
                        "requiredPermissions",
                        [],
                    ),
                    "requiredFlags": raw.get("authorization", {}).get(
                        "requiredFlags",
                        [],
                    ),
                },
                "auth": raw.get("auth")
                or {
                    "mode": "mock",
                    "required": False,
                    "shellAuthRequired": False,
                    "tokenForwarding": False,
                    "allowedDevModes": ["mock"],
                    "roles": [],
                },
            }
        )

    async def _build_registry_bootstrap(
        self,
        user: AuthenticatedUser,
    ) -> BootstrapResponse:
        permissions = self.permission_service.get_permissions(user)
        bootstrap_cache_key = self._build_bootstrap_cache_key(user.id, permissions)

        async def factory():
            manifests = await self.registry_client.get_active_features(self.app_env)

            required_flags = self._collect_required_flags(manifests)
            resolved_flags = await self.flag_service.resolve_flags(required_flags)

            visible_manifests = [
                manifest
                for manifest in manifests
                if self._is_visible(manifest, permissions, resolved_flags)
            ]

            frontend_flags = self._filter_frontend_flags(resolved_flags)

            return BootstrapResponse(
                environment=self.app_env,
                user=BootstrapUser(
                    id=user.id,
                    displayName=user.display_name,
                    email=user.email,
                ),
                permissions=permissions,
                flags=frontend_flags,
                features=[
                    registry_manifest_to_bootstrap_feature(
                        RegistryManifest.model_validate(manifest)
                    )
                    for manifest in visible_manifests
                ],
                metadata=BootstrapMetadata(
                    source="bootstrap-service-registry",
                    generatedBy="shell-bootstrap-api",
                    generatedAtUtc=datetime.now(UTC).isoformat(),
                ),
            ).model_dump()

        payload = await self.cache.get_or_set(
            bootstrap_cache_key,
            max(1, min(15, self.cache_ttl_seconds)),
            factory,
        )

        return BootstrapResponse(**payload)

    async def _build_registry_runtime_features(
        self,
        user: AuthenticatedUser,
    ) -> RuntimeFeaturesResponse:
        permissions = self.permission_service.get_permissions(user)
        runtime_cache_key = self._build_runtime_cache_key(user.id, permissions)

        async def factory():
            manifests = await self.registry_client.get_active_features(self.app_env)

            required_flags = self._collect_required_flags(manifests)
            resolved_flags = await self.flag_service.resolve_flags(required_flags)

            visible_manifests = [
                manifest
                for manifest in manifests
                if self._is_visible(manifest, permissions, resolved_flags)
            ]

            frontend_flags = self._filter_frontend_flags(resolved_flags)

            return RuntimeFeaturesResponse(
                environment=self.app_env,
                user=RuntimeUser(
                    id=user.id,
                    displayName=user.display_name,
                    email=user.email,
                ),
                permissions=permissions,
                flags=frontend_flags,
                features=[
                    registry_manifest_to_runtime_feature(
                        RegistryManifest.model_validate(manifest)
                    )
                    for manifest in visible_manifests
                ],
                metadata=RuntimeMetadata(
                    source="runtime-service-registry",
                    generatedBy="shell-bootstrap-api",
                    generatedAtUtc=datetime.now(UTC).isoformat(),
                ),
            ).model_dump()

        payload = await self.cache.get_or_set(
            runtime_cache_key,
            max(1, min(15, self.cache_ttl_seconds)),
            factory,
        )

        return RuntimeFeaturesResponse(**payload)

    def _build_bootstrap_cache_key(self, user_id: str, permissions: list[str]) -> str:
        joined_permissions = "|".join(sorted(set(permissions)))
        return f"bootstrap:v3:{self.app_env}:{user_id}:{joined_permissions}"

    def _build_runtime_cache_key(self, user_id: str, permissions: list[str]) -> str:
        joined_permissions = "|".join(sorted(set(permissions)))
        return f"runtime:v3:{self.app_env}:{user_id}:{joined_permissions}"

    def _collect_required_flags(self, manifests: list[dict]) -> list[str]:
        flags = set()

        for manifest in manifests:
            for flag in manifest.get("authorization", {}).get("requiredFlags", []):
                flags.add(flag)

        return sorted(flags)

    def _filter_frontend_flags(self, resolved_flags: dict[str, bool]) -> dict[str, bool]:
        if not self.include_flag_prefixes:
            return resolved_flags

        return {
            key: value
            for key, value in resolved_flags.items()
            if any(key.startswith(prefix) for prefix in self.include_flag_prefixes)
        }

    def _is_authorized_for_feature(
        self,
        required_permissions: list[str],
        required_flags: list[str],
        permissions: list[str],
        resolved_flags: dict[str, bool],
    ) -> bool:
        return has_permission(permissions, required_permissions) and all(
            resolved_flags.get(flag, False) for flag in required_flags
        )

    def _is_visible(
        self,
        manifest: dict,
        permissions: list[str],
        resolved_flags: dict[str, bool],
    ) -> bool:
        auth = manifest.get("authorization", {})

        required_permissions = auth.get("requiredPermissions", [])
        required_flags = auth.get("requiredFlags", [])

        return self._is_authorized_for_feature(
            required_permissions=required_permissions,
            required_flags=required_flags,
            permissions=permissions,
            resolved_flags=resolved_flags,
        )