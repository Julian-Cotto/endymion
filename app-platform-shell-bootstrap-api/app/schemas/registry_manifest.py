from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class RegistryManifestNav(BaseModel):
    label: str
    icon: str | None = None
    group: str | None = None
    order: int | None = None

    model_config = ConfigDict(extra="allow")


class RegistryManifestFrontend(BaseModel):
    enabled: bool = True
    entryUrl: str
    mountFunction: str = "mount"

    model_config = ConfigDict(extra="allow")


class RegistryManifestBackend(BaseModel):
    enabled: bool = True
    apiBaseUrl: str
    healthEndpoint: str | None = None

    model_config = ConfigDict(extra="allow")


class RegistryManifestAuthorization(BaseModel):
    requiredPermissions: list[str] = Field(default_factory=list)
    requiredFlags: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")


class RegistryManifestAuth(BaseModel):
    required: bool = True
    mode: str = "mock"
    shellAuthRequired: bool = True
    tokenForwarding: bool = False
    tokenStrategy: str | None = None
    allowedDevModes: list[str] = Field(default_factory=list)
    roles: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")


class RegistryManifest(BaseModel):
    # Core identity
    featureKey: str
    displayName: str
    route: str
    version: str

    # Optional (tests may omit this)
    nav: RegistryManifestNav | None = None

    # Required runtime sections
    frontend: RegistryManifestFrontend
    backend: RegistryManifestBackend

    # Optional sections
    authorization: RegistryManifestAuthorization = Field(
        default_factory=RegistryManifestAuthorization
    )
    auth: RegistryManifestAuth = Field(
        default_factory=RegistryManifestAuth
    )

    # Registry-only fields (ignored but accepted)
    manifestVersion: str | None = None
    environment: str | None = None
    compatibility: dict | None = None
    metadata: dict | None = None

    model_config = ConfigDict(extra="allow")