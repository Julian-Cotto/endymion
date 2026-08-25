"""add release auth json

Revision ID: 0002_add_release_auth_json
Revises: 0001_init_registry
Create Date: 2026-05-06 18:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0002_add_release_auth_json"
down_revision = "0001_init_registry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "releases",
        sa.Column(
            "auth_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("releases", "auth_json")