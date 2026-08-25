from pydantic import BaseModel

from app.schemas.manifest import ReleaseManifestIn


class RuntimeFeaturesResponse(BaseModel):
    environment: str
    features: list[ReleaseManifestIn]
