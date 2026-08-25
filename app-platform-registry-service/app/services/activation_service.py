from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db.models import Feature, Release, ReleaseStatus


class ActivationService:
    def __init__(self, db: Session):
        self.db = db

    def activate_release(self, feature_key: str, version: str, environment: str) -> Release:
        feature = self.db.scalar(
            select(Feature).where(Feature.feature_key == feature_key)
        )
        if not feature:
            raise ValueError(f"feature not found: {feature_key}")

        target = self.db.scalar(
            select(Release).where(
                Release.feature_id == feature.id,
                Release.version == version,
                Release.environment == environment,
                Release.is_deleted.is_(False),
            )
        )
        if not target:
            raise ValueError("target release not found")

        if target.status.value == "retired":
            raise ValueError("retired releases cannot be activated")

        self.db.execute(
            update(Release)
            .where(
                Release.feature_id == feature.id,
                Release.environment == environment,
                Release.status == ReleaseStatus.active,
            )
            .values(status=ReleaseStatus.inactive)
        )

        target.status = ReleaseStatus.active
        target.activated_at = datetime.utcnow()
        self.db.flush()

        return target
