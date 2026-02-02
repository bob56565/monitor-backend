"""Add base user tables

Revision ID: 001_base_tables
Revises: 
Create Date: 2026-01-29 06:15:00

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = '001_base_tables'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=True, default=datetime.utcnow),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # Create raw_sensor_data table
    op.create_table(
        'raw_sensor_data',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=True, default=datetime.utcnow),
        sa.Column('sensor_value_1', sa.Float(), nullable=False),
        sa.Column('sensor_value_2', sa.Float(), nullable=False),
        sa.Column('sensor_value_3', sa.Float(), nullable=False),
        sa.Column('raw_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=datetime.utcnow),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_raw_sensor_data_id'), 'raw_sensor_data', ['id'], unique=False)

    # Create calibrated_features table
    op.create_table(
        'calibrated_features',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('raw_sensor_id', sa.Integer(), nullable=True),
        sa.Column('feature_1', sa.Float(), nullable=False),
        sa.Column('feature_2', sa.Float(), nullable=False),
        sa.Column('feature_3', sa.Float(), nullable=False),
        sa.Column('derived_metric', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=datetime.utcnow),
        sa.Column('feature_pack_v2_json', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['raw_sensor_id'], ['raw_sensor_data.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_calibrated_features_id'), 'calibrated_features', ['id'], unique=False)

    # Create inference_results table
    op.create_table(
        'inference_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('calibrated_feature_id', sa.Integer(), nullable=True),
        sa.Column('prediction', sa.Float(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('model_version', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=datetime.utcnow),
        sa.Column('inference_pack_v2_json', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['calibrated_feature_id'], ['calibrated_features.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_inference_results_id'), 'inference_results', ['id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_inference_results_id'), table_name='inference_results')
    op.drop_table('inference_results')
    op.drop_index(op.f('ix_calibrated_features_id'), table_name='calibrated_features')
    op.drop_table('calibrated_features')
    op.drop_index(op.f('ix_raw_sensor_data_id'), table_name='raw_sensor_data')
    op.drop_table('raw_sensor_data')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')
