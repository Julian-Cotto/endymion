import re
from urllib.parse import urlparse

from app.schemas.manifest import ReleaseManifestIn


SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+([\-+][A-Za-z0-9\.\-]+)?$")
PERMISSION_PATTERN = re.compile(r"^[a-z0-9-]+\.[a-z0-9-]+$")
FLAG_PATTERN = re.compile(r"^[a-z0-9-]+\.[a-z0-9-]+$")


class ManifestValidationError(Exception):
    pass


class ManifestValidator:
    def __init__(self, allowed_frontend_hosts: set[str], allowed_api_hosts: set[str]):
        self.allowed_frontend_hosts = allowed_frontend_hosts
        self.allowed_api_hosts = allowed_api_hosts

    def validate(self, manifest: ReleaseManifestIn) -> None:
        if not SEMVER_PATTERN.match(manifest.version):
            raise ManifestValidationError("version must be valid semver")

        frontend_host = urlparse(str(manifest.frontend.entryUrl)).hostname
        api_host = urlparse(str(manifest.backend.apiBaseUrl)).hostname

        if frontend_host not in self.allowed_frontend_hosts:
            raise ManifestValidationError(f"frontend host not allowed: {frontend_host}")

        if api_host not in self.allowed_api_hosts:
            raise ManifestValidationError(f"api host not allowed: {api_host}")

        if manifest.frontend.type != "module":
            raise ManifestValidationError("only frontend.type='module' is supported")

        self._validate_authorization(manifest)

    def _validate_authorization(self, manifest: ReleaseManifestIn) -> None:
        required_permissions = manifest.authorization.requiredPermissions
        required_flags = manifest.authorization.requiredFlags

        if not required_permissions:
            raise ManifestValidationError(
                "authorization.requiredPermissions must not be empty"
            )

        if not required_flags:
            raise ManifestValidationError(
                "authorization.requiredFlags must not be empty"
            )

        for permission in required_permissions:
            if not PERMISSION_PATTERN.match(permission):
                raise ManifestValidationError(
                    f"invalid authorization permission: {permission}"
                )

        for flag in required_flags:
            if not FLAG_PATTERN.match(flag):
                raise ManifestValidationError(
                    f"invalid authorization flag: {flag}"
                )