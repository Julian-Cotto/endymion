from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Feature, Release, ReleaseStatus
from app.schemas.manifest import ReleaseManifestIn


class ReleaseService:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_feature(self, manifest: ReleaseManifestIn) -> Feature:
        feature = self.db.scalar(
            select(Feature).where(Feature.feature_key == manifest.featureKey)
        )

        if feature:
            return feature

        feature = Feature(
            feature_key=manifest.featureKey,
            display_name=manifest.displayName,
            owner_team=manifest.metadata.ownerTeam,
        )
        self.db.add(feature)
        self.db.flush()
        return feature

    def publish_release(self, manifest: ReleaseManifestIn) -> Release:
        feature = self.get_or_create_feature(manifest)

        existing = self.db.scalar(
            select(Release).where(
                Release.feature_id == feature.id,
                Release.version == manifest.version,
                Release.environment == manifest.environment,
            )
        )

        if existing:
            return existing

        release = Release(
            feature_id=feature.id,
            manifest_version=manifest.manifestVersion,
            version=manifest.version,
            environment=manifest.environment,
            status=ReleaseStatus.candidate,
            route=manifest.route,
            entry_url=str(manifest.frontend.entryUrl),
            api_base_url=str(manifest.backend.apiBaseUrl),
            nav_json=manifest.nav.model_dump(),
            authorization_json=manifest.authorization.model_dump(),
            auth_json=manifest.auth.model_dump(),
            compatibility_json=manifest.compatibility.model_dump(),
            metadata_json=manifest.metadata.model_dump(),
        )

        self.db.add(release)
        self.db.flush()
        return release