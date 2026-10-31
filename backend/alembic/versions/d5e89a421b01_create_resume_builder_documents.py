"""create_resume_builder_documents

Revision ID: d5e89a421b01
Revises: c7a95cb40396
Create Date: 2026-10-25 14:36:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5e89a421b01'
down_revision: Union[str, Sequence[str], None] = 'c7a95cb40396'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'resume_builder_documents',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('source_resume_id', sa.String(length=36), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default=sa.text('1'), comment='Monotonic version for optimistic concurrency control'),
        sa.Column('template_id', sa.String(length=50), nullable=False, server_default='ats_professional', comment='Canonical single-column ATS Professional template'),
        sa.Column('template_config', sa.JSON(), nullable=False),
        sa.Column('section_order', sa.JSON(), nullable=False),
        sa.Column('section_visibility', sa.JSON(), nullable=False),
        sa.Column('content', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['anonymous_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_resume_id'], ['uploaded_resumes.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_resume_builder_documents_session_id'), 'resume_builder_documents', ['session_id'], unique=False)
    op.create_index(op.f('ix_resume_builder_documents_source_resume_id'), 'resume_builder_documents', ['source_resume_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_resume_builder_documents_source_resume_id'), table_name='resume_builder_documents')
    op.drop_index(op.f('ix_resume_builder_documents_session_id'), table_name='resume_builder_documents')
    op.drop_table('resume_builder_documents')
