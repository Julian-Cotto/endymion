from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_release_write
from app.core.config import get_settings
from app.core.security import Principal, require_feature_scope
from app.db.session import get_db
from app.schemas.manifest import ReleaseManifestIn
from app.schemas.release import ReleasePublishResponse
from app.services.audit_service import AuditService
from app.services.manifest_validator import ManifestValidationError, ManifestValidator
from app.services.release_service import ReleaseService

router = APIRouter(prefix="/api/releases", tags=["releases"])


@router.post("", response_model=ReleasePublishResponse)
def publish_release(
    manifest: ReleaseManifestIn,
    principal: Principal = Depends(require_release_write),
    db: Session = Depends(get_db),
):
    settings = get_settings()

    require_feature_scope(principal, manifest.featureKey)

    validator = ManifestValidator(
        allowed_frontend_hosts=settings.frontend_hosts_set(),
        allowed_api_hosts=settings.api_hosts_set(),
    )

    try:
        validator.validate(manifest)
    except ManifestValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    service = ReleaseService(db)
    audit = AuditService(db)

    release = service.publish_release(manifest)

    audit.write(
        action="publish_release",
        feature_key=manifest.featureKey,
        version=manifest.version,
        environment=manifest.environment,
        actor=principal.subject,
        details={"route": manifest.route},
    )

    db.commit()

    return ReleasePublishResponse(
        id=str(release.id),
        featureKey=manifest.featureKey,
        version=release.version,
        environment=release.environment,
        status=release.status.value,
    )
