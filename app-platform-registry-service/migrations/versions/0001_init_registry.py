"""init registry schema

Revision ID: 0001_init_registry
Revises:
Create Date: 2026-03-20 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_init_registry"
down_revision = None
branch_labels = None
depends_on = None


release_status_enum = postgresql.ENUM(
    "draft",
    "candidate",
    "active",
    "inactive",
    "retired",
    "failed",
    name="release_status",
    create_type=False,
)


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    release_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "features",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("feature_key", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("owner_team", sa.String(length=200), nullable=False),
        sa.Column("repo_url", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("feature_key", name="uq_features_feature_key"),
    )
    op.create_index("ix_features_feature_key", "features", ["feature_key"], unique=False)

    op.create_table(
        "releases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("feature_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("manifest_version", sa.String(length=20), nullable=False, server_default="1.0"),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("environment", sa.String(length=50), nullable=False),
        sa.Column("status", release_status_enum, nullable=False, server_default="candidate"),
        sa.Column("route", sa.String(length=200), nullable=False),
        sa.Column("entry_url", sa.String(length=1000), nullable=False),
        sa.Column("api_base_url", sa.String(length=1000), nullable=False),
        sa.Column("nav_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("authorization_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("auth_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("compatibility_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("activated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["feature_id"], ["features.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("feature_id", "version", "environment", name="uq_release_feature_version_env"),
    )

    op.create_index("ix_releases_env_status", "releases", ["environment", "status"], unique=False)
    op.create_index("ix_releases_feature_env", "releases", ["feature_id", "environment"], unique=False)
    op.create_index("ix_releases_route_env", "releases", ["environment", "route"], unique=False)

    op.execute("""
        CREATE UNIQUE INDEX uq_one_active_release_per_feature_env
        ON releases(feature_id, environment)
        WHERE status = 'active' AND is_deleted = FALSE
    """)

    op.execute("""
        CREATE UNIQUE INDEX uq_active_route_per_environment
        ON releases(environment, route)
        WHERE status = 'active' AND is_deleted = FALSE
    """)

    op.create_table(
        "audits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("feature_key", sa.String(length=100), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=True),
        sa.Column("environment", sa.String(length=50), nullable=True),
        sa.Column("actor", sa.String(length=300), nullable=False),
        sa.Column("details_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_audits_action", "audits", ["action"], unique=False)
    op.create_index("ix_audits_feature_key", "audits", ["feature_key"], unique=False)
    op.create_index("ix_audits_created_at", "audits", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_audits_created_at", table_name="audits")
    op.drop_index("ix_audits_feature_key", table_name="audits")
    op.drop_index("ix_audits_action", table_name="audits")
    op.drop_table("audits")

    op.execute("DROP INDEX IF EXISTS uq_active_route_per_environment")
    op.execute("DROP INDEX IF EXISTS uq_one_active_release_per_feature_env")

    op.drop_index("ix_releases_route_env", table_name="releases")
    op.drop_index("ix_releases_feature_env", table_name="releases")
    op.drop_index("ix_releases_env_status", table_name="releases")
    op.drop_table("releases")

    op.drop_index("ix_features_feature_key", table_name="features")
    op.drop_table("features")

    release_status_enum.drop(op.get_bind(), checkfirst=True)
