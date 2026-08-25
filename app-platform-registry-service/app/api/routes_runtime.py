from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_runtime_read
from app.core.security import Principal
from app.db.session import get_db
from app.schemas.runtime import RuntimeFeaturesResponse
from app.services.runtime_service import RuntimeService

router = APIRouter(prefix="/api/runtime", tags=["runtime"])


@router.get("/features", response_model=RuntimeFeaturesResponse)
def get_features(
    environment: str,
    principal: Principal = Depends(require_runtime_read),
    db: Session = Depends(get_db),
):
    service = RuntimeService(db)
    return RuntimeFeaturesResponse(
        environment=environment,
        features=service.get_active_manifests(environment),
    )
