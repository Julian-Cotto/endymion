from __future__ import annotations

import pytest
from sqlalchemy import text

from app.db.models import ReleaseStatus
from app.db.session import SessionLocal
from app.schemas.manifest import ReleaseManifestIn
from app.services.activation_service import ActivationService
from app.services.audit_service import AuditService
from app.services.release_service import ReleaseService
from app.services.runtime_service import RuntimeService

from tests.factories import sample_manifest_dict


def _manifest(**kwargs) -> ReleaseManifestIn:
    return ReleaseManifestIn.model_validate(sample_manifest_dict(**kwargs))


def test_release_service_publish_idempotent(db_session):
    svc = ReleaseService(db_session)
    m = _manifest()
    r1 = svc.publish_release(m)
    r2 = svc.publish_release(m)
    assert r1.id == r2.id
    assert r1.auth_json["mode"] == "entra"
    db_session.commit()


def test_release_service_persists_auth_json(db_session):
    svc = ReleaseService(db_session)
    rel = svc.publish_release(_manifest())

    assert rel.auth_json == {
        "required": True,
        "mode": "entra",
        "shellAuthRequired": True,
        "tokenForwarding": True,
        "tokenStrategy": "forwarded-bearer",
        "allowedDevModes": ["mock"],
        "roles": [],
    }


def test_activation_service_happy_path(db_session):
    rel_svc = ReleaseService(db_session)
    m = _manifest()
    rel = rel_svc.publish_release(m)
    assert rel.status == ReleaseStatus.candidate

    act = ActivationService(db_session)
    activated = act.activate_release("orders", "1.0.0", "local")
    assert activated.status == ReleaseStatus.active
    assert activated.activated_at is not None
    db_session.commit()


def test_activation_feature_not_found(db_session):
    with pytest.raises(ValueError, match="feature not found"):
        ActivationService(db_session).activate_release("missing", "1.0.0", "local")


def test_activation_release_not_found(db_session):
    rel_svc = ReleaseService(db_session)
    rel_svc.publish_release(_manifest())
    db_session.commit()

    with pytest.raises(ValueError, match="target release not found"):
        ActivationService(db_session).activate_release("orders", "9.9.9", "local")


def test_activation_retired_blocked(db_session):
    rel_svc = ReleaseService(db_session)
    rel = rel_svc.publish_release(_manifest())
    rel.status = ReleaseStatus.retired
    db_session.flush()

    with pytest.raises(ValueError, match="retired"):
        ActivationService(db_session).activate_release("orders", "1.0.0", "local")


def test_runtime_service_active_manifests(db_session):
    rel_svc = ReleaseService(db_session)
    rel = rel_svc.publish_release(_manifest())
    rel.status = ReleaseStatus.active
    db_session.flush()

    rt = RuntimeService(db_session)
    manifests = rt.get_active_manifests("local")
    assert len(manifests) == 1
    assert manifests[0].featureKey == "orders"
    assert str(manifests[0].frontend.entryUrl).startswith("http://localhost:3200")
    assert manifests[0].auth.mode == "entra"
    assert manifests[0].auth.tokenForwarding is True


def test_runtime_service_empty_environment(db_session):
    assert RuntimeService(db_session).get_active_manifests("prod") == []


def test_runtime_service_coerces_non_dict_frontend_metadata(db_session):
    rel_svc = ReleaseService(db_session)
    rel = rel_svc.publish_release(_manifest())
    rel.status = ReleaseStatus.active
    rel.metadata_json = {"frontend": "not-a-dict", "ownerTeam": "platform"}
    db_session.flush()

    manifests = RuntimeService(db_session).get_active_manifests("local")
    assert len(manifests) == 1
    assert manifests[0].frontend.basePath == "/orders"


def test_runtime_service_coerces_non_dict_root_metadata(db_session):
    rel_svc = ReleaseService(db_session)
    rel = rel_svc.publish_release(_manifest())
    rel.status = ReleaseStatus.active
    rel.metadata_json = ["not", "a", "dict"]  # type: ignore[assignment]
    db_session.flush()

    manifests = RuntimeService(db_session).get_active_manifests("local")
    assert len(manifests) == 1
    assert manifests[0].metadata.ownerTeam == "Orders"


def test_session_local_opens_connection(postgres_engine):
    s = SessionLocal()
    try:
        assert s.execute(text("SELECT 1")).scalar_one() == 1
    finally:
        s.close()


def test_audit_service_write(db_session):
    AuditService(db_session).write(
        action="test_action",
        feature_key="orders",
        actor="tester",
        version="1.0.0",
        environment="local",
        details={"k": "v"},
    )
    db_session.commit()