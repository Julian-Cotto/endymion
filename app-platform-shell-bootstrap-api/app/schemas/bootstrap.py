from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BootstrapUser(BaseModel):
    id: str
    displayName: str
    email: str

    model_config = ConfigDict(extra="allow")


class BootstrapFrontend(BaseModel):
    entryUrl: str
    enabled: bool | None = None
    mountFunction: str | None = None

    model_config = ConfigDict(extra="allow")


class BootstrapBackend(BaseModel):
    apiBaseUrl: str
    enabled: bool | None = None
    healthEndpoint: str | None = None

    model_config = ConfigDict(extra="allow")


class BootstrapAuthorization(BaseModel):
    requiredPermissions: list[str] = Field(default_factory=list)
    requiredFlags: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")


class BootstrapAuth(BaseModel):
    mode: str

    model_config = ConfigDict(extra="allow")


class BootstrapFeature(BaseModel):
    featureKey: str
    route: str
    frontend: BootstrapFrontend
    backend: BootstrapBackend
    authorization: BootstrapAuthorization = Field(default_factory=BootstrapAuthorization)
    auth: BootstrapAuth

    model_config = ConfigDict(extra="allow")


class BootstrapMetadata(BaseModel):
    source: str
    generatedBy: str
    generatedAtUtc: str

    model_config = ConfigDict(extra="allow")


class BootstrapResponse(BaseModel):
    environment: str
    user: BootstrapUser
    permissions: list[str] = Field(default_factory=list)
    flags: dict[str, Any] = Field(default_factory=dict)
    features: list[BootstrapFeature] = Field(default_factory=list)
    metadata: BootstrapMetadata

    model_config = ConfigDict(extra="allow")