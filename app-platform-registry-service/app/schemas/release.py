from pydantic import BaseModel


class ReleasePublishResponse(BaseModel):
    id: str
    featureKey: str
    version: str
    environment: str
    status: str


class ActivationResponse(BaseModel):
    featureKey: str
    version: str
    environment: str
    status: str
    activatedAt: str | None = None
