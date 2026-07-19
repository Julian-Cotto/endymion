"""add report_uploaded_datasets table for file-typed sources"""
from alembic import op
import sqlalchemy as sa


revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'report_uploaded_datasets',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('ref', sa.String(length=64), nullable=False),
        sa.Column('filename', sa.String(length=320), nullable=False),
        sa.Column('columns', sa.JSON(), nullable=False),
        sa.Column('row_data', sa.JSON(), nullable=False),
        sa.Column('row_count', sa.Integer(), nullable=False),
        sa.Column('created_by', sa.String(length=320), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_report_uploaded_datasets_ref'), 'report_uploaded_datasets', ['ref'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_report_uploaded_datasets_ref'), table_name='report_uploaded_datasets')
    op.drop_table('report_uploaded_datasets')
