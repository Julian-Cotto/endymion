from sqlalchemy.orm import Session

from app.db.models import Audit


class AuditService:
    def __init__(self, db: Session):
        self.db = db

    def write(
        self,
        action: str,
        feature_key: str,
        actor: str,
        version: str | None = None,
        environment: str | None = None,
        details: dict | None = None,
    ) -> None:
        row = Audit(
            action=action,
            feature_key=feature_key,
            version=version,
            environment=environment,
            actor=actor,
            details_json=details or {},
        )
        self.db.add(row)
        self.db.flush()
