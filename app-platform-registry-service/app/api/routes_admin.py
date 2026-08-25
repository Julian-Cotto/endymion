from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_release_activate
from app.core.security import Principal
from app.db.session import get_db
from app.schemas.release import ActivationResponse
from app.services.activation_service import ActivationService
from app.services.audit_service import AuditService

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post(
    "/features/{feature_key}/versions/{version}/activate",
    response_model=ActivationResponse,
)
def activate_release(
    feature_key: str,
    version: str,
    environment: str,
    principal: Principal = Depends(require_release_activate),
    db: Session = Depends(get_db),
):
    service = ActivationService(db)
    audit = AuditService(db)

    try:
        release = service.activate_release(feature_key, version, environment)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    audit.write(
        action="activate_release",
        feature_key=feature_key,
        version=version,
        environment=environment,
        actor=principal.subject,
    )

    db.commit()

    return ActivationResponse(
        featureKey=feature_key,
        version=release.version,
        environment=release.environment,
        status=release.status.value,
        activatedAt=release.activated_at.isoformat() if release.activated_at else None,
    )
