from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class RuntimeUser(BaseModel):
    id: str
    displayName: str
    email: str | None = None

    model_config = ConfigDict(extra="allow")


class RuntimeFeatureNav(BaseModel):
    label: str
    icon: str
    group: str | None = None
    order: int | None = None

    model_config = ConfigDict(extra="allow")


class RuntimeFeatureFrontend(BaseModel):
    entryUrl: str
    enabled: bool | None = None
    mountFunction: str | None = None

    model_config = ConfigDict(extra="allow")


class RuntimeFeatureBackend(BaseModel):
    apiBaseUrl: str
    enabled: bool | None = None
    healthEndpoint: str | None = None

    model_config = ConfigDict(extra="allow")


class RuntimeFeatureAuthorization(BaseModel):
    requiredPermissions: list[str] = Field(default_factory=list)
    requiredFlags: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")


class RuntimeFeatureAuth(BaseModel):
    mode: str

    model_config = ConfigDict(extra="allow")


class RuntimeFeature(BaseModel):
    featureKey: str
    displayName: str | None = None
    route: str
    version: str | None = None
    nav: RuntimeFeatureNav | None = None
    frontend: RuntimeFeatureFrontend
    backend: RuntimeFeatureBackend
    authorization: RuntimeFeatureAuthorization = Field(default_factory=RuntimeFeatureAuthorization)
    auth: RuntimeFeatureAuth | None = None

    model_config = ConfigDict(extra="allow")


class RuntimeMetadata(BaseModel):
    source: str
    generatedBy: str
    generatedAtUtc: str

    model_config = ConfigDict(extra="allow")


class RuntimeFeaturesResponse(BaseModel):
    environment: str
    user: RuntimeUser
    permissions: list[str] = Field(default_factory=list)
    flags: dict[str, bool] = Field(default_factory=dict)
    features: list[RuntimeFeature] = Field(default_factory=list)
    metadata: RuntimeMetadata

    model_config = ConfigDict(extra="allow")