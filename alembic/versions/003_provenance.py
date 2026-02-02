"""Add inference provenance table

Revision ID: 003_provenance
Revises: 002_part_a_tables
Create Date: 2026-01-29 04:00:00.000000

Additive-only migration: Creates inference_provenance table for audit trails.
Does not modify any existing tables.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '003_provenance'
down_revision = '002_part_a_tables'
branch_labels = None
depends_on = None


def upgrade():
    """Create inference_provenance table."""
    op.create_table(
        'inference_provenance',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('output_id', sa.String(), nullable=False),
        sa.Column('panel_name', sa.String(), nullable=False),
        sa.Column('metric_name', sa.String(), nullable=False),
        sa.Column('output_type', sa.String(), nullable=False),
        sa.Column('time_window_start', sa.DateTime(), nullable=True),
        sa.Column('time_window_end', sa.DateTime(), nullable=True),
        sa.Column('time_window_days', sa.Integer(), nullable=True),
        sa.Column('input_chain', sa.Text(), nullable=False),
        sa.Column('raw_input_refs', sa.JSON(), nullable=False),
        sa.Column('derived_features', sa.JSON(), nullable=True),
        sa.Column('methodologies_used', sa.JSON(), nullable=False),
        sa.Column('method_why', sa.Text(), nullable=True),
        sa.Column('confidence_payload', sa.JSON(), nullable=False),
        sa.Column('confidence_percent', sa.Float(), nullable=False),
        sa.Column('gating_payload', sa.JSON(), nullable=False),
        sa.Column('gating_allowed', sa.String(), nullable=False),
        sa.Column('output_value', sa.Float(), nullable=True),
        sa.Column('output_range_low', sa.Float(), nullable=True),
        sa.Column('output_range_high', sa.Float(), nullable=True),
        sa.Column('output_units', sa.String(), nullable=True),
        sa.Column('schema_version', sa.String(), server_default='1.0.0', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('computation_time_ms', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for common queries
    op.create_index('ix_inference_provenance_user_id', 'inference_provenance', ['user_id'])
    op.create_index('ix_inference_provenance_output_id', 'inference_provenance', ['output_id'])
    op.create_index('ix_inference_provenance_panel_name', 'inference_provenance', ['panel_name'])
    op.create_index('ix_inference_provenance_confidence_percent', 'inference_provenance', ['confidence_percent'])
    op.create_index('ix_inference_provenance_created_at', 'inference_provenance', ['created_at'])


def downgrade():
    """Drop inference_provenance table (only if needed for rollback)."""
    op.drop_index('ix_inference_provenance_created_at', 'inference_provenance')
    op.drop_index('ix_inference_provenance_confidence_percent', 'inference_provenance')
    op.drop_index('ix_inference_provenance_panel_name', 'inference_provenance')
    op.drop_index('ix_inference_provenance_output_id', 'inference_provenance')
    op.drop_index('ix_inference_provenance_user_id', 'inference_provenance')
    op.drop_table('inference_provenance')
