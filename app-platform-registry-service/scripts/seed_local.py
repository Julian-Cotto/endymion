from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import Feature, Release, ReleaseStatus
from app.db.session import SessionLocal


LOCAL_MANIFESTS = [
    {
        "feature_key": "asset-inventory",
        "display_name": "IT Asset Inventory",
        "owner_team": "platform",
        "version": "1.0.0",
        "environment": "local",
        "route": "/inventory/it",
        "entry_url": "/_mfe/asset-inventory/src/bootstrap-entry.tsx",
        "api_base_url": "/api/inventory/it",
        "nav_json": {
            "label": "IT Inventory",
            "icon": "package",
            "group": None,
            "order": 10,
        },
        "authorization_json": {
            "requiredPermissions": ["asset-inventory.view"],
            "requiredFlags": ["asset-inventory.enabled"],
        },
        "compatibility_json": {
            "shellContractMin": "v1",
            "shellContractMax": "v1",
        },
        "metadata_json": {
            "ownerTeam": "platform",
            "frontend": {
                "type": "module",
                "enabled": True,
                "mountFunction": "mount",
                "basePath": "/inventory/it",
            },
            "backend": {
                "enabled": True,
                "healthEndpoint": "/api/inventory/it/health",
            },
        },
    },
    {
        "feature_key": "continued-education",
        "display_name": "Continued Education",
        "owner_team": "platform",
        "version": "0.1.0",
        "environment": "local",
        "route": "/education/continued-ed",
        "entry_url": "/_mfe/continued-education/src/bootstrap-entry.tsx",
        "api_base_url": "/api/education/continued-ed",
        "nav_json": {
            "label": "Continued Education",
            "icon": "graduation-cap",
            "group": None,
            "order": 20,
        },
        "authorization_json": {
            "requiredPermissions": ["continued-education.view"],
            "requiredFlags": ["continued-education.enabled"],
        },
        "compatibility_json": {
            "shellContractMin": "v1",
            "shellContractMax": "v1",
        },
        "metadata_json": {
            "ownerTeam": "platform",
            "frontend": {
                "type": "module",
                "enabled": True,
                "mountFunction": "mount",
                "basePath": "/education/continued-ed",
            },
            "backend": {
                "enabled": True,
                "healthEndpoint": "/api/education/continued-ed/health",
            },
        },
    },
    {
        "feature_key": "document-compliance",
        "display_name": "Document Compliance",
        "owner_team": "platform",
        "version": "0.1.0",
        "environment": "local",
        "route": "/document-compliance",
        "entry_url": "/_mfe/document-compliance/src/bootstrap-entry.tsx",
        "api_base_url": "/api/document-compliance",
        "nav_json": {
            "label": "Document Compliance",
            "icon": "file-check",
            "group": None,
            "order": 30,
        },
        "authorization_json": {
            "requiredPermissions": ["document-compliance.view"],
            "requiredFlags": ["document-compliance.enabled"],
        },
        "compatibility_json": {
            "shellContractMin": "v1",
            "shellContractMax": "v1",
        },
        "metadata_json": {
            "ownerTeam": "platform",
            "frontend": {
                "type": "module",
                "enabled": True,
                "mountFunction": "mount",
                "basePath": "/document-compliance",
            },
            "backend": {
                "enabled": True,
                "healthEndpoint": "/api/document-compliance/health",
            },
        },
    },
]


def upsert_feature(db: Session, item: dict) -> Feature:
    feature = (
        db.query(Feature)
        .filter(Feature.feature_key == item["feature_key"])
        .one_or_none()
    )

    if feature is None:
        feature = Feature(
            feature_key=item["feature_key"],
            display_name=item["display_name"],
            owner_team=item["owner_team"],
        )
        db.add(feature)
        db.flush()

    return feature


def upsert_active_release(db: Session, feature: Feature, item: dict) -> None:
    existing = (
        db.query(Release)
        .filter(
            Release.feature_id == feature.id,
            Release.version == item["version"],
            Release.environment == item["environment"],
        )
        .one_or_none()
    )

    # deactivate existing active
    (
        db.query(Release)
        .filter(
            Release.feature_id == feature.id,
            Release.environment == item["environment"],
            Release.status == ReleaseStatus.active,
        )
        .update({"status": ReleaseStatus.inactive})
    )

    if existing is None:
        existing = Release(
            feature_id=feature.id,
            version=item["version"],
            environment=item["environment"],
            manifest_version="1.0",
            status=ReleaseStatus.active,
            route=item["route"],                 # ✅ set BEFORE flush
            entry_url=item["entry_url"],
            api_base_url=item["api_base_url"],
            nav_json=item["nav_json"],
            authorization_json=item["authorization_json"],
            compatibility_json=item["compatibility_json"],
            metadata_json=item["metadata_json"],
            is_deleted=False,
        )
        db.add(existing)
        db.flush()
    else:
        existing.manifest_version = "1.0"
        existing.status = ReleaseStatus.active
        existing.route = item["route"]
        existing.entry_url = item["entry_url"]
        existing.api_base_url = item["api_base_url"]
        existing.nav_json = item["nav_json"]
        existing.authorization_json = item["authorization_json"]
        existing.compatibility_json = item["compatibility_json"]
        existing.metadata_json = item["metadata_json"]
        existing.is_deleted = False


def main() -> None:
    db = SessionLocal()
    try:
        for item in LOCAL_MANIFESTS:
            feature = upsert_feature(db, item)
            upsert_active_release(db, feature, item)

        db.commit()
        print("Seeded local registry features: " + ", ".join(m["feature_key"] for m in LOCAL_MANIFESTS))
    finally:
        db.close()


if __name__ == "__main__":
    main()