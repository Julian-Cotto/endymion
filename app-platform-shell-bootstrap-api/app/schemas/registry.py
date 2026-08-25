from pydantic import BaseModel, Field


class NavSchema(BaseModel):
    label: str
    icon: str | None = None
    group: str | None = None
    order: int | None = None


class FrontendSchema(BaseModel):
    entryUrl: str


class BackendSchema(BaseModel):
    apiBaseUrl: str


class AuthorizationSchema(BaseModel):
    requiredPermissions: list[str] = Field(default_factory=list)
    requiredFlags: list[str] = Field(default_factory=list)


class RuntimeFeatureManifest(BaseModel):
    featureKey: str
    displayName: str
    route: str
    version: str
    nav: NavSchema | None = None
    frontend: FrontendSchema
    backend: BackendSchema
    authorization: AuthorizationSchema = Field(default_factory=AuthorizationSchema)


class RuntimeFeaturesResponse(BaseModel):
    environment: str
    features: list[RuntimeFeatureManifest]
