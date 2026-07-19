"""add report_sources table, combine column, and make sql_text nullable"""
from alembic import op
import sqlalchemy as sa


revision = 'a1b2c3d4e5f6'
down_revision = 'f3e0618d2cd5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('report_definitions', sa.Column('combine', sa.JSON(), nullable=True))
    # A report can now derive its data from `report_sources` instead of an
    # inline SELECT, so sql_text is no longer required.
    with op.batch_alter_table('report_definitions') as batch:
        batch.alter_column('sql_text', existing_type=sa.Text(), nullable=True)

    op.create_table(
        'report_sources',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('report_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=160), nullable=False),
        sa.Column('source_type', sa.String(length=20), nullable=False),
        sa.Column('sql_text', sa.Text(), nullable=True),
        sa.Column('file_ref', sa.String(length=320), nullable=True),
        sa.Column('params', sa.JSON(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['report_id'], ['report_definitions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('report_id', 'name', name='uq_source_report_name'),
    )
    op.create_index(op.f('ix_report_sources_report_id'), 'report_sources', ['report_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_report_sources_report_id'), table_name='report_sources')
    op.drop_table('report_sources')
    with op.batch_alter_table('report_definitions') as batch:
        batch.alter_column('sql_text', existing_type=sa.Text(), nullable=False)
    op.drop_column('report_definitions', 'combine')
