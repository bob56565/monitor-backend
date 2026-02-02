"""Add A2 processing tables

Revision ID: 004_a2_tables
Revises: 003_provenance
Create Date: 2026-01-30

Adds all tables needed for A2 data quality processing, orchestration, and canonical summaries.
Non-breaking, additive migration only.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '004_a2_tables'
down_revision = '003_provenance'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all A2 tables."""
    
    # a2_runs table
    op.create_table(
        'a2_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('a2_run_id', sa.String(), nullable=False),
        sa.Column('submission_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('QUEUED', 'RUNNING', 'COMPLETED', 'FAILED', name='a2statusenum'), nullable=False, server_default='QUEUED'),
        sa.Column('progress', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('triggered_by', sa.String(), nullable=True, server_default='auto'),
        sa.Column('superseded', sa.Boolean(), nullable=True, server_default='0'),
        sa.Column('computation_time_ms', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['submission_id'], ['part_a_submissions.submission_id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_a2_runs_a2_run_id'), 'a2_runs', ['a2_run_id'], unique=True)
    op.create_index(op.f('ix_a2_runs_created_at'), 'a2_runs', ['created_at'], unique=False)
    op.create_index(op.f('ix_a2_runs_id'), 'a2_runs', ['id'], unique=False)
    op.create_index(op.f('ix_a2_runs_status'), 'a2_runs', ['status'], unique=False)
    op.create_index(op.f('ix_a2_runs_submission_id'), 'a2_runs', ['submission_id'], unique=False)
    op.create_index(op.f('ix_a2_runs_user_id'), 'a2_runs', ['user_id'], unique=False)
    
    # a2_summaries table
    op.create_table(
        'a2_summaries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('a2_run_id', sa.String(), nullable=False),
        sa.Column('submission_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('stream_coverage', sa.JSON(), nullable=False),
        sa.Column('gating', sa.JSON(), nullable=False),
        sa.Column('priors_used', sa.JSON(), nullable=False),
        sa.Column('prior_decay_state', sa.JSON(), nullable=False),
        sa.Column('conflict_flags', sa.JSON(), nullable=False),
        sa.Column('derived_features_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('derived_features_detail', sa.JSON(), nullable=True),
        sa.Column('anchor_strength_by_domain', sa.JSON(), nullable=False),
        sa.Column('confidence_distribution', sa.JSON(), nullable=True),
        sa.Column('schema_version', sa.String(), nullable=False, server_default='1.0.0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['a2_run_id'], ['a2_runs.a2_run_id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_a2_summaries_a2_run_id'), 'a2_summaries', ['a2_run_id'], unique=True)
    op.create_index(op.f('ix_a2_summaries_created_at'), 'a2_summaries', ['created_at'], unique=False)
    op.create_index(op.f('ix_a2_summaries_id'), 'a2_summaries', ['id'], unique=False)
    op.create_index(op.f('ix_a2_summaries_submission_id'), 'a2_summaries', ['submission_id'], unique=False)
    op.create_index(op.f('ix_a2_summaries_user_id'), 'a2_summaries', ['user_id'], unique=False)
    
    # a2_artifacts table
    op.create_table(
        'a2_artifacts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('a2_run_id', sa.String(), nullable=False),
        sa.Column('submission_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('artifact_type', sa.String(), nullable=False),
        sa.Column('artifact_data', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['a2_run_id'], ['a2_runs.a2_run_id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_a2_artifacts_a2_run_id'), 'a2_artifacts', ['a2_run_id'], unique=False)
    op.create_index(op.f('ix_a2_artifacts_artifact_type'), 'a2_artifacts', ['artifact_type'], unique=False)
    op.create_index(op.f('ix_a2_artifacts_id'), 'a2_artifacts', ['id'], unique=False)
    op.create_index(op.f('ix_a2_artifacts_submission_id'), 'a2_artifacts', ['submission_id'], unique=False)
    op.create_index(op.f('ix_a2_artifacts_user_id'), 'a2_artifacts', ['user_id'], unique=False)


def downgrade() -> None:
    """Remove all A2 tables."""
    op.drop_table('a2_artifacts')
    op.drop_table('a2_summaries')
    op.drop_table('a2_runs')
