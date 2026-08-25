from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ReleaseStatus(str, enum.Enum):
    draft = "draft"
    candidate = "candidate"
    active = "active"
    inactive = "inactive"
    retired = "retired"
    failed = "failed"


class Feature(Base):
    __tablename__ = "features"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    feature_key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(200))
    owner_team: Mapped[str] = mapped_column(String(200))
    repo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    releases: Mapped[list["Release"]] = relationship(back_populates="feature")


class Release(Base):
    __tablename__ = "releases"
    __table_args__ = (
        UniqueConstraint("feature_id", "version", "environment", name="uq_release_feature_version_env"),
        Index("ix_release_feature_env_status", "environment", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    feature_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("features.id"), nullable=False)

    manifest_version: Mapped[str] = mapped_column(String(20), default="1.0")
    version: Mapped[str] = mapped_column(String(50))
    environment: Mapped[str] = mapped_column(String(50))
    status: Mapped[ReleaseStatus] = mapped_column(Enum(ReleaseStatus), default=ReleaseStatus.candidate)

    route: Mapped[str] = mapped_column(String(200))
    entry_url: Mapped[str] = mapped_column(String(1000))
    api_base_url: Mapped[str] = mapped_column(String(1000))

    nav_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    authorization_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    auth_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    compatibility_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)

    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    feature: Mapped["Feature"] = relationship(back_populates="releases")


class Audit(Base):
    __tablename__ = "audits"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action: Mapped[str] = mapped_column(String(100), index=True)
    feature_key: Mapped[str] = mapped_column(String(100), index=True)
    version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    environment: Mapped[str | None] = mapped_column(String(50), nullable=True)
    actor: Mapped[str] = mapped_column(String(300))
    details_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)